# Cross-language SEO: global trend to regional SERP

Use this method only when the frozen brief names a target language/region different from the source-language market. Keep it attached to the W evidence chain; it is not a separate research hand-off.

## Evidence sequence

1. Define target locale: language, country/region, reader intent, date and Google Trends time window.
2. In Google Trends, inspect the global baseline using **English seed terms and English candidate related/rising queries only**, for every target locale. Select low-base, high-momentum long-tail candidates only when relevant to the reader problem; record the English source concept, English query, `GT seed language = ENGLISH_ONLY`, scope, time window, observed signal and capture path/date. Treat `Breakout`/rising labels and relative interest as momentum signals, never absolute search volume. Do not compare target-language wording in Google Trends.
3. For each selected English concept, inspect the target-region SERP using the target language and location. Record the query, date, visible result titles/snippets, recurring terms, question phrasing, modifiers and intent pattern. Do not copy text from results.
4. Map the English global candidate to the regional semantic variants that actually fit the same intent. Prefer native query wording, terminology, units, regulations and cultural context over literal translation. Reject variants that change intent, are unnatural, conflict with brand language or are unsupported by the regional evidence.
5. Place one primary localized phrase naturally in the article title and early body when useful. Distribute supporting variants only where they explain the reader’s question; never force every variant into a section label.

## Required `research/cross-language-seo.md` record

| Field | Required content |
| --- | --- |
| Target locale and reader | language, region, audience, intent |
| Global Trends discovery | English source concept, English query, `GT seed language = ENGLISH_ONLY`, global scope, time window, date, low-base/high-momentum observation, evidence path |
| Regional SERP evidence | regional query, date, result/related-question semantic patterns, evidence path |
| English-to-local mapping | English concept/query, target-region SERP query, selected primary phrase, natural variants, intended placements |
| Rejections | literal translations or variants rejected, with reason |
| Decision | `READY`, `UNVERIFIED`, or `OWNER_WAIVED` |

## Brand-site precedence

Before choosing a regional-SERP variant or a model fallback, inspect current public brand pages for the same target locale and reader intent. Use the precedence `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK`; record the brand-page URL, context and capture date. A stale, misleading, unnatural or intent-conflicting brand variant may be rejected only with a recorded reason.

`READY` requires both evidence types. If at least two independent target-region SERP checks document no usable consensus natural variant, use `MODEL_TRANSLATION_FALLBACK` and record the failed checks, source concept, proposed wording, language/intent rationale and cultural/legal risk. It may be accepted after independent review, but must never be described as SERP-proven. `UNVERIFIED` is not silently upgraded. `OWNER_WAIVED` requires a dated owner record that names the missing evidence and accepts the localization risk.
