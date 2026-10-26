"""Small deterministic checks: count actual links and verify delivery assets."""
from __future__ import annotations
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host(value: str) -> str:
    raw = value if "://" in value else "//" + value
    try:
        name = (urlsplit(raw).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    return name[4:] if name.startswith("www.") else name


def policy_errors(policy: object) -> list[str]:
    if policy is None:
        return []
    if not isinstance(policy, dict):
        return ["link_policy must be an object"]
    errors = []
    for key in ("max_target_links", "max_web_links", "target_link_count", "web_link_count"):
        if key in policy and (isinstance(policy[key], bool) or not isinstance(policy[key], int) or policy[key] < 0):
            errors.append(f"link_policy.{key} must be a non-negative integer")
    domains = policy.get("target_domains", [])
    if not isinstance(domains, list) or any(not isinstance(d, str) or not host(d) or "/" in d or "@" in d for d in domains):
        errors.append("link_policy.target_domains must contain explicit domain names")
    required = policy.get("required_links", [])
    if not isinstance(required, list):
        errors.append("link_policy.required_links must be a list")
    else:
        for item in required:
            if not isinstance(item, dict) or not item.get("href") or not item.get("anchor_text"):
                errors.append("required_links entries need href and anchor_text")
            elif "count" in item and (isinstance(item["count"], bool) or not isinstance(item["count"], int) or item["count"] < 1):
                errors.append("required_links.count must be a positive integer when specified")
    brands = policy.get("target_brand_names", {})
    if not isinstance(brands, dict):
        errors.append("link_policy.target_brand_names must map domains to confirmed brand names")
    else:
        for domain, names in brands.items():
            if (not isinstance(domain, str) or not host(domain)
                    or re.search(r"[\s/@:#?]", domain)):
                errors.append("target_brand_names keys must be explicit domain names")
            if (not isinstance(names, list) or not names
                    or any(not isinstance(name, str) or not name.strip() for name in names)):
                errors.append("target_brand_names entries need non-empty confirmed brand names")
    return errors


def anchor_has_brand(text: str, names: list[str]) -> bool:
    text = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
    # A URL is not a substitute for a brand-bearing text recommendation.
    if re.fullmatch(r"(?:https?://|www\.)\S+", text):
        return False
    for name in names:
        name = " ".join(unicodedata.normalize("NFKC", name).casefold().split())
        prefix = r"(?<![a-z0-9])" if re.match(r"[a-z0-9]", name[0]) else ""
        suffix = r"(?![a-z0-9])" if re.match(r"[a-z0-9]", name[-1]) else ""
        if re.search(prefix + re.escape(name) + suffix, text):
            return True
    return False


def brand_anchor_errors(anchors, policy: dict) -> list[str]:
    brands = {host(domain): names for domain, names in policy.get("target_brand_names", {}).items()}
    errors = []
    for url, text in anchors:
        domain = host(url)
        matches = [key for key in brands if domain == key or domain.endswith("." + key)]
        if matches:
            names = brands[max(matches, key=len)]
            bare_address = (not re.search(r"\s", text) and "." in text.split("/", 1)[0]
                            and host(text) == domain)
            if bare_address or not anchor_has_brand(text, names):
                errors.append("target product anchor must contain its confirmed brand name: " + url)
    return errors


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = []
        self.current = None
        self.parts = []
        self.code_depth = 0
        self.bare_urls = []
        self.visibility = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        hidden = (bool(self.visibility and self.visibility[-1][1])
                  or tag in {"script", "style", "template", "noscript"}
                  or "hidden" in attributes
                  or bool(re.search(r"(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))",
                                    attributes.get("style") or "", re.I)))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.visibility.append((tag, hidden))
        if tag in {"pre", "code"}:
            self.code_depth += 1
        if tag == "a":
            self.current = dict(attrs).get("href", "")
            self.parts = []

    def handle_data(self, data):
        if self.visibility and self.visibility[-1][1]:
            return
        if self.current is not None:
            self.parts.append(data)
        elif not self.code_depth:
            self.bare_urls.extend(re.findall(r"https?://[^\s<>]+", data))

    def handle_endtag(self, tag):
        for index in range(len(self.visibility) - 1, -1, -1):
            if self.visibility[index][0] == tag:
                del self.visibility[index:]
                break
        if tag in {"pre", "code"}:
            self.code_depth = max(0, self.code_depth - 1)
        if tag == "a" and self.current is not None:
            self.anchors.append((self.current, " ".join("".join(self.parts).split())))
            self.current = None


def check_links(body: str, policy: dict | None, cta: dict) -> tuple[dict, list[str]]:
    errors = policy_errors(policy)
    if errors:
        return {}, errors
    policy = policy or {}
    parser = Links()
    parser.feed(body)
    domains = {host(d) for d in policy.get("target_domains", [])}
    domains.add(host(cta.get("product_destination_url", "")))
    domains.update(host(d) for d in policy.get("target_brand_names", {}))
    domains.discard("")

    def target(url):
        name = host(url)
        return any(name == d or name.endswith("." + d) for d in domains)

    web = [(url, text) for url, text in parser.anchors if urlsplit(url).scheme in {"http", "https"}]
    targets = [(url, text) for url, text in web if target(url)]
    bare_targets = [url for url in parser.bare_urls if target(url)]
    errors.extend(brand_anchor_errors(web, policy))
    stats = {
        "web_link_occurrences": len(web),
        "target_link_occurrences": len(targets),
        "unique_target_urls": len({url for url, _ in targets}),
        "third_party_link_occurrences": len(web) - len(targets),
        "potential_target_autolinks": len(bare_targets),
    }
    for key, count in (("max_target_links", len(targets)), ("max_web_links", len(web))):
        if key in policy and count > policy[key]:
            errors.append(f"{key}: observed {count}, allowed {policy[key]}")
    for key, count in (("target_link_count", len(targets)), ("web_link_count", len(web))):
        if key in policy and count != policy[key]:
            errors.append(f"{key}: observed {count}, required {policy[key]}")
    if bare_targets and any(k in policy for k in ("max_target_links", "max_web_links", "target_link_count", "web_link_count")):
        errors.append("bare target URLs may become platform autolinks; make them explicit before enforcing a link budget")
    required = [{"href": cta.get("product_destination_url"), "anchor_text": cta.get("anchor_text")}]
    required += policy.get("required_links", [])
    for item in required:
        expected = (item["href"], " ".join(str(item["anchor_text"]).split()))
        if expected not in parser.anchors:
            errors.append("missing required link/anchor: " + str(item["anchor_text"]))
        elif "count" in item and parser.anchors.count(expected) != item["count"]:
            errors.append("required link/anchor count differs: " + str(item["anchor_text"]))
    return stats, errors


def check_visuals(manifest: dict, root: Path, *, cover_required=False, minimum_images=0, exact_body_images=None) -> list[str]:
    errors = []
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return ["visual assets must be a list"]
    if len(assets) < minimum_images:
        errors.append(f"body images: observed {len(assets)}, required at least {minimum_images}")
    if exact_body_images is not None and len(assets) != exact_body_images:
        errors.append(f"body images: observed {len(assets)}, required exactly {exact_body_images}")
    if minimum_images >= 3:
        zones = {str(a.get("coverage_zone", "")).upper() for a in assets if isinstance(a, dict)}
        if not {"LEAD", "MIDDLE", "CLOSING"}.issubset(zones):
            errors.append("body images need lead/middle/closing coverage; cover does not count")
    cover = manifest.get("cover_image")
    if cover_required and not isinstance(cover, dict):
        errors.append("separate cover_image is required")
    root = root.resolve()
    records = [("body image", a) for a in assets]
    if isinstance(cover, dict):
        records.append(("cover image", cover))
    for kind, item in records:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str):
            errors.append(kind + " lacks a file")
            continue
        relative = Path(item["file"])
        path = (root / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or root not in path.parents or not path.is_file():
            errors.append(kind + " must exist inside the article root")
            continue
        suffix = path.suffix.lower()
        data = path.read_bytes()
        valid = suffix == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n") or suffix in {".jpg", ".jpeg"} and data.startswith(b"\xff\xd8\xff")
        if not valid:
            errors.append(kind + " must be a real PNG/JPG/JPEG")
        if item.get("sha256") != digest(path):
            errors.append(kind + " hash does not match")
        if not str(item.get("alt", "")).strip():
            errors.append(kind + " needs localized alt text")
        if kind == "cover image":
            if not re.fullmatch(r"00-cover-.+\.(png|jpe?g)", path.name, re.I):
                errors.append("cover image needs separate 00-cover naming")
            if any(item.get("file") == a.get("file") or item.get("sha256") == a.get("sha256") for a in assets if isinstance(a, dict)):
                errors.append("cover image must not directly reuse the body lead asset")
    return errors
