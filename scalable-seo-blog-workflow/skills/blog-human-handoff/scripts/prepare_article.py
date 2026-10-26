"""One editable Markdown draft -> deterministic internal records and two payloads.

Preparation never grants a quality verdict or permission to publish.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re
import sys


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError("cannot load local workflow helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def integrity():
    return load_module("blog_content_integrity", Path(__file__).with_name("content_integrity.py"))


def markdown_parser():
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise ValueError("Markdown authoring requires markdown-it-py; install scripts/requirements.txt in your Python environment") from exc
    return MarkdownIt("commonmark", {"html": True, "linkify": False}).enable("table")


def dump_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def read_draft(path):
    raw = path.read_text(encoding="utf-8")
    match = re.fullmatch(r"---json\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)", raw)
    if not match:
        raise ValueError("draft needs a ---json header followed by one Markdown article")
    data = json.loads(match[1])
    if not isinstance(data, dict):
        raise ValueError("draft header must be a JSON object")
    allowed = {"seo_title", "tags", "description", "excerpt", "images", "cover", "research"}
    if set(data) - allowed:
        raise ValueError("draft cannot override scope/CTA/policies: unknown header keys " + ", ".join(sorted(set(data) - allowed)))
    for key in ("seo_title", "description"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError("draft needs " + key)
    if "excerpt" in data and (not isinstance(data["excerpt"], str) or not data["excerpt"].strip()):
        raise ValueError("excerpt must be a non-empty article summary")
    if not isinstance(data.get("tags"), list) or not data["tags"] or any(not isinstance(x, str) or not x.strip() for x in data["tags"]):
        raise ValueError("draft needs non-empty tags")
    lines = match[2].strip().splitlines()
    if not lines or not re.fullmatch(r"#\s+\S.*", lines[0]):
        raise ValueError("draft must start with one article title")
    parser = markdown_parser()
    title_tokens = parser.parse(lines[0] + "\n")
    title = "".join(t.content for t in title_tokens[1].children or [] if t.type in {"text", "code_inline"})
    if not title.strip():
        raise ValueError("article title is empty")
    body_markdown = "\n".join(lines[1:]).strip() + "\n"
    tokens = parser.parse(body_markdown)

    def inspect(items):
        for token in items:
            if token.type == "image":
                raise ValueError("body images use explicit BLOG_3P_IMAGE markers, not Markdown image embeds")
            if token.type == "heading_open" and token.tag == "h1":
                raise ValueError("do not duplicate the separately transferred article title in body")
            if token.type in {"html_inline", "html_block"} and not re.fullmatch(r"\s*<!--\s*BLOG_3P_IMAGE:\d{2}\s*-->\s*", token.content):
                raise ValueError("raw HTML is not an authoring surface; use Markdown or fenced code")
            if token.children:
                inspect(token.children)
    inspect(tokens)
    return data, title.strip(), body_markdown, tokens, parser.renderer.render(tokens, parser.options, {})


def safe_asset(root, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("image record needs file")
    relative = Path(value)
    resolved = (root / relative).resolve()
    if relative.is_absolute() or ".." in relative.parts or root.resolve() not in resolved.parents or not resolved.is_file():
        raise ValueError("image file must exist inside the article root")
    return resolved


def project_draft(source, context, root):
    """Pure projections except reading declared source/assets; no source checking claims."""
    I = integrity()
    data, title, body_md, tokens, body_html = read_draft(source)
    article = context.get("frozen_article", {})
    plan = context.get("prewrite_plan", {})
    cta = article.get("cta")
    if not isinstance(cta, dict) or cta.get("mode") != "SECONDARY_RECOMMENDATION":
        raise ValueError("owner-frozen required CTA is missing")
    research = data.get("research")
    if not isinstance(research, dict):
        raise ValueError("draft research notes are required; not a separate research report")
    sources = research.get("sources", [])
    if not isinstance(sources, list) or not sources or any(not isinstance(s, dict) or not s.get("id") or not s.get("url") for s in sources):
        raise ValueError("research sources need id and URL")
    ids = [s["id"] for s in sources]
    if len(set(ids)) != len(ids):
        raise ValueError("research source IDs must be unique")
    basis = research.get("keyword_basis")
    refs = research.get("keyword_refs", [])
    if basis not in {"CURRENT_BRAND_SITE", "REGIONAL_SERP", "MODEL_TRANSLATION_FALLBACK"} or not isinstance(refs, list) or not refs or any(x not in ids for x in refs):
        raise ValueError("record an actual keyword basis and its source IDs")
    if basis == "MODEL_TRANSLATION_FALLBACK" and len(set(refs)) < 2:
        raise ValueError("translation fallback needs two recorded regional checks")
    focus = research.get("focus_keyword")
    required = context.get("keyword_requirements", [])
    if not focus:
        if required and required[0]["language"].split("-")[0] == str(article.get("language", "")).split("-")[0]:
            focus = required[0]["phrase"]
        elif required:
            raise ValueError("record the natural localized focus keyword")
        else:
            focus = article.get("focus_keyword")
    if not isinstance(focus, str) or not focus.strip():
        raise ValueError("focus keyword is missing")
    metadata = {
        "canonical_title": title, "platform_title": title, "seo_title": data["seo_title"],
        "tags": data["tags"], "description": data["description"],
        "language": article.get("language"), "primary_keyword": focus,
    }
    if "excerpt" in data:
        metadata["excerpt"] = data["excerpt"]
    assets = data.get("images", [])
    if not isinstance(assets, list) or any(not isinstance(a, dict) for a in assets):
        raise ValueError("images must be a list")
    actual_markers = []
    for token in tokens:
        if token.type == "html_block":
            match = re.fullmatch(r"\s*<!--\s*BLOG_3P_IMAGE:(\d{2})\s*-->\s*", token.content)
            if match:
                actual_markers.append((int(match[1]), token.map))
    if [x[0] for x in actual_markers] != list(range(1, len(assets) + 1)):
        raise ValueError("each body image needs one ordered marker at its actual position")
    manifest_assets = []
    visible_parser_class = load_module("blog_payload_compiler_projection", Path(__file__).with_name("build_visual_payload.py")).CTAContentParser
    for ordinal, item in enumerate(assets, 1):
        file = safe_asset(root, item.get("file"))
        match = re.fullmatch(rf"{ordinal:02d}-(lead|middle|closing)-.+\.(png|jpe?g)", file.name, re.I)
        if not match:
            raise ValueError("body images need numbered lead/middle/closing PNG/JPG naming")
        # Whitespace variants of the marker have the same source position.
        prefix = re.split(r"<!--\s*BLOG_3P_IMAGE:" + f"{ordinal:02d}" + r"\s*-->", body_html)[0]
        visible = visible_parser_class()
        visible.feed(prefix)
        anchor = next((part.strip() for part in reversed(visible.body_text) if part.strip()), "")
        if not anchor:
            raise ValueError("image position needs preceding readable context")
        if not item.get("caption"):
            raise ValueError("body image needs a reader caption")
        manifest_assets.append({
            **item, "ordinal": ordinal, "coverage_zone": match[1].upper(),
            "sha256": I.digest(file), "placement_anchor": anchor,
            "adjacent_claim_id": item.get("adjacent_claim_id", f"EDITORIAL-{ordinal:02d}"),
            "reader_job": item.get("reader_job", plan.get("topic_slot", {}).get("reader_task", "Explain the adjacent reader task.")),
            "placement_reason": "Exact source marker after the recorded anchor.",
            "visual_review_status": "QUALITY_RECEIPT_REQUIRED",
        })
    requirements = context.get("delivery_requirements", {})
    exact = requirements.get("body_image_count")
    minimum = requirements.get("minimum_body_images", exact if exact is not None else 3)
    cover_required = requirements.get("cover_required", True)
    manifest = {"schema_version": "1.0", "assets": manifest_assets}
    if data.get("cover") is not None:
        cover = data["cover"]
        if not isinstance(cover, dict):
            raise ValueError("cover must be a record")
        file = safe_asset(root, cover.get("file"))
        manifest["cover_image"] = {**cover, "sha256": I.digest(file), "visual_review_status": "QUALITY_RECEIPT_REQUIRED"}
    errors = I.check_visuals(manifest, root, cover_required=cover_required, minimum_images=minimum, exact_body_images=exact)
    if errors:
        raise ValueError("; ".join(errors))
    slot = plan.get("topic_slot", {})
    posture = copy.deepcopy(plan.get("evidence_posture", {}))
    claims = research.get("claims", [])
    if not isinstance(claims, list) or any(not isinstance(c, dict) or not c.get("id") or not c.get("text") or not c.get("source_refs") or any(s not in ids for s in c["source_refs"]) for c in claims):
        raise ValueError("claims need id, text and actual source_refs")
    selection = {"focus_keyword": focus}
    for key in ("requirement_id", "preserved_meanings", "localization_rationale"):
        if key in research:
            selection[key] = research[key]
    evidence = {
        "schema_version": "1.3", "article_id": context.get("article_id"),
        "source_records": [{**s, "source_id": s["id"], "verification": "AUTHOR_RECORDED_NOT_MACHINE_VERIFIED"} for s in sources],
        "reader_task": slot.get("reader_task"),
        "intent_and_angle": {"selected": slot.get("differentiation_angle"), "alternatives_rejected": []},
        "topic_slot_alignment": {"frozen_slot_id": slot.get("slot_id"), "status": "ALIGNED", "within_slot_adjustments": research.get("adjustments", []), "resolved_conflicts": [], "active_conflict": None},
        "keyword_and_localization": selection,
        "research_separation": {
            "reader_intent_basis": {"decision": basis, "selected_phrase_evidence_refs": refs, "notes": research.get("keyword_notes", "")},
            "platform_profile_use": {"mode": "NOT_USED", "evidence_refs": [], "used_as_keyword_or_demand_evidence": False},
        },
        "evidence_posture": posture, "claims": [{**c, "claim_id": c["id"]} for c in claims],
        "visual_jobs": [{"coverage_zone": a["coverage_zone"], "adjacent_claim_id": a["adjacent_claim_id"], "reader_job": a["reader_job"]} for a in manifest_assets],
        "uncertainties_and_non_claims": research.get("uncertainties", []),
    }
    statistics, errors = I.check_links(body_html, context.get("link_policy"), cta)
    if errors:
        raise ValueError("; ".join(errors))
    compiler = load_module("blog_payload_compiler_cards", Path(__file__).with_name("build_visual_payload.py"))
    compiler.ensure_body_preserves_cta(body_html, cta)
    lines = body_md.splitlines()
    for (ordinal, span), asset in reversed(list(zip(actual_markers, manifest_assets))):
        lines[span[0]:span[1]] = compiler.markdown_image_card(asset).splitlines()
    return {
        "canonical": body_html,
        "metadata": dump_text(metadata), "visual_manifest": dump_text(manifest),
        "evidence_pack": dump_text(evidence), "markdown_body": "\n".join(lines).strip() + "\n",
        "title": title, "link_statistics": statistics, "cover_required": cover_required,
        "minimum_body_images": minimum, "body_image_count": exact,
    }


def verify_author_projection(package, root):
    record = package.get("author_source")
    if record is None:
        return None
    if not isinstance(record, dict) or record.get("path") != "canonical/article.md" or record.get("context_path") != "context/article-contract.json":
        raise ValueError("author_source paths are invalid")
    I = integrity()
    source = safe_asset(root, record["path"])
    context_path = safe_asset(root, record["context_path"])
    if I.digest(source) != record.get("sha256") or I.digest(context_path) != record.get("context_sha256"):
        raise ValueError("author Markdown/context changed; prepare and rebind the affected quality receipt")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    expected = project_draft(source, context, root)
    for key, relative in (("canonical", "canonical/article.html"), ("metadata", "canonical/metadata.json"), ("visual_manifest", "canonical/visual-manifest.json"), ("evidence_pack", "research/evidence-pack.json")):
        if safe_asset(root, relative).read_text(encoding="utf-8") != expected[key]:
            raise ValueError("derived " + key + " was edited independently of the author Markdown")
    if package.get("cta") != context.get("frozen_article", {}).get("cta") or package.get("link_policy", {}) != context.get("link_policy", {}):
        raise ValueError("package CTA/link policy differs from owner-frozen context")
    return expected


def prepare(workspace, article_id):
    harness = load_module("blog_prepare_harness", Path(__file__).resolve().parents[2] / "blog-harness/scripts/harnessctl.py")
    root = workspace / "articles" / article_id
    context_path = root / "context/article-contract.json"
    errors = harness.article_context_errors(workspace, context_path)
    if errors:
        raise ValueError("; ".join(errors))
    context = json.loads(context_path.read_text(encoding="utf-8"))
    source = root / "canonical/article.md"
    expected = project_draft(source, context, root)
    I = integrity()
    previous = {}
    package_path = root / "article-package.json"
    if package_path.exists():
        previous = json.loads(package_path.read_text(encoding="utf-8"))
        if "author_source" not in previous:
            raise ValueError("existing legacy package: do not silently migrate; use the confirmed legacy route")
    outputs = {
        "canonical/article.html": expected["canonical"],
        "canonical/metadata.json": expected["metadata"],
        "canonical/visual-manifest.json": expected["visual_manifest"],
        "research/evidence-pack.json": expected["evidence_pack"],
    }
    # Validate before writing a candidate, not after partially changing artifacts.
    compiler = load_module("blog_prepare_preview", Path(__file__).with_name("build_visual_payload.py"))
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        metadata_path = Path(temporary) / "metadata.json"
        metadata_path.write_text(expected["metadata"], encoding="utf-8")
        candidate_html, _ = compiler.render_payload_pair(
            title=expected["title"], body=expected["canonical"],
            image_items=json.loads(expected["visual_manifest"])["assets"],
            metadata_path=metadata_path, title_transfer_mode="SEPARATE_TITLE_FIELD",
            markdown_body=expected["markdown_body"],
        )
    keyword_errors = harness.keyword_delivery_errors(context, json.loads(expected["evidence_pack"]), json.loads(expected["metadata"]), candidate_html)
    if keyword_errors:
        raise ValueError("; ".join(keyword_errors))
    changed = any(not (root / rel).exists() or (root / rel).read_text(encoding="utf-8") != text for rel, text in outputs.items())
    for relative, text in outputs.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    article = context["frozen_article"]
    roles = {
        "metadata": "SINGLE_SOURCE_FOR_TITLE_AND_SEO_METADATA",
        "visual_manifest": "SINGLE_SOURCE_FOR_IMAGE_ASSETS_ALT_CAPTIONS_AND_PLACEMENT",
        "evidence_pack": "ARTICLE_CLAIM_AND_SEO_DECISION_INDEX",
    }
    package = {
        "schema_version": "1.5", "article_id": article_id,
        "canonical_path": "canonical/article.html", "canonical_sha256": I.digest(root / "canonical/article.html"),
        "canonical_format": "RICH_TEXT_HTML_FRAGMENT",
        "artifact_sources": {key: {"path": relative, "sha256": I.digest(root / relative), "role": roles[key]} for key, relative in (("metadata", "canonical/metadata.json"), ("visual_manifest", "canonical/visual-manifest.json"), ("evidence_pack", "research/evidence-pack.json"))},
        "title_transfer_mode": previous.get("title_transfer_mode", "SEPARATE_TITLE_FIELD"),
        "visual_payload_template": {"id": "BLOG_3P_VISUAL_PAYLOAD", "version": "3", "rendering": "COMPILER_ONLY"},
        "reader_value_promise": article["reader_value_promise"], "cta": article["cta"],
        "link_policy": context.get("link_policy", {}),
        "visual_narrative": {"minimum_images": expected["minimum_body_images"], "body_image_count": expected["body_image_count"], "required_coverage_zones": ["LEAD", "MIDDLE", "CLOSING"] if expected["minimum_body_images"] >= 3 else [], "cover_image_required": expected["cover_required"]},
        "author_source": {"path": "canonical/article.md", "sha256": I.digest(source), "context_path": "context/article-contract.json", "context_sha256": I.digest(context_path)},
        "review_status": "PENDING", "gate_status": "PENDING",
    }
    package["artifact_sources"]["manual_retelling"] = "PROHIBITED"
    if previous:
        for key in ("review_status", "gate_status"):
            if key in previous and previous.get("author_source") == package["author_source"] and previous.get("artifact_sources") == package["artifact_sources"]:
                package[key] = previous[key]
    changed = changed or bool(previous and previous != package)
    package_path.write_text(dump_text(package), encoding="utf-8")
    compiler = load_module("blog_prepare_compiler", Path(__file__).with_name("build_visual_payload.py"))
    html, markdown = compiler.render_payload_pair(
        title=expected["title"], body=expected["canonical"],
        image_items=json.loads(expected["visual_manifest"])["assets"],
        metadata_path=root / "canonical/metadata.json", title_transfer_mode=package["title_transfer_mode"],
        markdown_body=expected["markdown_body"],
    )
    (root / "handoff").mkdir(exist_ok=True)
    (root / "handoff/visual-payload.html").write_text(html, encoding="utf-8")
    (root / "handoff/visual-payload.md").write_text(markdown, encoding="utf-8")
    index_path = root / "reviews/review-index.json"
    if not index_path.exists():
        harness.build_review_index(workspace, context_path, index_path, None)
    elif changed:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        receipt = index.get("latest_author_qa", {})
        if receipt.get("status") == "AUTHOR_QA_READY":
            index.setdefault("superseded_quality_receipts", []).append(copy.deepcopy(receipt))
            receipt["status"] = "PENDING"
            for field in ("receipt_path", "receipt_sha256", "author_agent_id"):
                receipt[field] = None
        index["canonical"] = {"path": harness.relative_path(workspace, root / "canonical/article.html"), "sha256": I.digest(root / "canonical/article.html")}
        index_path.write_text(dump_text(index), encoding="utf-8")
    trace = root / "requirements-traceability.md"
    trace.write_text(
        "# 自动生成的需求位置索引（不是质量结论）\n\n"
        "用户依据：context/article-contract.json；正文：canonical/article.md。\n"
        "CTA、语言、关键词与图片：上述稿件和同源发布页；发现的语义问题仍由质量角色记录。\n",
        encoding="utf-8",
    )
    print("PREPARED_NOT_QUALITY_APPROVED")
    print("link_counts=" + json.dumps(expected["link_statistics"], ensure_ascii=False))
    print("source=canonical/article.md; delivery=handoff/visual-payload.html + visual-payload.md")


def bind_author_qa(workspace, article_id, agent_id, note):
    """Record an existing visible W self-review, never generate a review verdict."""
    import hashlib
    if not agent_id or not note:
        raise ValueError("binding needs the actual author agent ID and their short quality conclusion")
    harness = load_module("blog_bind_harness", Path(__file__).resolve().parents[2] / "blog-harness/scripts/harnessctl.py")
    root = workspace / "articles" / article_id
    context_path, index_path = root / "context/article-contract.json", root / "reviews/review-index.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    if context.get("review_effort", {}).get("quality_mode") != "WQ_SHARED_CONTEXT":
        raise ValueError("author binding cannot replace an owner-selected independent R review")
    state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
    turns = state.get("orchestration", {}).get("tasks", [])
    if not any(t.get("article_id") == article_id and t.get("agent_id") == agent_id and t.get("role") == "ARTICLE_WRITER" and t.get("workflow_stage") == "AUTHOR_QA" and t.get("status") == "COMPLETED" for t in turns if isinstance(t, dict)):
        raise ValueError("record the actual visible AUTHOR_QA turn in the existing controller ledger first")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("open_findings"):
        raise ValueError("cannot bind readiness while real findings remain open")
    errors = harness.review_ready_errors(workspace, context_path, index_path, root / "article-package.json")
    if errors:
        raise ValueError("; ".join(errors))
    hashes = harness.final_artifact_hashes(workspace, context, index["canonical"])
    receipt = {
        "schema_version": "1.0", "article_id": article_id,
        "quality_mode": "WQ_SHARED_CONTEXT", "result": "AUTHOR_QA_READY",
        "protocol": harness.AUTHOR_QA_PROTOCOL,
        "candidate_canonical_sha256": index.get("latest_author_qa", {}).get("candidate_canonical_sha256") or hashes["canonical_sha256"],
        "final_artifact_hashes": hashes, "findings": [], "open_finding_ids": [],
        "author_agent_id": agent_id, "note": note, "basis": "EXISTING_VISIBLE_AUTHOR_QA_TURN",
    }
    text = dump_text(receipt)
    receipt_name = "author-qa-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] + ".json"
    receipt_path = root / "reviews" / receipt_name
    receipt_path.write_text(text, encoding="utf-8")
    index["latest_author_qa"] = {
        **index.get("latest_author_qa", {}), **hashes,
        "status": "AUTHOR_QA_READY", "author_agent_id": agent_id,
        "receipt_path": harness.relative_path(workspace, receipt_path),
        "receipt_sha256": integrity().digest(receipt_path),
        "self_qa_protocol": harness.AUTHOR_QA_PROTOCOL,
        "candidate_canonical_sha256": receipt["candidate_canonical_sha256"],
        "open_finding_ids": [],
    }
    index_path.write_text(dump_text(index), encoding="utf-8")
    errors = harness.review_index_errors(workspace, index_path, require_full_approved=True)
    if errors:
        raise ValueError("; ".join(errors))
    print("AUTHOR_QA_RECORDED_FROM_VISIBLE_TURN")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--brief", action="store_true")
    parser.add_argument("--bind-author-qa", action="store_true")
    parser.add_argument("--agent-id")
    parser.add_argument("--note", help="The existing author's actual conclusion, not a CLI-generated review")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.article_id):
        parser.error("unsafe article ID")
    try:
        if args.brief and args.bind_author_qa:
            raise ValueError("choose brief or author receipt binding, not both")
        if args.bind_author_qa:
            bind_author_qa(args.workspace.resolve(), args.article_id, args.agent_id, args.note)
        elif args.brief:
            context_path = args.workspace / "articles" / args.article_id / "context/article-contract.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            a = context["frozen_article"]
            slot = context["prewrite_plan"]["topic_slot"]
            print("读者问题：" + slot["reader_task"])
            print("本篇角度：" + slot["differentiation_angle"])
            print("语言/市场：" + a["language"] + " / " + a["market"])
            print("平台：" + str(context.get("platform_assignment", {}).get("platform")))
            print("关键词要求：" + json.dumps(context.get("keyword_requirements", []), ensure_ascii=False))
            print("CTA：" + json.dumps(a["cta"], ensure_ascii=False))
            print("链接数量/图片要求：" + json.dumps({"link_policy": context.get("link_policy", {}), "delivery_requirements": context.get("delivery_requirements", {"minimum_body_images": 3, "cover_required": True})}, ensure_ascii=False))
            print("禁止偏离：" + "; ".join(slot["forbidden_deviations"]))
        else:
            prepare(args.workspace.resolve(), args.article_id)
    except (ValueError, OSError, KeyError) as exc:
        print("PREPARE_FAILED\n" + str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
