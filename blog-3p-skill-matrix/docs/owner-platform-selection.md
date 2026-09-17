# Owner Platform Selection Lock

This lock prevents a workflow from treating its own candidate discovery, activation note, configuration, or platform-login evidence as owner authorization.

## Two separate questions

1. **Recommendation:** Which source-listed platform best matches the frozen article language, market and format? Only the visible reusable `CAMPAIGN_PLATFORM_MATCHING_RESEARCHER` answers this in `platform-matching-proposal.json`.
2. **Selection:** Which exact `{article_id, platform, account}` pair did the owner confirm from that proposal? Only a receipt in `owner-platform-selection.json` can answer this.
3. **Eligibility:** Can that selected platform carry the frozen language and format? Only then may a read-only `locale_platform_validation` record answer this.

G never answers recommendation or selection: it creates/resumes the matching subagent, checks its source bounds, and obtains the owner's confirmation. Eligibility never answers recommendation or selection. A login announcement, OAuth option, registration page, platform preflight, browser recovery result, public sample, prior campaign, or generated configuration is not an owner-selection source.

## Required lock contents

Place each owner-originated input artifact inside `evidence/owner-selection/` and record its SHA-256. Supported source types are `OWNER_XLSX`, `OWNER_TABLE`, and `OWNER_MESSAGE`. Each pair receipt must contain:

- `article_id`, `platform`, and a safe `account` alias;
- `source_id`, exact `source_locator`, and the source's platform literal;
- the exact owner-confirmed account-alias wording and an `owner_confirmation_id`;
- `status: EXPLICITLY_CONFIRMED`.

The lock must also reference the matching proposal's path, SHA-256, visible subagent task ID and researcher role. Set the lock's `status` to `OWNER_CONFIRMED`, calculate its SHA-256, and place that value in `campaign.json.platform_scope.selection_lock.sha256`. The campaign validator requires the lock hash, each source artifact hash, the proposal hash, and exact equality between proposal, receipts, `allowed_pairs`, and article assignments.

## Required behavior when a receipt is absent

The matching subagent records `NO_RECOMMENDATION_OWNER_DECISION_REQUIRED`. G does not select a candidate, look for a replacement, infer an account, or write a provisional mapping into `campaign.json`. A wide instruction such as “new languages” or “no duplicate platforms” constrains the subagent's source-bounded research and the owner's later confirmation; it does not create one.
