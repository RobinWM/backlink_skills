# Shared evidence cache contract

Use a cache only to avoid repeating the same bounded, read-only observation. A cache record is an evidence reference, never a research conclusion, a platform-selection authority, or permission to widen scope. Store it under `evidence/shared/` with its source URL/path, observation time, scope, query or page context, content hash when available, and the reuse decision that cites it.

## Reuse keys

| Record kind | A cache hit requires | What the receiving article still records |
| --- | --- | --- |
| `GLOBAL_ENGLISH_TRENDS` | The same `english_concept_id`, English seed/candidate set, observation date, and Trends window. A different concept, candidate set, date, or window is a miss. | Its own selected long-tail opportunity and English-to-target-market mapping. Trends remains global context, not local-demand evidence. |
| `BRAND_SITE_VARIANT` | The same target locale and reader intent, a current public brand page, and a fresh recheck of the page or an explicitly recorded valid-through date. | Adoption or evidence-backed rejection for that article's wording. Brand ownership alone does not prove naturalness. |
| `REGIONAL_SERP_VARIANT` | The exact locale, market, reader intent, query context, and dated SERP observation. Any locale, market, intent, query, or stale-observation change is a miss. | The selected natural variant, rejected literal translations, and its article-specific intent rationale. |

The cache key and cited record must be visible in the receiving article's evidence. A cache hit may shorten collection, but it does not let W omit article-specific reasoning or let R omit independent review.

## Never-reuse class

Do not reuse any cache record as evidence for volatile or account-specific facts: product capability/availability, price, quota, performance, rankings, comparative results, current policy, moderation outcome, registration/login/OAuth/session state, account eligibility, editor behavior tied to an account or theme, or platform language support. `MODEL_TRANSLATION_FALLBACK` is also never reusable: it is an article-specific conclusion from that article's two dated regional-SERP no-consensus checks.

When a record is stale, mismatched, inaccessible, contradicted, or lacks a clear scope, mark it `UNVERIFIED` and collect fresh evidence. Do not silently substitute a nearby variant, platform, account, locale, or market.

## Role boundary

- Campaign G may cite a cache record in the pre-write plan as known evidence or a research lead. It still needs owner confirmation before any article lane, and a cache can never select, lock, replace, or validate a platform/account pair.
- W independently verifies the cache key, records the article-specific use, and gathers any non-reusable or fresh evidence. Cached context never turns into `RESEARCH_READY` by itself.
- R independently judges the cached evidence's fit, freshness, target-language naturalness, and the receiving article's use of it. G only checks that the declared cache reference remains within the confirmed scope.
- The campaign operations steward may reuse only durable public format facts under the platform-profile rules. It must refresh campaign-specific, login/account, policy, price, and locale-support facts for the current campaign.

## Cache record minimum

Use a compact record with: `id`, `kind`, `status`, `source`, `observed_at`, `scope`, `query_or_page_context`, `valid_through_or_recheck`, `evidence_path`, and `reuse_decision`. For a reused record, add the receiving `article_id` and exact matching key. Do not copy a cached conclusion into a new record without preserving its source and date.
