# Blog 3P Skill Matrix

[简体中文](README.zh-CN.md) · Version 0.9.21 · [MIT](LICENSE)

An open-source Skill suite for high-quality, auditable blog production. It turns article work into a recoverable local workflow: establish a campaign and its scope, perform evidence-backed writing, run independent review and final gating, then compile a visual rich-text package for a human publisher. It automates content-quality work, not platform publishing.

## At a glance

| This matrix does | This matrix deliberately does not do |
| --- | --- |
| Preserves owner scope, research evidence, a canonical article, independent article review, requirements acceptance, and a copy-ready rich-text hand-off. | Log in, operate a platform editor, upload media, call publishing APIs, publish, delete, roll back, schedule, or alter browser fingerprints. |

Use it for local-first editorial production when a human, rather than an automation, owns the final native-platform action. It works with Python 3.9+ and the local filesystem; web, Trends, SERP, and public-page checks are optional read-only evidence adapters.

## Why this exists

Typical “write an SEO post” flows mix research, drafting, review, platform adaptation, and publication in one conversation. Sources disappear, review becomes self-review, editor experimentation consumes delivery capacity, and the reader page can drift from the local draft.

This project separates those concerns into explicit Skills while keeping one canonical article and a traceable record of reader-visible changes. A visible platform-matching researcher evaluates only owner-supplied candidates before the owner locks a mapping; a harness preserves scope and state; one executable Writer integrates research with drafting; the reusable Writer–Reviewer inner loop makes article-quality decisions; and a Gatekeeper confirms that the final delivery still honors the owner's frozen task contract. `blog-writer-merged` is an editorial-core reference, not a second Writer workflow. A human uses the platform’s native editor for the final release.

## Operating model

- **G earns the right to dispatch.** Before any article worktree or W/R exists, the persistent visible controller gathers and reports a complete per-article pre-write research and writing plan. It waits for `OWNER_PREWRITE_PLAN_CONFIRMED`, hash-binds that report and manifest to the task contract, then records only confirmed owner requirements in `requirements-contract.md`, maintains campaign state and priority, and accepts final contract fidelity. It never becomes an invisible CLI review session.
- **Each article has one executable W and one persistent R.** `blog-3p-writer` is the only active Writer role; it and the language Reviewer remain with that article through research, drafting, repair, full review, and delta review. They are not shared with another article. R owns article quality, including SEO; W maintains `requirements-traceability.md`.
- **Worktree isolation is explicit.** A visible child task is not automatically a Git worktree. Only after pre-write confirmation, where the host supports project worktrees, G creates one visible worktree task per ready independent article before W/R starts. Otherwise it records `WORKTREE_UNAVAILABLE` and may use a visibly labeled shared-workspace fallback only for disjoint article paths.
- **Each worktree contains a complete article lane.** Its root is an article-level G, which creates and reuses that worktree's W and R through `G → W ↔ R → G`. Campaign G remains the sole global requirements, queue, and state controller; it consolidates lane reports instead of duplicating their editorial work.
- **Quality and owner intent are distinct checks.** R decides whether the article is good. Once R approves, G checks whether any confirmed owner requirement was lost, substituted, weakened, or expanded; G does not redo prose or SEO review.
- **Ordinary turns use a compact evidence index.** At dispatch, lane G creates an immutable hash-bound article contract. R maintains a review index and W adds a delta capsule for a bounded repair. Normal turns read those records plus changed artifacts; a full historic reread remains mandatory only after compaction, hash drift, unresolved finding lineage, or escalation. Agent replacement and scope conflict are escalation conditions.
- **Reader value comes first; CTA is required but secondary.** Each article has a frozen reader-value promise and must remain useful without relying on its CTA. The owner-required CTA preserves its exact visible anchor text, identifiable product, current destination, claim basis, reader-task relevance, and any applicable relationship disclosure. R judges meaning and commercial balance; G checks declaration-to-delivery fidelity.
- **Images carry a narrative, not a quota.** For substantive guides, tutorials, comparisons, reviews, and long explainers, W plans at least three original information-bearing visuals across `LEAD`, `MIDDLE`, and `CLOSING`. R opens every asset and tests its adjacent claim, legibility, distinct reader job, and non-redundancy; a hero, filename, dimensions, or alt text alone cannot pass.
- **Research is a pre-draft gate, not an angle label.** The owner first confirms G's directional dossier; then every article records its actual long-tail reader intent and evidence before outlining, and every target language records regional-SERP natural variants. Multi-English batches require distinct intent IDs and reader questions. The reusable R approves this W research package before W may draft.
- **Platform samples are advisory profiles, not borrowed templates.** One reusable operations steward may inspect only authorized platforms' public same-language/same-format samples. It writes a deterministic format profile for the hand-off and a non-binding editorial profile for reader fit. A shortage is `UNVERIFIED`, uses a conservative generic structure, and never blocks research or drafting.
- **Public QA reuses the lane G only.** After a human records the URL, exact `HUMAN_ACCEPTED`/`HUMAN_NEEDS_FIX` state and known limits in a structured return receipt, the same article's existing `ARTICLE_LANE_GATEKEEPER` receives a bounded read-only public snapshot and makes one narrow comparison against the accepted canonical/payload. It does not restart W/R, create a fresh public gate, or redo article SEO/prose review. It classifies pass, scoped pass-with-limitation, human transport repair, unverified evidence, or an explicit canonical-change request.
- **Heading hierarchy is visual-public only.** Canonical and payload tags help authoring and copy selection, but never prove platform transport. A human does not edit editor HTML/DOM; after `HUMAN_ACCEPTED`, lane G accepts title, section and subsection hierarchy only from rendered public reader-page evidence. The snapshot can record a visual-evidence path, but cannot infer a hierarchy verdict.
- **Platform matching is delegated, selection is confirmed.** Before a human-release map exists, one visible reusable `CAMPAIGN_PLATFORM_MATCHING_RESEARCHER` evaluates only owner-supplied candidates against frozen language, market and format needs. G does not rank or choose; it preserves the report and obtains the owner's exact platform/account confirmation.
- **CLI stays mechanical.** It may run deterministic local checks and compilers, but cannot substitute for a reviewer or manufacture evidence.

## Architecture

```text
Owner task and source-bounded candidates
        │
        ▼
G pre-write dossier (one plan per article)
        │
        ▼
OWNER_PREWRITE_PLAN_CONFIRMED + hash binding
        │
        ▼
Visible article worktree / lane G ──► W integrated research ──► same R: RESEARCH_APPROVED
                                        │
                                        ▼
                               W canonical package ↔ reusable R review
                                                        │
                                                        ▼
                                                 G final decision
                                                        │
                                  PASS = HUMAN_RELEASE_READY
                                                        │
                                                        ▼
                                     Visual rich-text human hand-off
                                                        │
                                                        ▼
       Human native publish → return receipt + read-only snapshot → same lane G check
```

`PASS` never means that a machine published the post. It means that the local editorial artifact is ready for a human to use. Completion is separate: the human saves a URL/state return receipt, then for `HUMAN_ACCEPTED` that article's existing lane G performs a bounded read-only reader-page contract check using a normalized snapshot plus rendered visual evidence. W/R do not run again for a public mismatch: a transport repair returns to the human and same G; only an explicit owner-requested canonical or payload correction reopens W/R.

The pre-write dossier is also not a shortcut around research. It reports G's evidence, known limits, and proposed writing route so the owner can correct the plan before costly article lanes begin. After approval, W independently performs the full source, long-tail, and localization research; R remains the only role that can issue `RESEARCH_APPROVED`.

## Skill matrix

| Skill | Responsibility | Main outputs |
| --- | --- | --- |
| `blog-3p-harness` | Initializes an isolated campaign, records the owner-confirmed pre-write plan, locks scope, resumes safely, and runs structural checks. | `campaign.json`, `state.json`, `prewrite-plan.md/json`, confirmation, checklist |
| `blog-3p-platform-matching` | Visible reusable subagent that researches language/market/format fit within the owner candidate source and recommends one platform per article. | Matching report and pending-owner-confirmation proposal |
| `blog-writer-merged` | Editorial-core reference for evidence, localization, reader value, images, and title quality. It is never a second W lane. | Reusable editorial standards and references |
| `blog-3p-writer` | The sole article-scoped Writer (W): research, draft, repair, and compile the reviewed package. | Article package, fingerprint, resolution record, delta capsule |
| `blog-3p-review` | Article-scoped, reusable language Reviewer (R) checks that article's content, evidence, title/body hand-off, and stable findings across review rounds. | `reviews/review-N.md` |
| `blog-3p-gate` | Persistent Gatekeeper (G) collects and reports the pre-write plan, waits for owner confirmation, then manages scope, queue, owner-contract traceability, final decisions, and the same-lane post-publication check. | plan binding, `requirements-contract.md`, `gate/gate-report-N.md`, `gate/public-qa-report-N.md` |
| `blog-3p-human-handoff` | Compiles a minimal browser-opened hand-off and captures bounded return evidence after human release. | `handoff/visual-payload.html`, return receipt, release card, public snapshot |

The matrix is deliberately modular. An organization can use the harness and engine without a human-release package, or use the W–R–G loop on an existing canonical article. The contracts remain consistent.

## Core guarantees

### One canonical article, independent judgment

W writes. R reviews without editing and owns article quality, including SEO. G owns state and accepts only whether the frozen user contract survived into final delivery; it does not duplicate R's prose/SEO review. Owner requirements use `REQ-*` IDs, while G-only gaps use `REQUIREMENT-*` and quality findings retain IDs such as `SEO-LOCALIZATION-001`.

Every reader-visible change to the canonical article or visual payload updates the canonical fingerprint and takes the appropriate R/G path again. A reader-page mismatch by itself stays with the existing lane G and does not reopen W/R.

### Compact, hash-bound article context

At dispatch, lane G writes `context/article-contract.json`: a projection of the confirmed article scope, applicable `REQ-*`, reader-value/CTA declaration, language/market, applicable release mapping, and source hashes. R maintains `reviews/review-index.json` with the current canonical/package hashes, report pointers, decision and stable finding lineage. These records reduce repeated context loading; they cannot alter scope or override source evidence.

For a bounded repair, W adds `reviews/review-delta-N.json` with the approved baseline hashes, exact changed paths, affected claims/requirements/findings, and explicit flags for sources, localization, title/metadata, CTA, images and payload. R-Δ examines that capsule, changed artifacts and direct dependencies. Full historical reread is still required only after compaction, hash drift, unresolved or ambiguous lineage, or escalation; replacement and scope conflict are escalation conditions. Full R still reads the complete current canonical package and every final image.

### Reader value first; transparent recommendations second

The primary outcome is a high-quality, evidence-bounded answer to the reader's task. Every new schema-`2.2+` article freezes a `reader_value_promise`; the article must still be coherent and useful if its CTA is removed. `cta.mode = NONE` is not valid in a new schema-2.2 campaign.

Every schema-2.2 article uses `cta.mode = SECONDARY_RECOMMENDATION`. In the current schema-2.5 workflow, `article-package.json` is schema `1.3` and references the canonical evidence, visual, and hand-off manifests while recording the exact visible anchor text, product identity, current destination URL, claim-evidence path, reader-task relevance, and relationship disclosure or `NOT_APPLICABLE`. These fields trace a recommendation; they do not license unsupported claims that a product is independently reliable, best, tested, available, or suitable for every reader. R—not a count, word-ratio, placement, or density check—judges whether the article remains reader-led, balanced, and truthful. G only confirms that the frozen declaration survived the final package. Schema-2.2/2.3 workspaces retain their historical schema-`1.2` package contract; do not relabel them solely to adopt the newer workflow. This reduces avoidable moderation/deletion risk; it never guarantees a platform will retain a published page.

### Owner-confirmed pre-write plan

Before the matrix spends a worktree or starts a writing/review lane, G maintains one canonical schema-`1.3` `prewrite-plan.json` for every configured article. Each card states the audience/task, independent reader-value promise, required secondary CTA with its exact visible anchor text, destination, claim/source boundary and disclosure, evidence and uncertainty, localization/keyword route, provisional title and outline, visual narrative, transport assumptions, and owner decisions still needed. G runs `harnessctl.py sync-prewrite-plan` to render the human-readable `prewrite-plan.md`. That Markdown file is deterministic and read-only: never hand-edit both files or use it as a second source of scope truth.

`OWNER_PREWRITE_PLAN_CONFIRMED` is a hard dispatch gate. Its ID, article set, report hash, and manifest hash must agree in the state, owner confirmation, requirements contract, and scope lock. A material plan change invalidates that binding. Until it is renewed, G cannot create an article worktree, lane G, W, R, article queue, or article agent. This gives the owner a correction point before parallel work consumes time or tokens without turning G's proposal into a substitute for W/R research.

### Visual narrative coverage

The campaign freezes a `visual_narrative_policy` alongside SEO and scope. The standard policy requires `LEAD`, `MIDDLE`, and `CLOSING` coverage with a minimum of three images for applicable article types. Each manifest entry links an asset to a section anchor, adjacent claim, reader job, rights/source, prompt or brief, localized alt text, caption, and pixel review.

For a uniform no-exception batch, set `all_articles_required: true` before dispatch. This makes the three-image, three-zone rule a hard requirement for every article in that campaign. A policy exception is otherwise owner-confirmed and visible to R; it is never inferred from a missing image. The human hand-off cards show the zone and reader job so a publisher can preserve the intended placement.

### Cross-language SEO without fabricated local evidence

For a frozen multilingual target, wording is selected in this strict order:

```text
CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK
```

- **Current brand site:** a current public brand page for the same locale and reader intent is the highest-priority wording source. This keeps the blog aligned with brand language and its semantic matrix.
- **Regional SERP:** target-region search results establish reader intent and naturally used semantic variants. When usable, Google Trends compares English seeds/candidates only as global relative-interest context and records the English-concept-to-regional-SERP map. Its normalized index is never presented as search volume, low-base/high-momentum proof, local demand, popularity, commercial intent, or model capability.
- **Model translation fallback:** allowed only after two independent regional-SERP checks document that no usable consensus variant exists. The proposed wording, failed checks, rationale, and cultural/legal risk are recorded. It is never labeled as SERP-proven.

A brand-site expression is not copied blindly: it must be rejected with evidence if it is stale, misleading, unnatural, or incompatible with the article’s intent. Regional SERPs are for understanding local intent and phrasing, never for copying competitor text.

### Pre-draft long-tail research

The matrix does not accept an empty keyword-variant field, a generic head term, title copy, or an editorial creative angle as research. Before the owner confirms G's pre-write plan, G reports the proposed keyword/localization route and uncertainty. After that confirmation—and before outline or prose—W records candidate and rejected long-tail terms, a reader problem, query/date/evidence, and the selected wording. A campaign with multiple English articles also keeps an intent register: each primary long-tail term and reader problem must be materially distinct.

For every target language, the record captures target-market SERP queries, natural variants, selected wording source, and rejected literal translations. English-only Google Trends comparisons are optional global relative-interest context, never target-language wording evidence. If they are unavailable or inconclusive, W does not force a trend signal or retry to manufacture one: it selects the long-tail reader problem from the frozen platform's documented audience needs, the brand site, and target-market SERP intent, then records what supports that choice and an explicit evidence boundary. That fallback must not be described as a volume, popularity, momentum, or commercial-demand finding. If two independent regional checks find no usable consensus, the record may use `MODEL_TRANSLATION_FALLBACK`, with both checks and a linguistic rationale. The same R issues `RESEARCH_APPROVED` before W drafts; the final review rechecks that the article did not drift from that research.

### In-scope platform style profiles

After G has frozen the exact platform/account pair, the reusable campaign operations steward may make a best-effort, read-only inspection of public samples for that same platform, language, and content type. It records sources, dates, visible signals, and uncertainty in two separate artifacts:

- `format-profile.md` is deterministic delivery input: supported title/meta fields, title/body transfer guidance, public visual hierarchy observations, and observed list, link, image, commercial-disclosure, or layout constraints. It never directs editor HTML/DOM changes. The human hand-off uses it when it exists.
- `editorial-style-profile.md` is advisory writing input: defensible observations about title tone, opening pattern, paragraph rhythm, and structure. W may use it only to improve reader fit.

Neither artifact proves keyword demand, factual claims, platform policy, or popularity. When global Trends data is insufficient, a dated, comparable editorial profile may instead support a bounded reader-needs rationale for a long-tail; it still cannot be called a demand, popularity, volume, or momentum finding. The profiles cannot alter scope, canonical facts, localized wording priority, the required-secondary CTA policy or its exact anchor/href/disclosure, or the required visual narrative. Never copy sample titles, phrases, argument flow, engagement claims, or promotional patterns. If samples are unavailable, incomplete, or not demonstrably comparable, mark the profile `UNVERIFIED` and use a conservative generic structure; R records no finding for absence alone. Only reader-page behavior verified through `PUBLIC_QA_PASSED` can be harvested into a durable platform skill. A `PUBLIC_QA_PASSED_WITH_LIMITATION` result can contribute only its fully scoped, dated and non-generalizable limitation. See [the profile template](docs/platform-style-profiles.md).

### Human-native publication boundary

The normal release path does **not** log into a platform, type into an editor, upload media, press Publish, delete content, roll back content, use a write API, or alter browser fingerprints. It produces exactly one compiler-owned `BLOG_3P_VISUAL_PAYLOAD@2` page: every article gets the same deliberately plain shell and top-down order—blog title, body with Chinese image annotations, SEO title, tags, description. W supplies only canonical title, source outline/body, image manifest and metadata; it cannot design a per-article shell, CSS, JavaScript or controls. The page has no buttons, clipboard code or copy guarantees: the publisher selects the visible title and body in the browser and uses the native editor. The compiler refuses a package or body that omits or changes the required CTA's exact visible anchor text, href or applicable disclosure; it never adds promotional copy. The publisher must not inspect or edit platform editor HTML/DOM to force title tags. Every annotation visibly prints the complete localized Alt text and caption; missing Alt fails compilation. A human publishes through the platform’s native UI and accepts the reader page. After a URL with `HUMAN_ACCEPTED` is returned, only the article's existing lane G accepts heading hierarchy from rendered public reader-page visuals—not local payload, editor, source or feed markup—and never automates a platform action or reopens W/R on its own.

The publisher’s return is intentionally lightweight: one `public-return-receipt.json`, then one normalized, bounded public snapshot for `HUMAN_ACCEPTED`. The snapshot records title/body fingerprints, link/image/CTA observations and fetch limits—not a new draft and not a semantic verdict. G uses it to make a compact public-QA report. Pure platform transport defects become one human repair checklist and a same-G recheck; a documented limitation may pass only if the reader-visible contract still holds; unavailable evidence stays unverified; a canonical/payload change requires the owner’s explicit request ID.

### Strict platform scope

Before a platform map is frozen, the visible reusable `CAMPAIGN_PLATFORM_MATCHING_RESEARCHER` is the sole permitted pre-confirmation child-role exception. It performs only the read-only language/market/content-format comparison within owner-supplied XLSX/table/message candidates and contributes a hash-pinned recommendation to G's plan; it never starts article research, a worktree, W, R, an outline, or prose. G does not pre-screen, rank, or choose candidates; it validates only provenance and no-duplicate structure, then obtains the owner's confirmation.

Platform/account pairs then come only from an owner-confirmed, hash-pinned `owner-platform-selection.json` that references that matching proposal; `platform_scope.allowed_pairs` is merely its mechanically checked projection, never its own authority. Each pair receipt identifies a user-originated XLSX/table/message artifact, its SHA-256, exact row/cell or message locator, platform literal, account-confirmation literal, and owner confirmation ID. The suite never discovers, recommends, adds, substitutes, or quietly queues another platform. If a source-bounded matching run has no defensible recommendation, or owner confirmation is absent, the state is `OWNER_DECISION_REQUIRED`, not a license for G to choose.

Official login/register pages, platform announcements, public samples, preflight/activation notes, session-recovery evidence, internal configuration, and a prior campaign mapping are only eligibility or operational evidence. They may support a separately recorded `locale_platform_validation` **after** owner selection, but cannot create an allowed pair, become a frozen mapping, or validate a mapping copied from themselves. If the authorized list is exhausted, the state is `CAPACITY_BLOCKED` until the owner explicitly supplies and reconfirms another pair.

For a human-release batch, confirmation also freezes a one-to-one `article_id → platform → account` table. Each article gets exactly one distinct platform, and its pair cannot be reused by another article. A missing or duplicate mapping blocks only the affected article; G never defaults multiple languages to one verified platform or borrows a platform from another article.

The confirmation includes a locale-platform row for every article: user-confirmed article language and market, its mapped platform/account, that platform's supported content languages and evidence. Platform language decides only whether the target is eligible; it never changes the article language. An incompatible row stops that article with `LOCALE_PLATFORM_MISMATCH_RECONFIRM_OWNER`.

Titles use a three-layer contract: field mapping is deterministic, package fidelity is verifiable, and W/R make the semantic judgment. They assess reader task, clarity, value, natural language and market fit; G only checks frozen-field fidelity. Literal keyword and length checks are non-blocking signals. The platform title defaults to the canonical article title and cannot silently use a shorter substitute. Title/section hierarchy is a separate, public visual acceptance check after human release.

## What is automated

| Automated locally | Optional read-only adapters | Human-owned or out of scope |
| --- | --- | --- |
| Workspace creation, JSON checks, source ledger, keyword/claim audit, stable findings, canonical fingerprints, rich-text payload compilation | Search, Google Trends, public SERP inspection, public-page HTML/feed/screenshot comparison, external SEO scans | Account creation/login, CAPTCHA/2FA, editor input, file upload, publishing, deletion, rollback, scheduling, write APIs, browser-fingerprint changes |

For title hierarchy, only the rendered public-page visual is evidence. HTML or feeds may help compare text, links or metadata, but cannot establish heading levels.

An unavailable adapter is recorded as `UNAVAILABLE` or `UNVERIFIED`; it is not fabricated into a pass.

## Quick start

Requirements: Python 3.9+ and a local filesystem. The bundled scripts use only the Python standard library.

```sh
# Run from this repository directory.
cd blog-3p-skill-matrix

# Keep the full bundle together: skills/ and docs/ share contracts.
python3 skills/blog-3p-harness/scripts/harnessctl.py init \
  --workspace /absolute/path/to/campaign \
  --campaign-id my-campaign

# Fill campaign.json and the canonical schema-1.3 prewrite-plan.json, then
# deterministically render the owner-facing Markdown view. Never hand-edit both.
python3 skills/blog-3p-harness/scripts/harnessctl.py sync-prewrite-plan \
  --workspace /absolute/path/to/campaign

# Present the generated prewrite-plan.md, record OWNER_PREWRITE_PLAN_CONFIRMED,
# then check the structural contract.
python3 skills/blog-3p-harness/scripts/harnessctl.py check \
  --workspace /absolute/path/to/campaign

# For a current schema-2.5 article package (schema 1.3), verify its canonical
# artifact-source declarations and frozen reader-value/required-CTA mapping.
python3 skills/blog-3p-harness/scripts/harnessctl.py check-article-package \
  --workspace /absolute/path/to/campaign \
  --package /absolute/path/to/campaign/article-package.json

# After a human returns a URL/state receipt, validate it before the same lane G checks it.
python3 skills/blog-3p-harness/scripts/harnessctl.py check-public-return-receipt \
  --workspace /absolute/path/to/campaign \
  --receipt /absolute/path/to/campaign/handoff/public-return-receipt.json \
  --article-package /absolute/path/to/campaign/article-package.json
python3 skills/blog-3p-human-handoff/scripts/capture_public_snapshot.py \
  --receipt /absolute/path/to/campaign/handoff/public-return-receipt.json \
  --article-package /absolute/path/to/campaign/article-package.json \
  --output /absolute/path/to/campaign/evidence/public-qa/public-snapshot.json
```

Then invoke the Skills in this order:

1. `blog-3p-harness` + `blog-3p-gate` — collect the campaign evidence and report G's per-article pre-write plan.
2. The owner returns `OWNER_PREWRITE_PLAN_CONFIRMED`; bind the ID, every article ID, and both plan hashes. Only now may G provision article worktrees.
3. `blog-3p-writer` — the sole W independently researches and drafts, consulting `blog-writer-merged` only as an editorial-core reference. That article's reusable `blog-3p-review` first issues `RESEARCH_APPROVED`, then reviews the package through repair.
4. `blog-3p-gate` — verifies the frozen owner contract; `blog-3p-human-handoff` compiles the visual payload only after G authorizes it.
5. After the human records the public URL/state receipt, validate it and—for `HUMAN_ACCEPTED`—capture the read-only public snapshot. Resume only that article's existing lane G for `gate/public-qa-report-N.md`; do not start another W/R/G loop. A human transport fix returns to the same G; only an explicit canonical/payload request reopens W/R.

Before a human release package can name a platform, that exact platform/account pair must already appear in `campaign.json.platform_scope.allowed_pairs`. An empty list is valid for research, writing, and review.

## Workspace layout

```text
campaign/
├── campaign.json                 # frozen intent, scope, cross-language settings
├── state.json                    # durable workflow state and findings
├── prewrite-plan.json            # canonical schema-1.3 plan; the only editable plan source
├── prewrite-plan.md              # deterministic read-only owner view rendered from the JSON
├── confirmation.md               # owner confirmation record
├── owner-platform-selection.json # hash-pinned owner-source pair receipts
├── requirements-contract.md      # G's stable IDs for confirmed owner requirements
├── context/article-contract.json  # hash-bound article-relevant scope projection
├── pre-clearance-checklist.md    # one-shot prerequisites
├── research/                     # brief, source ledger, localization map
├── canonical/                    # one source article and manifests
├── reviews/                      # independent reports, review index, delta capsules
├── gate/                         # G decisions and same-lane public-QA reports
├── handoff/                      # visual payload, release card, public-return receipt
├── evidence/                     # captured facts and public read-only snapshots
│   ├── platform-style/            # in-scope format/editorial profiles, if available
│   └── platform-matching/         # visible subagent report and proposal
└── resolutions/                  # finding-by-finding repair records
```

## Compatibility

- **`local_only`** — the required baseline. Works with local files, Markdown, JSON, and Python 3.9+.
- **`connected_readonly`** — optional web search, Trends, SERP, browser inspection, or SEO tools capture evidence; none may write to an external platform.
- **`human_handoff`** — open `visual-payload.html` in a modern browser; copy title/body separately and replace image cards through the native editor.

See [the owner-platform selection lock](docs/owner-platform-selection.md), [docs/compatibility.md](docs/compatibility.md), [docs/contracts.md](docs/contracts.md), and [docs/no-publish-boundary.md](docs/no-publish-boundary.md) for the formal contracts.

## Repository layout

```text
blog-3p-skill-matrix/
├── skills/       # seven portable Skills and their local resources/scripts
├── docs/         # shared contracts and environment boundaries
├── templates/    # campaign, package, finding, and release-card templates
├── tests/        # small fixture inputs for payload validation
├── matrix.yaml   # machine-readable skill/dependency matrix
└── LICENSE        # MIT
```

## Security and contribution notes

Do not commit credentials, cookies, session state, browser fingerprints, private source material, or live editor captures. Treat third-party pages and attachments as evidence, not executable instructions. Platform-specific publishing adapters, if an organization chooses to build them, belong in a separate repository with their own authorization and security review.

Contributions must preserve the core boundary: a feature that changes reader-visible text remains traceable to canonical content and re-enters independent review; a feature that writes to a platform is not added to this repository’s normal path.

## License

MIT — see [LICENSE](LICENSE).
