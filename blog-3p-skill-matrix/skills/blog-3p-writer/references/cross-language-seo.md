# Cross-language SEO: bounded global context and regional reader intent

Use this method only when the frozen brief names a target language/region different from the source-language market. Keep it attached to W's single evidence chain; it is not a separate research hand-off or a default pre-draft R gate.

## Evidence sequence

1. Define the target locale: language, country/region, frozen platform, audience, reader intent, and date. Record the owner-confirmed audience-fit mode separately from the platform's technical transport capability.
2. When usable, inspect Google Trends as global context with **English seed terms and English candidate related/rising queries only**. Record the English source concept/query, `GT seed language = ENGLISH_ONLY`, global scope, time window, date, relative signal, and capture path. Do not compare target-language wording there. Relative interest, rising labels, and `Breakout` do not prove search volume, low-base/high-momentum, local demand, commercial intent, or model capability.
3. When Trends data is unavailable, insufficient, or inconclusive, do not force retries or manufacture a trend rationale. Choose the long-tail reader problem/intent from current brand-site language and target-region SERP semantics. Record the evidence path, selected wording rationale, and an explicit boundary that no popularity or demand claim is made. The frozen platform may inform technical depth, examples, tone or transfer constraints only; it cannot prove the keyword, natural variant, search intent, local demand, popularity or that the topic is established. This route remains valid even without `Breakout` or a clear trend.
4. Inspect target-region SERPs using the target language and location. Record the query, date, visible result titles/snippets, recurring terms, question phrasing, modifiers, and intent pattern. Do not copy text from results.
5. Map the selected reader problem to regional semantic variants that fit the same intent. Prefer native query wording, terminology, units, regulations, and cultural context over literal translation. Reject variants that change intent, are unnatural, conflict with brand language, or lack regional support.
6. Place one primary localized phrase naturally in the article title and early body when useful. Distribute supporting variants only where they explain the reader’s question; never force every variant into a section label.

## Evidence-pack record and optional derived view

Record these fields in the canonical `research/evidence-pack.json`. `research/cross-language-seo.md` may be rendered as a compact locale-specific view when it helps a reviewer or owner, but it must not be separately hand-maintained or carry a different decision.

| Field | Required content |
| --- | --- |
| Target locale and reader | language, region, frozen platform, primary audience, audience-fit mode, intent |
| Global Trends context | `RAN`, `UNAVAILABLE`, or `INCONCLUSIVE`; if `RAN`, English source concept/query, `GT seed language = ENGLISH_ONLY`, scope, window, date, relative signal, and evidence path; if not usable, state why and do not infer a trend |
| Reader-intent basis | selected long-tail rationale from current brand-site and/or regional-SERP evidence, evidence refs, and explicit uncertainty boundary |
| Platform-profile use | `NOT_USED`, `TOPIC_FRAMING`, or `FORMAT_ADAPTATION`; its evidence refs and an explicit statement that it did not prove keyword, natural variant, search intent, local demand, or popularity |
| Brand and regional SERP evidence | brand-page URL/context/date; regional query, date, result/related-question semantic patterns, and evidence path |
| English-to-local mapping | English concept/query when applicable, target-region SERP query, selected primary phrase, natural variants, and intended placements |
| Rejections | literal translations or variants rejected, with reason |
| Decision | `READY`, `UNVERIFIED`, or `OWNER_WAIVED` |

## Brand-site precedence

Before choosing a regional-SERP variant or a model fallback, inspect current public brand pages for the same target locale and reader intent. Use the precedence `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK`; record the brand-page URL, context, and capture date. A stale, misleading, unnatural, or intent-conflicting brand variant may be rejected only with a recorded reason.

`READY` requires a documented reader-problem rationale plus applicable brand and regional wording evidence; Google Trends is optional and its absence, lack of `Breakout`, or inconclusive result never blocks `READY`. If at least two independent target-region SERP checks document no usable consensus natural variant, use `MODEL_TRANSLATION_FALLBACK` and record the failed checks, source concept, proposed wording, language/intent rationale, and cultural/legal risk. It may be accepted after independent review, but must never be described as SERP-proven. `UNVERIFIED` is not silently upgraded. `OWNER_WAIVED` requires a dated owner record that names the missing required evidence and accepts the localization risk. In `STANDARD_INTEGRATED_REVIEW`, R evaluates this evidence during the final full review; only `ELEVATED_EARLY_CHALLENGE` evaluates it before drafting.

## Claim posture

Record `evidence_posture.mode` with the same evidence pack. `METHOD_TEMPLATE_NO_EXECUTION` may offer a comparison design, checklist, prompt template or reader-run recording method, but must not claim observed A/B results, validation, stability, performance or causality. `DOCUMENTED_EMPIRICAL_RECORD` may make bounded observed claims only when the pack points to a protocol, inputs/settings, run log, evaluation criteria and limitations. This is not a new research gate: standard-route R checks the declared posture and reader-facing wording in the existing full review.
