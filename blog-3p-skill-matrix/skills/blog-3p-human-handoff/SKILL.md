---
name: blog-3p-human-handoff
description: Compile and locally validate a minimal browser-opened visual blog hand-off in a fixed title, annotated body, SEO title, tags, description order. Use when a reviewed blog article needs a human-friendly native publishing package without editor or API automation.
---

# Blog 3P Human Handoff

Compile a final pre-publication audit surface—not raw HTML source and not a second adaptation draft. This Skill has no platform login, editor, upload, publish, delete or rollback action.

## Inputs and output

Require an approved canonical package, `article-package.json`, `canonical/metadata.json`, `local-seo-issues-reference.md`, a declared title/body transfer mode, and the in-scope platform `format-profile.md` when one is available.

### Compact source chain

- `article-package.json.artifact_sources.evidence_pack` is the article claim/SEO decision index.
- `article-package.json.artifact_sources.visual_manifest` is the only source for image assets, localized Alt, captions, positions and coverage.
- `article-package.json.artifact_sources.handoff_manifest` inventories derived hand-off artifacts and their hashes.

Do not manually retell those records in the release card, payload annotations, or local precheck. The only accepted output is compiler-generated `BLOG_3P_VISUAL_PAYLOAD@2`: W supplies title, canonical outline/body fragment, the one visual manifest and SEO metadata, but must not hand-author `visual-payload.html`, its shell, CSS, JavaScript, buttons, cards or operation order. Preserve the approved `reader_value_promise` and required CTA's exact visible anchor text, declared href and applicable visible disclosure; do not add a different CTA or platform-side promotional copy. Pass `--article-package article-package.json` to both `scripts/build_visual_payload.py` and `scripts/validate_payload.py`; they reject a missing, changed or untransported required CTA. A missing/`UNVERIFIED` editorial style profile is never a compiler failure.

The page is deliberately plain and always reads top to bottom: blog title, article body with image annotations at the intended positions, SEO title, tags, description. It has no copy button, clipboard script, or platform-specific controls. The publisher manually selects the visible title and body in the browser, then pastes them into the native editor. `SEPARATE_TITLE_FIELD` means that title and body are selected separately; `TITLE_IN_BODY` is for targets without a distinct title field. The old `BODY_H1_REQUIRED` value is accepted only as an input compatibility alias and is normalized to `TITLE_IN_BODY`. The payload's local `<h1>`/`<h2>`/`<h3>` markup only helps authoring and rich-text selection. It never promises, proves, or gates the target platform's final heading tags.

Render local image positions as numbered Chinese annotations with file, coverage zone, complete localized Alt text and caption. Empty Alt text must fail compilation; do not replace it with a placeholder. The canonical input may contain article content and outline markers only; scripts, styles, layout-shell tags, custom controls and `<img>` are rejected because the fixed template owns layout and image annotations. Preserve actual anchors and the readable source outline in the body. For an applicable `LEAD`/`MIDDLE`/`CLOSING` policy, invoke `validate_payload.py` with the required zones and minimum annotation count; it verifies the fixed-template signature, fixed top-down order, visible Alt text, and the frozen CTA anchor/href/disclosure transport. Any locally reported heading markup is diagnostic only. Add `RELEASE-CARD.md`, the linked visual and link manifests, fingerprint, local precheck and `handoff/handoff-manifest.json` to the hand-off directory. The handoff manifest records the canonical, evidence-pack, visual-manifest, payload, release-card, local-precheck and R-delta paths plus their hashes; it is an index, not a second prose or SEO document.

## Final audit

Compile only after canonical text, SEO fields, links, reader-value promise and frozen CTA are stable. Then the article's existing R performs one narrow final `VISUAL_PAYLOAD_DELTA`: inspect the one visual manifest, final assets/visual review sheet, compiled payload and only the fields they transport. It confirms image-to-adjacent-copy fitness, legibility, distinct reader jobs, required coverage zones, localized Alt/captions, CTA anchor/href/disclosure transport, and fixed-template fidelity. It does not repeat the prose, fact, title, localization or commercial-balance review that already produced the text lock. On approval, record the same R's `APPROVED` final receipt with report path/hash, R ID, review-index hash, visual-manifest hash and visual-payload hash, plus its completed visible `VISUAL_PAYLOAD_DELTA` task receipt. If any canonical text, metadata, link, source, CTA or reader-value field changed, this is not a visual delta: return to the existing W → R repair path.

After R approves that narrow delta, G validates only the handoff manifest hashes, applicable `REQ-*` traceability and the compact same-R receipt chain before human release; G does not replace R's image or editorial judgment. The hand-off check must find the registered R's completed visible `RESEARCH_REVIEW`, `FULL_REVIEW`, and `VISUAL_PAYLOAD_DELTA` receipts, with report paths/hashes recorded in `reviews/review-index.json`. A published reader-page mismatch instead stays with the existing article-lane G for the read-only public check and does not restart W/R unless the owner explicitly requests a canonical/payload correction. A passing machine check proves only packaging invariants; it cannot establish final heading hierarchy.

## Public return receipt and snapshot

After a human publishes or updates the reader page, copy `templates/public-return-receipt.json` into `handoff/public-return-receipt.json`. It names the public URL, exact `HUMAN_ACCEPTED` or `HUMAN_NEEDS_FIX` state, return time, known revision/timestamp or `UNVERIFIED`, rendered-page evidence paths, and any already known platform limitation. A limitation is valid only when it is scoped to platform, account/site, editor/theme, locale/market and observation date, has evidence and affected contract items, and says `not_generalizable: true`.

Run `harnessctl.py check-public-return-receipt` first. For `HUMAN_ACCEPTED`, run `scripts/capture_public_snapshot.py` with the receipt and the approved `article-package.json`; it makes a bounded HTTP GET only (or reads an explicitly supplied local HTML fixture) and writes `evidence/public-qa/public-snapshot.json`. It does not log in, edit a page, upload, publish, or infer heading levels. `HUMAN_NEEDS_FIX` deliberately skips capture and remains a human platform-side task.

The existing lane G—not R, W, a fresh public reviewer, or a new worktree—uses the receipt and snapshot to write the compact `gate/public-qa-report-N.md`. Its per-article publication record must bind the receipt timestamp, local artifact paths, existing G ID, attempt and `unverified_retry_count`; G appends a timestamped `PUBLIC_QA_READONLY` task row pointing to that report. It classifies `PUBLIC_QA_PASSED`, `PUBLIC_QA_PASSED_WITH_LIMITATION`, `HUMAN_TRANSPORT_FIX_REQUIRED`, `PUBLIC_QA_UNVERIFIED`, or `CANONICAL_CHANGE_REQUESTED`. Transport fixes return to the human in one consolidated checklist and then to this same G. `CANONICAL_CHANGE_REQUESTED` requires an explicit owner request ID and is the only route back to W → R → G.

## Reader-page hierarchy acceptance

After the human returns both a public URL and `HUMAN_ACCEPTED`, the existing lane G judges heading hierarchy **only** from the rendered public reader page. Capture sufficient visual evidence to judge that the page title, section headings and subsection headings are visibly distinguished, correctly ordered and not visibly duplicated or flattened. If the receipt has no usable visual path, this same G may make one bounded, read-only browser capture before reporting `PUBLIC_QA_UNVERIFIED`; it must not create another agent or open a platform editor. The JSON snapshot may record that visual evidence was supplied, but cannot decide this question. Do not inspect, rely on, or ask the human to edit the platform editor's HTML/DOM; it is not a valid acceptance surface. Public source or feed markup also cannot override the visual hierarchy verdict. Missing or inconclusive rendered-page evidence is `PUBLIC_QA_UNVERIFIED`; a visible hierarchy mismatch is a stable `PUBLIC-VISUAL-HIERARCHY-NNN` finding for the owner's human-correction decision and recheck.

Read `../../docs/contracts.md`, `../../docs/compatibility.md` and `../../docs/no-publish-boundary.md`.
