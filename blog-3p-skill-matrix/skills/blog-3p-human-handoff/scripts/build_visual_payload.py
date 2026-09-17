#!/usr/bin/env python3
"""Build the fixed, minimal visual hand-off page from canonical inputs."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from html.parser import HTMLParser
from pathlib import Path

TEMPLATE_ID = "BLOG_3P_VISUAL_PAYLOAD"
TEMPLATE_VERSION = "2"
CTA_FIELDS = ("anchor_text", "product_name", "product_destination_url", "product_evidence_path", "reader_task_relevance", "relationship_disclosure")
PACKAGE_SCHEMAS = {"1.2", "1.3"}
FORBIDDEN_BODY_TAGS = {
    "html", "head", "body", "main", "section", "article", "header", "footer",
    "style", "script", "iframe", "form", "button", "input", "textarea", "select",
    "nav", "aside", "img",
}


class BodyFragmentPolicy(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag.casefold() in FORBIDDEN_BODY_TAGS:
            raise ValueError(f"canonical body may not contain <{tag}>; the fixed template owns layout and image annotations")
        for name, _ in attrs:
            if name.casefold() == "style" or name.casefold().startswith("on"):
                raise ValueError(f"canonical body may not contain the {name} attribute")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


class CTAContentParser(HTMLParser):
    """Read visible body text and links without changing the canonical fragment."""

    def __init__(self):
        super().__init__()
        self.body_text: list[str] = []
        self.anchors: list[tuple[str, str]] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.casefold() == "a":
            self._anchor_href = dict(attrs).get("href", "").strip()
            self._anchor_text = []

    def handle_data(self, data):
        self.body_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag):
        if tag.casefold() == "a" and self._anchor_href is not None:
            self.anchors.append((self._anchor_href, normalize_text("".join(self._anchor_text))))
            self._anchor_href = None
            self._anchor_text = []


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def read_body_fragment(path: Path) -> str:
    body = path.read_text(encoding="utf-8")
    parser = BodyFragmentPolicy()
    parser.feed(body)
    parser.close()
    return body


def read_article_package(path: Path) -> dict:
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"article-package must be valid JSON: {exc}") from exc
    if not isinstance(package, dict) or package.get("schema_version") not in PACKAGE_SCHEMAS:
        raise ValueError("article-package must use schema_version 1.2 or 1.3")
    return package


def required_cta_from_package(path: Path) -> dict[str, str]:
    package = read_article_package(path)
    cta = package.get("cta")
    if not isinstance(cta, dict) or cta.get("mode") != "SECONDARY_RECOMMENDATION":
        raise ValueError("article-package must declare a required SECONDARY_RECOMMENDATION CTA")
    missing = [field for field in CTA_FIELDS if not isinstance(cta.get(field), str) or not cta[field].strip()]
    if missing:
        raise ValueError("article-package required CTA is missing: " + ", ".join(missing))
    return {field: cta[field].strip() for field in CTA_FIELDS}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_relative(workspace: Path, path: Path) -> str:
    root = workspace.resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"handoff artifact must stay inside --workspace: {path}")
    return str(resolved.relative_to(root))


def artifact_record(workspace: Path, path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"handoff artifact is missing: {path}")
    return {"path": workspace_relative(workspace, path), "sha256": sha256_file(path)}


def require_approved_final_visual_delta(workspace: Path, package: dict, visual_payload: Path) -> dict:
    """Require an existing same-R visual receipt before deriving a release manifest."""
    final_delta = package.get("final_visual_payload_delta")
    if not isinstance(final_delta, dict) or final_delta.get("reviewer_result") != "APPROVED":
        raise ValueError("handoff manifest requires an APPROVED final visual payload delta")
    required = (
        "report_path", "report_sha256", "reviewer_agent_id", "review_index_sha256",
        "reviewed_visual_manifest_sha256", "reviewed_visual_payload_sha256",
    )
    missing = [field for field in required if not isinstance(final_delta.get(field), str) or not final_delta[field].strip()]
    if missing:
        raise ValueError("approved final visual payload delta is missing: " + ", ".join(missing))
    try:
        report = (workspace / final_delta["report_path"]).resolve()
        workspace_relative(workspace, report)
    except (TypeError, ValueError) as exc:
        raise ValueError("final visual payload delta report must stay inside --workspace") from exc
    if not report.is_file() or final_delta["report_sha256"] != sha256_file(report):
        raise ValueError("final visual payload delta report_sha256 must match its existing report")
    index = workspace / "reviews/review-index.json"
    if not index.is_file() or final_delta["review_index_sha256"] != sha256_file(index):
        raise ValueError("final visual payload delta review_index_sha256 must match reviews/review-index.json")
    try:
        review_index = json.loads(index.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("reviews/review-index.json must be valid JSON") from exc
    if review_index.get("article_id") != package.get("article_id"):
        raise ValueError("review index article_id must match article-package before handoff compilation")
    if review_index.get("latest_research_review", {}).get("status") != "RESEARCH_APPROVED":
        raise ValueError("handoff manifest requires review-index RESEARCH_APPROVED")
    if review_index.get("latest_full_review", {}).get("status") != "APPROVED":
        raise ValueError("handoff manifest requires review-index full R APPROVED")
    indexed_visual_delta = review_index.get("last_delta")
    if not isinstance(indexed_visual_delta, dict) or indexed_visual_delta.get("review_scope") != "R_VISUAL_DELTA" or indexed_visual_delta.get("status") != "APPROVED":
        raise ValueError("handoff manifest requires an approved R_VISUAL_DELTA in the review index")
    for field in (
        "report_path", "report_sha256", "reviewer_agent_id",
        "reviewed_visual_manifest_sha256", "reviewed_visual_payload_sha256",
    ):
        if indexed_visual_delta.get(field) != final_delta.get(field):
            raise ValueError(f"final visual payload delta {field} must match the review index")
    sources = package.get("artifact_sources")
    visual_source = sources.get("visual_manifest") if isinstance(sources, dict) else None
    if not isinstance(visual_source, dict) or not isinstance(visual_source.get("path"), str):
        raise ValueError("article-package requires a visual_manifest artifact source")
    visual_manifest = workspace / visual_source["path"]
    if not visual_manifest.is_file() or visual_source.get("sha256") != sha256_file(visual_manifest):
        raise ValueError("article-package visual_manifest sha256 must match before handoff compilation")
    if final_delta["reviewed_visual_manifest_sha256"] != visual_source["sha256"]:
        raise ValueError("final visual payload delta must bind the reviewed visual manifest")
    if final_delta["reviewed_visual_payload_sha256"] != sha256_file(visual_payload):
        raise ValueError("final visual payload delta must bind the compiled visual payload")
    return final_delta


def build_handoff_manifest(
    *, workspace: Path, package_path: Path, package: dict, metadata_path: Path, output: Path,
    visual_payload: Path, requirements_traceability: Path,
) -> None:
    """Produce one small receipt that points at the final human-release artifacts."""
    article_id = str(package.get("article_id", "")).strip()
    if not article_id:
        raise ValueError("article-package requires article_id to build a handoff manifest")
    artifact_sources = package.get("artifact_sources")
    if not isinstance(artifact_sources, dict):
        raise ValueError("article-package schema 1.3 requires artifact_sources before handoff compilation")
    visual_source = artifact_sources.get("visual_manifest")
    if not isinstance(visual_source, dict) or not isinstance(visual_source.get("path"), str):
        raise ValueError("article-package requires a visual_manifest artifact source")
    visual_manifest = workspace / visual_source["path"]
    visual_record = artifact_record(workspace, visual_manifest)
    if visual_source.get("sha256") != visual_record["sha256"]:
        raise ValueError("article-package visual_manifest sha256 must match the reviewed manifest before handoff compilation")
    final_delta = require_approved_final_visual_delta(workspace, package, visual_payload)
    manifest = {
        "schema_version": "1.0",
        "article_id": article_id,
        "purpose": "DERIVED_HANDOFF_ARTIFACT_AND_HASH_INDEX",
        "visual_payload": artifact_record(workspace, visual_payload),
        "article_package": artifact_record(workspace, package_path),
        "metadata": artifact_record(workspace, metadata_path),
        "visual_manifest": visual_record,
        "final_visual_payload_delta": {
            field: final_delta[field]
            for field in (
                "reviewer_result", "report_path", "report_sha256", "reviewer_agent_id",
                "review_index_sha256", "reviewed_visual_manifest_sha256", "reviewed_visual_payload_sha256",
            )
        },
        "gate_input": {
            "requirements_traceability_path": workspace_relative(workspace, requirements_traceability),
            "requirements_traceability_sha256": sha256_file(requirements_traceability),
            "gate_mode": "MANIFEST_HASH_AND_REQUIREMENTS_ONLY",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_body_preserves_cta(body: str, cta: dict[str, str]) -> None:
    parser = CTAContentParser()
    parser.feed(body)
    parser.close()
    expected_anchor = normalize_text(cta["anchor_text"])
    expected_href = cta["product_destination_url"]
    if not any(href == expected_href and text == expected_anchor for href, text in parser.anchors):
        raise ValueError("canonical body must preserve the required CTA's exact visible anchor text and href")
    disclosure = cta["relationship_disclosure"]
    if disclosure != "NOT_APPLICABLE" and normalize_text(disclosure) not in normalize_text("".join(parser.body_text)):
        raise ValueError("canonical body must preserve the required CTA relationship disclosure")


CSS = """
body{margin:0;background:#fff;color:#222;font:16px/1.7 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
main{max-width:860px;margin:28px auto;padding:0 20px 48px}h1{font-size:32px;line-height:1.25;margin:0 0 28px}h2{font-size:24px;line-height:1.35;margin-top:34px}h3{font-size:19px;line-height:1.4;margin-top:24px}a{color:#0759b7;text-decoration:underline}.image-placeholder{border:1px dashed #888;background:#fafafa;padding:12px 14px;margin:22px 0;font-size:14px;color:#333}.image-placeholder strong{display:block;margin-bottom:5px}#seo-metadata{border-top:1px solid #ccc;margin-top:36px;padding-top:16px}#seo-metadata h2{margin:0 0 12px;font-size:20px}#seo-metadata p{margin:7px 0}
""".strip()
TEMPLATE_ASSET_SHA256 = hashlib.sha256(CSS.encode("utf-8")).hexdigest()


def image_placeholders(path: Path | None) -> str:
    if path is None:
        return ""
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("images-json must contain a list")
    rendered = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"image #{index} must be an object")
        alt = str(item.get("alt", "")).strip()
        if not alt:
            raise ValueError(f"image #{index} is missing required alt text")
        zone = str(item.get("coverage_zone", "UNSPECIFIED")).strip().upper()
        rendered.append(
            '<aside class="image-placeholder" data-coverage-zone="{zone}">'
            '<strong>【图片注释 #{index}】</strong>'
            '<div>插入图片：{file}</div><div>位置：{zone}</div>'
            '<div>Alt：{alt}</div><div>图注：{caption}</div></aside>'.format(
                index=index,
                zone=html.escape(zone),
                file=html.escape(str(item.get("file", "待提供"))),
                alt=html.escape(alt),
                caption=html.escape(str(item.get("caption", ""))),
            )
        )
    return "\n".join(rendered)


def read_metadata(path: Path) -> tuple[str, str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("metadata-json must contain an object")
    seo_title = str(data.get("seo_title", "")).strip()
    description = str(data.get("description", data.get("meta_description", ""))).strip()
    raw_tags = data.get("tags", [])
    if isinstance(raw_tags, list):
        tags = ", ".join(str(tag).strip() for tag in raw_tags if str(tag).strip())
    else:
        tags = str(raw_tags).strip()
    if not seo_title or not tags or not description:
        raise ValueError("metadata-json requires non-empty seo_title, tags and description")
    return seo_title, tags, description


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-html", type=Path, required=True)
    parser.add_argument("--article-package", type=Path, required=True)
    parser.add_argument("--metadata-json", type=Path, required=True)
    parser.add_argument("--images-json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--handoff-manifest-output", type=Path)
    parser.add_argument("--workspace", type=Path, help="Required only when generating --handoff-manifest-output.")
    parser.add_argument("--requirements-traceability", type=Path, help="Required only when generating --handoff-manifest-output.")
    parser.add_argument(
        "--title-transfer-mode", "--heading-transport",
        dest="title_transfer_mode",
        choices=["SEPARATE_TITLE_FIELD", "TITLE_IN_BODY", "BODY_H1_REQUIRED"],
        default="SEPARATE_TITLE_FIELD",
        help="Local title/body selection aid; it does not assert the public page's heading markup.",
    )
    args = parser.parse_args()

    title_transfer_mode = "TITLE_IN_BODY" if args.title_transfer_mode == "BODY_H1_REQUIRED" else args.title_transfer_mode
    body = read_body_fragment(args.body_html)
    package = read_article_package(args.article_package)
    cta = required_cta_from_package(args.article_package)
    ensure_body_preserves_cta(body, cta)
    body = body.replace("{{IMAGE_CARDS}}", image_placeholders(args.images_json))
    seo_title, tags, description = read_metadata(args.metadata_json)
    rendered = """<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{title}</title><style>{css}</style><main data-template-id=\"{template_id}\" data-template-version=\"{template_version}\" data-template-assets-sha256=\"{template_assets_sha256}\"><!-- {template_id}@{template_version}: compiler-generated minimal template --><h1 id=\"blog-title\">{title}</h1><article id=\"article-body\" data-title-transfer-mode=\"{mode}\">{body}</article><section id=\"seo-metadata\"><h2>SEO Metadata</h2><p id=\"seo-title\"><strong>SEO title：</strong>{seo_title}</p><p id=\"seo-tags\"><strong>Tags：</strong>{tags}</p><p id=\"seo-description\"><strong>Description：</strong>{description}</p></section></main></html>""".format(
        title=html.escape(args.title), css=CSS, template_id=TEMPLATE_ID,
        template_version=TEMPLATE_VERSION, template_assets_sha256=TEMPLATE_ASSET_SHA256,
        mode=title_transfer_mode, body=body, seo_title=html.escape(seo_title),
        tags=html.escape(tags), description=html.escape(description),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    if args.handoff_manifest_output is not None:
        if args.workspace is None or args.requirements_traceability is None:
            raise ValueError("--handoff-manifest-output requires --workspace and --requirements-traceability")
        if package.get("schema_version") != "1.3":
            raise ValueError("--handoff-manifest-output requires article-package schema_version 1.3")
        build_handoff_manifest(
            workspace=args.workspace,
            package_path=args.article_package,
            package=package,
            metadata_path=args.metadata_json,
            output=args.handoff_manifest_output,
            visual_payload=args.output,
            requirements_traceability=args.requirements_traceability,
        )
    print(f"BUILT: {args.output}")
    if args.handoff_manifest_output is not None:
        print(f"HANDOFF_MANIFEST_BUILT: {args.handoff_manifest_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
