# Campaign contract

The harness creates `campaign.json`, `state.json`, `prewrite-plan.json`, generated `prewrite-plan.md`, `confirmation.md` and `requirements-contract.md`. `campaign.json` is structured frozen owner intent; `prewrite-plan.json` is the canonical editable per-article manifest; `prewrite-plan.md` is its deterministic read-only owner-facing rendering created by `sync-prewrite-plan`; `requirements-contract.md` is G's stable-ID record of requirements explicitly confirmed by the owner; `state.json` is durable workflow progress. Never hand-maintain the plan in both JSON and Markdown, and never put credentials, session data, browser fingerprints or access tokens in any of them.

New workspaces use schema `2.5`. The structural checker remains compatible with schemas `1.0` through `2.4`; legacy workspaces remain valid under their historical contract and must not be silently relabeled as schema 2.5. In particular, `cta.mode = NONE` is historical schema-2.1 compatibility only, never valid for a new schema-2.2+ campaign. Schema 2.3 added the structured public-return receipt, normalized read-only snapshot, per-article public-QA ledger and same-lane-G-only classification policy. Schema 2.4 added canonical manifests, deterministic pre-write rendering, compact article/review context and bounded delta review. Schema 2.5 locks optional English-only global Trends context, the bounded target-platform audience-need route for insufficient data, and the prohibited trend inferences without requiring a Trends artifact.

## Pre-write plan contract

G begins in `prewrite_planning`. Before any article worktree, article-lane G, W, R, article queue, outline, prose, image generation, canonical package or article-research role exists, G gathers and reports a pre-write dossier. It is a read-only research protocol and known-evidence summary, not a completed W research package; it must identify uncertainty and may not declare `RESEARCH_READY` or `RESEARCH_APPROVED`.

Canonical `prewrite-plan.json` and its generated owner-facing `prewrite-plan.md` must cover every configured `article_id` exactly once. In schema-2.5, the JSON manifest is schema `1.3`, includes the artifact convention and shared-evidence reference, and is the only editable plan source; run `sync-prewrite-plan` after every change. Each plan contains non-empty `task_and_audience`, `reader_value_and_secondary_cta`, `research_evidence_and_uncertainty`, `keyword_and_localization_strategy`, `factual_claims_and_sources`, `title_and_outline`, `visual_narrative`, `platform_transport_assumptions`, and `risks_and_owner_decisions`. The manifest also records non-empty campaign `owner_task_and_scope`, `content_value_and_cta_policy`, `sources_checked_and_uncertainty`, `shared_constraints`, and `platform_matching_status`. Schema-2.2/2.3 retain manifest schema `1.2`; schema `2.1` uses manifest schema `1.1`; schema `2.0` uses manifest schema `1.0` and its historical section list. `UNVERIFIED` must say what was checked and the resulting risk; it is never a license to invent evidence.

G presents this dossier and moves to `awaiting_owner_prewrite_confirmation`. Only the explicit `OWNER_PREWRITE_PLAN_CONFIRMED` receipt permits article-lane provisioning. Bind the owner confirmation ID, exact unique article IDs, report SHA-256 and manifest SHA-256 in `state.json.prewrite_plan`, `confirmation.md`, `requirements-contract.md`, `campaign.json.scope_lock.prewrite_plan_receipt`, and the report/manifest themselves. A material card, scope, title/outline, locale, visual, factual, or transport change invalidates the binding and returns to owner confirmation. `OWNER_PREWRITE_PLAN_CHANGES_REQUESTED` never authorizes a partial dispatch.

This does not create a second article-research role. After owner confirmation, W performs the complete integrated keyword, source and cross-language research; the same article's reusable R then issues `RESEARCH_APPROVED` before W outlines or drafts.

`blog-3p-writer` is the sole executable W for that integrated research, drafting, packaging and repair. `blog-writer-merged` is an editorial-core reference only; it must not create a second research pass, canonical package or W lane.

## Shared evidence cache

Read [shared-evidence-cache.md](shared-evidence-cache.md) whenever a campaign wants to reuse a read-only observation. Cache reuse reduces repeated collection; it does not replace the pre-write plan, owner confirmation, W's integrated research, R's independent approval, or per-article evidence records. When optional `GLOBAL_ENGLISH_TRENDS` context is recorded, only an exact concept/seed/date/window match may be shared; it never becomes demand, popularity, or momentum proof. Brand wording requires the same locale and intent plus freshness; and regional-SERP wording requires the exact locale, market and intent. Volatile claims, policy, login/account state, price, performance and translation fallback are always fresh/article-specific.

Cached platform evidence is never owner-selection authority. Before article lanes begin, the owner still confirms the proposal and exact `{platform, account}` mapping. A durable public format observation may be reused only under the platform-profile cache rules; current campaign policy, login/account and locale-support facts must be refreshed.

Required safety fields:

- `prewrite_plan_policy.mode = CAMPAIGN_G_PREWRITE_EVIDENCE_AND_PLAN`
- `prewrite_plan_policy.required_before_article_dispatch = true`
- `prewrite_plan_policy.owner_confirmation_required = true`
- `prewrite_plan_policy.report_path = prewrite-plan.md`
- `prewrite_plan_policy.manifest_path = prewrite-plan.json`
- `prewrite_plan_policy.canonical_source = prewrite-plan.json`
- `prewrite_plan_policy.owner_view_mode = DETERMINISTIC_RENDERED_READ_ONLY`
- `prewrite_plan_policy.manual_duplicate_entry = PROHIBITED`
- `prewrite_plan_policy.sync_command = sync-prewrite-plan`
- `prewrite_plan_policy.allow_article_roles_before_confirmation = false`
- `prewrite_plan_policy.standalone_article_research_role = PROHIBITED`
- `prewrite_plan_policy.writer_research_remains_required = true`
- `keyword_research_policy.required_after_owner_prewrite_confirmation_before_drafting = true`
- `platform_scope.source = OWNER_SELECTION_LOCK_ONLY`
- `platform_scope.allowed_pairs = []` or exact owner-supplied pairs
- `platform_scope.automatic_discovery_or_expansion = false`
- `release_policy.machine_external_writes_allowed = false`
- `cross_language_seo.variant_priority_order = [CURRENT_BRAND_SITE, REGIONAL_SERP, MODEL_TRANSLATION_FALLBACK]`
- `cross_language_seo.google_trends_seed_language = ENGLISH_ONLY` when optional Google Trends context is recorded; its absence or an inconclusive result does not block the bounded target-platform audience-need route.
- `orchestration_policy.delegation_default = VISIBLE_SUBAGENTS`
- `orchestration_policy.visible_task_record_required = true`
- `orchestration_policy.invisible_cli_agent_sessions = PROHIBITED`
- `orchestration_policy.writer_reviewer_pair_mode = ONE_REUSABLE_PAIR_PER_ARTICLE`
- `orchestration_policy.cross_article_agent_reuse = PROHIBITED`
- `orchestration_policy.operations_steward_mode = ONE_REUSABLE_CAMPAIGN_OPERATIONS_STEWARD`
- `orchestration_policy.persistent_requirements_gatekeeper = true`
- `orchestration_policy.fresh_agent_roles = []`
- `orchestration_policy.pair_activation = G_QUEUE_SUBJECT_TO_RUNTIME_CAPACITY`
- `orchestration_policy.execution_isolation = WORKTREE_FIRST_PER_ARTICLE`
- `orchestration_policy.worktree_autospawn = CREATE_VISIBLE_PROJECT_WORKTREE_PER_READY_ARTICLE_WHEN_SUPPORTED`
- `orchestration_policy.worktree_fallback = VISIBLE_SHARED_WORKSPACE_WITH_PATH_ISOLATION`
- `orchestration_policy.silent_worktree_fallback = false`
- `orchestration_policy.article_worktree_role_bundle = ONE_REUSABLE_W_R_G_LANE_PER_ARTICLE`
- `orchestration_policy.project_worktree_root_role = ARTICLE_LANE_GATEKEEPER`
- `orchestration_policy.campaign_gatekeeper_scope = GLOBAL_REQUIREMENTS_QUEUE_AND_LEDGER_ONLY`
- `orchestration_policy.article_public_gate_mode = REUSE_ARTICLE_LANE_GATEKEEPER_ONLY`
- `orchestration_policy.public_qa_policy.mode = REUSE_ARTICLE_LANE_GATEKEEPER_READONLY`
- `orchestration_policy.public_qa_policy.requires_human_acceptance = true`
- `orchestration_policy.public_qa_policy.human_return_receipt = STRUCTURED_REQUIRED`
- `orchestration_policy.public_qa_policy.public_snapshot = NORMALIZED_READONLY_REQUIRED`
- `orchestration_policy.public_qa_policy.fresh_public_reviewer = PROHIBITED`
- `orchestration_policy.public_qa_policy.automatic_wr_reopen = false`
- `orchestration_policy.public_qa_policy.human_transport_fix_recheck = SAME_LANE_G_ONLY`
- `orchestration_policy.public_qa_policy.canonical_change_reopen = OWNER_EXPLICIT_REQUEST_ID_REQUIRED`
- `orchestration_policy.public_qa_policy.accepted_platform_limitation = EVIDENCE_SCOPED_NOT_GENERALIZABLE`
- `orchestration_policy.public_qa_policy.unverified_retry_budget = 1`
- `orchestration_policy.public_qa_policy.on_mismatch = CLASSIFY_BEFORE_OWNER_DECISION`
- `orchestration_policy.queue_resume_policy = AUTO_START_NEXT_READY_TASK_ON_SLOT_AVAILABLE`
- `article_platform_assignment.mode = ONE_ARTICLE_ONE_DISTINCT_PLATFORM`
- `article_platform_assignment.required_before_editorial_dispatch = true`
- `article_platform_assignment.platform_reuse_across_articles = PROHIBITED`
- `article_platform_assignment.pair_reuse_across_articles = PROHIBITED`
- `locale_platform_validation.mode = ARTICLE_LANGUAGE_MARKET_PLATFORM_EVIDENCE`
- `locale_platform_validation.required_before_editorial_dispatch = true`
- `locale_platform_validation.article_language_source = USER_CONFIRMED_ARTICLE_LANGUAGE_ONLY`
- `locale_platform_validation.platform_language_role = ELIGIBILITY_ONLY_NEVER_REWRITE_LANGUAGE`
- `title_quality_policy.mode = MODEL_LED_SEMANTIC_REVIEW`
- `title_quality_policy.required_before_review = true`
- `title_quality_policy.heuristics.non_blocking = true`
- `content_value_policy.mode = READER_VALUE_FIRST`
- `content_value_policy.primary_purpose = STANDALONE_ANSWER_TO_READER_TASK`
- `content_value_policy.cta_role = REQUIRED_SECONDARY_TRANSPARENT_RECOMMENDATION`
- `content_value_policy.cta_must_be_present = true`
- `content_value_policy.cta_requires_identifiable_product_and_claim_basis = true`
- `content_value_policy.cta_requires_relationship_disclosure_when_applicable = true`
- `content_value_policy.cta_must_not_replace_or_dominate_reader_value = true`
- `artifact_optimization_policy.mode = CANONICAL_MANIFESTS_AND_DELTA_CONTEXT`
- `artifact_optimization_policy.prewrite_manifest_schema = 1.3`
- `artifact_optimization_policy.article_context.path = context/article-contract.json`
- `artifact_optimization_policy.review_index.path = reviews/review-index.json`
- `artifact_optimization_policy.review_delta.schema_version = 1.0`

`state.json.orchestration.tasks[]` is the durable visibility ledger. Each independent role records its visible agent identity, `article_id` where applicable, bounded input paths, expected and actual output paths, timestamps, status and recovery instruction. While the pre-write plan is not `OWNER_PREWRITE_PLAN_CONFIRMED`, it must contain no `ARTICLE_LANE_GATEKEEPER`, `ARTICLE_WRITER` or `ARTICLE_LANGUAGE_REVIEWER`; its article queue, article agents, article worktrees and active article pairs must all be empty. `state.json.orchestration.article_agents[article_id]` holds that article's sole `ARTICLE_WRITER` and `ARTICLE_LANGUAGE_REVIEWER`; the pair is reused for the article's drafting, repair, full R and R-Δ only. `reviews/review-index.json` records the latest research/full approval report paths and hashes with that same reviewer ID. Before a schema-2.5 hand-off, require that R's completed visible `RESEARCH_REVIEW`, `FULL_REVIEW`, and `VISUAL_PAYLOAD_DELTA` task rows all bind their expected reports; the `APPROVED` final visual receipt additionally binds its report, R ID, review-index, visual-manifest and visual-payload hashes. W maintains one per-article `requirements-traceability.md` mapping applicable `REQ-*` IDs to canonical and visual-payload evidence; it is not a verdict. R owns complete article quality, including SEO and title/localization judgment, and verifies those paths exist. Persistent G accepts only the owner-contract mapping after R approval; its own findings use `REQUIREMENT-*` and do not duplicate R's quality findings. After a human return, `state.json.publication.articles[article_id]` records URL, human state, timezone-aware return time, campaign-local receipt/snapshot/report paths, existing lane-G agent ID, attempt, bounded `unverified_retry_count`, owner request ID and public-QA outcome. The receipt, snapshot and report must exist and bind the same article/URL; a `PUBLIC_QA_READONLY` task row binds the same registered G ID, timestamp and report. `HUMAN_NEEDS_FIX` is never completion. After `HUMAN_ACCEPTED`, that existing `ARTICLE_LANE_GATEKEEPER` alone writes `gate/public-qa-report-N.md`; it does not create a public role or invoke W/R. It classifies `PUBLIC_QA_PASSED`, `PUBLIC_QA_PASSED_WITH_LIMITATION`, `HUMAN_TRANSPORT_FIX_REQUIRED`, `PUBLIC_QA_UNVERIFIED`, or `CANONICAL_CHANGE_REQUESTED`; only the last needs an explicit owner request ID and can reopen W/R. A W/R task after the receipt timestamp is forbidden unless its `workflow_stage` is `CANONICAL_REOPEN` and it carries that same owner request ID. `service_agents.campaign_operations` holds one visible, campaign-scoped `CAMPAIGN_OPERATIONS_STEWARD`, reused for read-only platform readiness, evidence collection, session recovery and bounded technical investigation; it never writes externally, chooses platforms, drafts articles or decides quality. Resume it with its recorded evidence rather than creating phase-named preflight/registration/recovery agents. `article_queue[]` schedules pairs only after the current runtime slots are full. `orchestration.capacity{available_slots,active_article_pairs,active_article_worktrees,spawn_policy,last_dispatch_at}` records dispatch capacity. Local CLI commands may perform deterministic mechanics only; a detached CLI conversation or background agent is never a valid W/R/G/Probe record.

## Runtime-isolation contract

Three independent properties must never be conflated: a **visible child task** makes work observable, a **reusable W/R/G article lane** preserves that article's editorial context and decisions, and a **Git project worktree** isolates its files and Git state. One does not imply either of the other two.

Only after the pre-write plan is confirmed and hash-bound may an article lane be ready. When the host exposes a Git-project worktree capability and two or more independent article lanes are ready, G must create one visible project-worktree task per article before its first W turn. Its root role is `ARTICLE_LANE_GATEKEEPER`, never W. The lane G immediately creates and reuses that worktree's `ARTICLE_WRITER` and `ARTICLE_LANGUAGE_REVIEWER`, driving `G → W ↔ R → G` serially; W and R never work concurrently on the same article. The campaign G remains the only global owner of frozen scope, campaign queue and consolidated state; it consumes the lane G's saved report without repeating article-quality review. A plain child agent in the parent checkout, or a W-only project task, does not satisfy this rule. Register the worktree in `state.json.orchestration.article_workspaces[article_id]` with `isolation: GIT_WORKTREE`, `status: PROVISIONING|READY`, the visible `task_thread_id`, worktree path when exposed, base ref, and a `role_bundle` containing the lane G, W and R agent IDs. Treat a provisioning-only client identifier as not ready until the host reports a usable task/worktree.

If the host cannot create a project worktree, record `isolation: SHARED_WORKSPACE`, `status: WORKTREE_UNAVAILABLE`, the capability/error reason, and the explicit fallback `VISIBLE_SHARED_WORKSPACE_WITH_PATH_ISOLATION`. That fallback is permitted only when every article has disjoint bounded input/output paths; it must never be described as a worktree. If paths overlap or isolation is needed for conflicting changes, mark the affected article `WORKTREE_ISOLATION_BLOCKED` and queue it rather than risking cross-article changes. When a slot frees, G provisions the next ready article worktree before dispatching its W/R pair.

For a human-release batch, `articles[]` and `article_platform_assignment.assignments[]` must have the same article IDs, exactly once each. Each assignment is an object `{article_id, platform, account}` and must exactly match an `allowed_pairs` object. Platform names and platform/account pairs are unique across the batch; no automatic or cross-article reassignment exists.

`locale_platform_validation.rows[]` must likewise cover every article exactly once. A row matches the frozen article `language` and `market` plus its platform/account assignment, lists `supported_content_languages`, gives platform-language evidence, and declares `COMPATIBLE`. Platform language is a rejection/eligibility signal only; it may never rewrite the article language.

Every locked article must supply `focus_keyword`. In schema `2.2+`, it must also supply a non-empty `reader_value_promise` plus a `cta` object whose `mode` is `SECONDARY_RECOMMENDATION`. It requires exact visible `anchor_text`, product name, current destination URL, claim-evidence path, reader-task relevance and a relationship disclosure; `NOT_APPLICABLE` may be used only where no material relationship applies. In schema-2.5, `article-package.json` uses schema `1.3`, copies both values exactly and points to the canonical evidence/visual/handoff manifests; run `harnessctl.py check-article-package` to verify that mapping and artifact chain without scoring the content. Schema-2.2/2.3 packages remain schema `1.2` under their historical contract. These are declaration/provenance fields, not an automated quality score or a license to state that a product is reliable, ranked, tested or available. R judges whether the article genuinely answers the reader task and whether the required recommendation is proportionate, balanced and truthful; G checks only that the frozen fields map to delivery. Do not add CTA count, density, placement or word-ratio requirements. `title_quality_policy` asks W/R to judge canonical article title, platform title and SEO title from the reader task, topic clarity, distinct value, natural language and market fit. G only checks that an owner-specified title or SEO task is faithfully mapped to delivery. Word minima, visible-character minima and literal-keyword checks are advisory only. Default platform title equals the canonical article title; a divergent mapping is blocked unless the owner records an explicit platform constraint. Heading hierarchy itself is accepted only from rendered public reader-page visuals after `HUMAN_ACCEPTED`.

An empty platform list permits research and writing but not a human release package. A human-release target must match one exact allowed pair.
