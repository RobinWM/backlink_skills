#!/usr/bin/env python3
"""Small release builder; no campaign state, review registry, or platform writes."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile


MATRIX = Path(__file__).resolve().parents[3]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError("cannot load bundled helper")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_rows(plan):
    rows = plan.get("articles")
    if not isinstance(rows, list) or not rows:
        raise ValueError("task plan needs its confirmed article list")
    ids, platforms = set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("article entry must be an object")
        identifier = row.get("article_id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", identifier):
            raise ValueError("article ID must be a safe folder name")
        platform = row.get("platform")
        if not isinstance(platform, str) or not platform.strip():
            raise ValueError("each article needs its owner-confirmed platform")
        platform = platform.strip().casefold()
        if identifier in ids or platform in platforms:
            raise ValueError("each article and platform must be distinct")
        ids.add(identifier)
        platforms.add(platform)
    return rows


def confirmation_file(plan_path):
    return plan_path.parent / ".task-confirmation.json"


def freeze(plan_path, receipt, source):
    plan_rows(json.loads(plan_path.read_text(encoding="utf-8")))
    text = receipt.read_text(encoding="utf-8").strip()
    if not text or not source.strip():
        raise ValueError("save the actual owner reply and its source first")
    target = confirmation_file(plan_path)
    record = {
        "plan_sha256": digest(plan_path), "receipt_path": str(receipt.resolve()),
        "receipt_sha256": digest(receipt), "source": source,
        "meaning": "LOCAL_BINDING_ONLY_NOT_AUTHENTICATION_OR_QUALITY_APPROVAL",
    }
    target.write_text(dump(record), encoding="utf-8")
    return {"result": "CONFIRMATION_BOUND_NOT_AUTHENTICATED", "record": str(target)}


def confirmed_plan(plan_path):
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_rows(plan)
    record = json.loads(confirmation_file(plan_path).read_text(encoding="utf-8"))
    if record.get("plan_sha256") != digest(plan_path):
        raise ValueError("task plan changed; G must inspect the change and obtain owner confirmation before rebinding")
    receipt = Path(record.get("receipt_path", ""))
    if not receipt.is_file() or record.get("receipt_sha256") != digest(receipt):
        raise ValueError("original owner confirmation is missing or changed")
    return plan


def article_context(plan, identifier):
    selected = next((x for x in plan_rows(plan) if x["article_id"] == identifier), None)
    if selected is None:
        raise ValueError("article is outside the confirmed plan")
    shared = plan.get("shared", {})
    if not isinstance(shared, dict):
        raise ValueError("shared requirements must be an object")
    row = {**copy.deepcopy(shared), **copy.deepcopy(selected)}
    for key in ("cta", "link_policy", "delivery_requirements"):
        if key in shared or key in selected:
            row[key] = {**shared.get(key, {}), **selected.get(key, {})}
    for field in ("language", "reader_task"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise ValueError("confirmed article needs " + field)
    route = row.get("review_route", "WR")
    if route != "WR":
        raise ValueError("new tasks require WR independent review; G must resolve the confirmed plan, not silently change its route")
    row["review_route"] = route
    cta = row.get("cta", {})
    for field in ("anchor_text", "product_name", "product_destination_url", "relationship_disclosure"):
        if not isinstance(cta.get(field), str) or not cta[field].strip():
            raise ValueError("owner-required CTA needs " + field)
    if cta.get("mode", "SECONDARY_RECOMMENDATION") != "SECONDARY_RECOMMENDATION":
        raise ValueError("required CTA cannot be none")
    cta["mode"] = "SECONDARY_RECOMMENDATION"
    I = module("lean_delivery_checks", MATRIX / "skills/blog-human-handoff/scripts/content_integrity.py")
    errors = I.policy_errors(row.get("link_policy"))
    if errors:
        raise ValueError("; ".join(errors))
    policy = copy.deepcopy(row.get("link_policy") or {})
    primary_domain = I.host(cta["product_destination_url"])
    if not primary_domain:
        raise ValueError("required CTA needs a target product domain")
    brands = policy.setdefault("target_brand_names", {})
    # New builds enforce the rule even when the plan omits the optional map.
    # Do not guess shorter aliases or rewrite the owner's locked anchor.
    if not any(primary_domain == I.host(d) or primary_domain.endswith("." + I.host(d)) for d in brands):
        brands[primary_domain] = [cta["product_name"]]
    for domain in policy.get("target_domains", []):
        domain = I.host(domain)
        if not any(domain == I.host(d) or domain.endswith("." + I.host(d)) for d in brands):
            errors.append("target domain needs confirmed target_brand_names: " + domain)
    errors.extend(I.brand_anchor_errors([(cta["product_destination_url"], cta["anchor_text"])], policy))
    row["link_policy"] = policy
    requirements = row.get("delivery_requirements", {})
    for field in ("body_image_count", "minimum_body_images"):
        if field in requirements and (type(requirements[field]) is not int or requirements[field] < 0):
            errors.append(field + " must be a confirmed non-negative integer")
    for field in ("cover_required", "public_image_urls_required"):
        if field in requirements and type(requirements[field]) is not bool:
            errors.append(field + " must be a boolean")
    requirements.setdefault("public_image_urls_required", True)
    row["delivery_requirements"] = requirements
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "article_id": identifier, "frozen_article": row,
        "keyword_requirements": row.get("keyword_requirements", []),
        "link_policy": row.get("link_policy", {}),
        "delivery_requirements": requirements,
        "prewrite_plan": {
            "topic_slot": {"slot_id": identifier, "reader_task": row["reader_task"],
                "differentiation_angle": row.get("angle", row["reader_task"])},
            "evidence_posture": row.get("evidence_posture", {"mode": "METHOD_TEMPLATE_NO_EXECUTION"}),
        },
    }


def build(plan_path, identifier, check=False, brief=False, verify_images=False, local_preview=False):
    plan = confirmed_plan(plan_path)
    context = article_context(plan, identifier)
    if brief:
        return {"article_id": identifier, "requirements": context["frozen_article"],
            "note": "Confirmed requirements and final-delivery defaults; not a quality verdict."}
    if local_preview and verify_images:
        raise ValueError("--local-preview is a draft; verify hosted images in the final build")
    if not local_preview and not context["delivery_requirements"]["public_image_urls_required"]:
        raise ValueError("final delivery requires public image URLs; resolve the plan or use --local-preview for a draft")
    root = plan_path.parent / "articles" / identifier
    if (root / "article-package.json").exists() or (root / "context/article-contract.json").exists():
        raise ValueError("existing indexed project: preserve its legacy route; do not silently migrate")
    source = root / "canonical/article.md"
    P = module("lean_draft_projection", MATRIX / "skills/blog-human-handoff/scripts/prepare_article.py")
    projection = P.project_draft(source, context, root)
    metadata = json.loads(projection["metadata"])
    if not isinstance(metadata.get("excerpt"), str) or not metadata["excerpt"].strip():
        raise ValueError("new release payload needs an excerpt (article summary) in the author draft")
    for requirement in context["keyword_requirements"]:
        if requirement.get("title_mode") != "COMPLETE_PHRASE":
            continue
        phrase = requirement["phrase"]
        if requirement.get("language", "").split("-")[0] != metadata["language"].split("-")[0]:
            phrase = metadata["primary_keyword"]
        if phrase.casefold() not in projection["title"].casefold():
            raise ValueError("title omits explicitly locked keyword phrase")
    row = context["frozen_article"]
    if row.get("locked_title") and row["locked_title"] != projection["title"]:
        raise ValueError("title differs from the owner-locked title")
    C = module("lean_payload_template", MATRIX / "skills/blog-human-handoff/scripts/build_visual_payload.py")
    visuals = json.loads(projection["visual_manifest"])
    public_images = None
    if not local_preview:
        H = module("public_image_checks", Path(__file__).with_name("public_images.py"))
        records = H.image_records(visuals)
        previous = root / "handoff/.build.json"
        if verify_images:
            if check:
                raise ValueError("--verify-images rebuilds; use --check separately")
            public_images = H.verify(records)
        elif previous.is_file():
            public_images = json.loads(previous.read_text(encoding="utf-8")).get("public_images")
        if not H.matching_receipt(public_images, records):
            raise ValueError("new or changed public image URLs need --verify-images before delivery")
    mode = row.get("title_transfer_mode", "SEPARATE_TITLE_FIELD")
    if mode not in {"SEPARATE_TITLE_FIELD", "TITLE_IN_BODY"}:
        raise ValueError("unsupported title transfer mode")
    with tempfile.TemporaryDirectory() as folder:
        metadata_path = Path(folder) / "metadata.json"
        metadata_path.write_text(projection["metadata"], encoding="utf-8")
        html, markdown = C.render_payload_pair(
            title=projection["title"], body=projection["canonical"],
            image_items=visuals["assets"], metadata_path=metadata_path,
            title_transfer_mode=mode, markdown_body=projection["markdown_body"],
            cover_image=visuals.get("cover_image"),
        )
    output_dir = "preview" if local_preview else "handoff"
    if local_preview:
        html = html.replace('<h1 id="blog-title">', '<p>本地草稿预览 / Local draft preview</p><h1 id="blog-title">', 1)
        markdown = "> 本地草稿预览 / Local draft preview\n\n" + markdown
    outputs = {output_dir + "/visual-payload.html": html, output_dir + "/visual-payload.md": markdown}
    inputs = {"task_plan_sha256": digest(plan_path), "article_sha256": digest(source),
        "images": {a["file"]: a["sha256"] for a in visuals["assets"]}}
    if "cover_image" in visuals:
        cover = visuals["cover_image"]
        inputs["images"][cover["file"]] = cover["sha256"]
    manifest = {
        "article_id": identifier,
        "purpose": "LOCAL_DRAFT_PREVIEW" if local_preview else "MECHANICAL_BUILD_NOT_QUALITY_APPROVAL",
        "inputs": inputs, "link_statistics": projection["link_statistics"],
        "outputs": {name: hashlib.sha256(value.encode("utf-8")).hexdigest() for name, value in outputs.items()},
        "cover": visuals.get("cover_image"), "review_route": row["review_route"],
    }
    if public_images is not None:
        manifest["public_images"] = public_images
    outputs[output_dir + "/.build.json"] = dump(manifest)
    if check:
        for name, expected in outputs.items():
            target = root / name
            if not target.is_file() or target.read_text(encoding="utf-8") != expected:
                raise ValueError(name + " differs from current source; rebuild and check the affected change")
    else:
        for name, text in outputs.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    return {
        "result": ("LOCAL_PREVIEW_NOT_QUALITY_APPROVED" if local_preview else
                   "MECHANICAL_CHECK_PASSED_NOT_QUALITY_APPROVAL" if check else "BUILT_NOT_QUALITY_APPROVED"),
        "article_id": identifier, "link_statistics": projection["link_statistics"],
        "html": str(root / output_dir / "visual-payload.html"),
        "markdown": str(root / output_dir / "visual-payload.md"),
        "body_images": len(visuals["assets"]),
        "cover": visuals.get("cover_image", {}).get("file"),
        "review_route": row["review_route"],
        "next_step": ("FINISH_PUBLIC_IMAGE_DELIVERY" if local_preview else
                      "INDEPENDENT_R_REVIEW_THEN_G_ACCEPTANCE"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--article-id")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--receipt-file", type=Path)
    parser.add_argument("--source")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--brief", action="store_true")
    parser.add_argument("--local-preview", action="store_true",
                        help="Build only a draft under preview/; never a final handoff.")
    parser.add_argument("--verify-images", action="store_true",
                        help="Anonymously verify hosted images and build the complete HTML/Markdown pair.")
    args = parser.parse_args()
    try:
        plan_path = args.plan.resolve()
        if args.freeze:
            if not args.receipt_file or not args.source or args.check or args.brief or args.verify_images or args.local_preview:
                raise ValueError("G binds an actual owner reply using --receipt-file and --source")
            result = freeze(plan_path, args.receipt_file, args.source)
        else:
            if not args.article_id:
                raise ValueError("--article-id is required")
            if args.brief and args.verify_images:
                raise ValueError("--brief cannot verify images")
            result = build(plan_path, args.article_id, check=args.check, brief=args.brief,
                           verify_images=args.verify_images, local_preview=args.local_preview)
        print(dump(result), end="")
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
