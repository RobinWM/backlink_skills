# Cross-language SEO: bounded global context and regional reader intent

Use this method only when the frozen brief names a target language/region different from the source-language market. Keep it attached to the W evidence chain; it is not a separate research hand-off.

## Evidence sequence

1. Define the target locale: language, country/region, frozen platform, audience, reader intent, and date.
2. When usable, inspect Google Trends as global context with **English seed terms and English candidate related/rising queries only**. Record the English source concept/query, `GT seed language = ENGLISH_ONLY`, global scope, time window, date, relative signal, and capture path. Do not compare target-language wording there. Relative interest, rising labels, and `Breakout` do not prove search volume, low-base/high-momentum, local demand, commercial intent, or model capability.
3. When Trends data is unavailable, insufficient, or inconclusive, do not force retries or manufacture a trend rationale. Choose the long-tail reader problem/intent from the frozen target platform's documented plausible mainstream audience needs, current brand-site language, and target-region SERP semantics. Record the evidence path, selected wording rationale, and an explicit boundary that no popularity or demand claim is made. This route remains valid even without `Breakout` or a clear trend.
4. Inspect target-region SERPs using the target language and location. Record the query, date, visible result titles/snippets, recurring terms, question phrasing, modifiers, and intent pattern. Do not copy text from results.
5. Map the selected reader problem to regional semantic variants that fit the same intent. Prefer native query wording, terminology, units, regulations, and cultural context over literal translation. Reject variants that change intent, are unnatural, conflict with brand language, or lack regional support.
6. Place one primary localized phrase naturally in the article title and early body when useful. Distribute supporting variants only where they explain the reader’s question; never force every variant into a section label.

## Required `research/cross-language-seo.md` record

| Field | Required content |
| --- | --- |
| Target locale and reader | language, region, frozen platform, audience, intent |
| Global Trends context | `RAN`, `UNAVAILABLE`, or `INCONCLUSIVE`; if `RAN`, English source concept/query, `GT seed language = ENGLISH_ONLY`, scope, window, date, relative signal, and evidence path; if not usable, state why and do not infer a trend |
| Target-platform reader-need rationale | documented plausible audience need, reader problem/intent, selected long-tail rationale, evidence path, and explicit uncertainty boundary |
| Brand and regional SERP evidence | brand-page URL/context/date; regional query, date, result/related-question semantic patterns, and evidence path |
| English-to-local mapping | English concept/query when applicable, target-region SERP query, selected primary phrase, natural variants, and intended placements |
| Rejections | literal translations or variants rejected, with reason |
| Decision | `READY`, `UNVERIFIED`, or `OWNER_WAIVED` |

## Brand-site precedence

Before choosing a regional-SERP variant or a model fallback, inspect current public brand pages for the same target locale and reader intent. Use the precedence `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK`; record the brand-page URL, context, and capture date. A stale, misleading, unnatural, or intent-conflicting brand variant may be rejected only with a recorded reason.

`READY` requires a documented reader-problem rationale plus applicable brand and regional wording evidence; Google Trends is optional and its absence, lack of `Breakout`, or inconclusive result never blocks `READY`. If at least two independent target-region SERP checks document no usable consensus natural variant, use `MODEL_TRANSLATION_FALLBACK` and record the failed checks, source concept, proposed wording, language/intent rationale, and cultural/legal risk. It may be accepted after independent review, but must never be described as SERP-proven. `UNVERIFIED` is not silently upgraded. `OWNER_WAIVED` requires a dated owner record that names the missing required evidence and accepts the localization risk.
