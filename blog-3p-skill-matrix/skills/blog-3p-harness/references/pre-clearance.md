# One-shot pre-clearance

Before any article worktree, W/R, outline or drafting, G prepares one owner-facing pre-write dossier. It may collect read-only campaign evidence and a source-bounded platform-matching proposal, but it must not present its summary as completed W research.

For a current schema-2.5 workspace, G maintains one canonical schema-`1.3` `prewrite-plan.json`, with exactly one plan card per configured article/subtask, then runs `harnessctl.py sync-prewrite-plan` to render `prewrite-plan.md`. The Markdown is a deterministic, read-only owner view: never hand-edit it or dual-write the plan. Legacy workspaces retain their historical pre-write manifest contract. Collect and report:

1. Campaign goal, reader task, audience, language and target locales.
2. Brand/product pages, approved claims, source access, standalone reader-value promise, and the required secondary CTA/disclosure declaration. It records exact visible anchor text, product identity, current destination, claim evidence, reader-task relevance and any material-relationship disclosure; it does not establish independent reliability, ranking, testing or availability.
3. Focus/supporting topics, content type, length, image rights and visual requirements.
4. Cross-language method: brand-site pages to inspect; an optional English-only Google Trends seed/candidate set and window for global relative-interest context; target-region SERP method; English-concept-to-local-variant mapping; and, when Trends data is insufficient or inconclusive, the documented target-platform audience-need rationale and explicit evidence boundary. No missing trend signal blocks drafting or proves demand.
5. Exact human-release platform/account pairs, only when release is in scope.
6. Provisional title and outline: focus keyword/approved variant, reader task, canonical article title, platform title and SEO title, reader promise, visible section/subsection route, and explicit uncertainty. Field mapping is deterministic; semantic title quality is reviewed by W/R, while G checks only frozen-field fidelity; length is only an advisory.
7. Visual narrative: LEAD/MIDDLE/CLOSING jobs, count, adjacent claims, rights and reader purpose.
8. Platform transport assumptions: only confirmed or proposed in-scope facts, title/body transfer, public visual hierarchy risks, metadata limits and unknowns. Editor HTML/DOM is never an acceptance surface.
9. Risks, excluded work, unresolved decisions and the requested owner choice.

For reusable read-only observations, apply the [shared evidence cache contract](shared-evidence-cache.md). The dossier may cite an exact, dated cache hit as a research lead, but it must retain the source, scope and uncertainty. It cannot reuse volatile claims, policy, login/account, price, performance, locale-support or translation-fallback evidence, and it cannot let a cache choose or substitute a platform/account pair.

G reports the generated dossier and waits for `OWNER_PREWRITE_PLAN_CONFIRMED`. Bind its confirmation ID, exact article IDs, generated Markdown-report SHA-256 and canonical JSON-manifest SHA-256 in `state.json`, `confirmation.md`, `requirements-contract.md` and `campaign.json.scope_lock`. Until that binding is valid, no article worktree, lane G, W, R, article agent, active pair or article queue may exist.

After owner confirmation, G copies only the explicit confirmed items into `requirements-contract.md` as stable `REQ-<AREA>-NNN` entries. Mark each item `DONE`, `USER_ACTION`, `AUTOMATION` or `NOT_APPLICABLE`; request all outstanding user actions once rather than serially. Then W—not G's dossier—conducts the integrated keyword/source research and R issues `RESEARCH_APPROVED` before prose.
