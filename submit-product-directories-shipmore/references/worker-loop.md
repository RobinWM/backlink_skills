# Shipmore worker loop

## Deterministic loop

For one Shipmore Run, use the same stable worker ID for every claim and heartbeat from the same worker instance.

```text
while true:
  claim(runId, workerId)

  if run_not_found:
    stop with configuration error

  if run_paused:
    stop mutable work; wait for resume/new instruction

  if run_terminal:
    stop

  if queue_empty:
    stop

  task = claim.data
  runItemId = task.id

  inspect previous submission snapshot

  if no new action is appropriate:
    complete(skipped, preserve current submissionStatus)
    continue

  heartbeat(runItemId)
  browser preflight + legitimacy/authorization checks
  if mandatory backlink/badge:
    register outbound link; poll and verify Product homepage
    if verification fails: complete truthfully; do not submit
  heartbeat(runItemId)
  perform verified form work
  heartbeat(runItemId)
  inspect exact final result
  classify result
  complete(stable eventId)
```

## Before opening the browser

Validate:

- `runItemId = claim.data.id`;
- `claimedBy` matches this worker;
- lease has not expired;
- Product and Directory data are present enough for the next read-only step;
- previous `submissionStatus` does not prohibit blind resubmission.

Use `submitUrl` as the preferred route. If it is a homepage or redirects to a different official submission route, inspect the destination before any form mutation.

## Mandatory preflight decision order

Run read-only checks in this order so an earlier terminal policy result is not hidden by a later, less important missing field.

1. **Unavailable route/site** — if the official submission route is gone, closed, or unavailable, classify `unavailable`.
2. **Paid-only** — if the route requires payment that is not authorized, classify `paid_only` and stop.
3. **Mandatory backlink/badge** — do not immediately classify as ineligible. Use the authorized Shipmore outbound-link registration and homepage verification procedure below. Continue only if verification passes; timeout stops the item before form submission.
4. **Other ineligibility** — unsupported eligibility, prohibited non-backlink site changes, or unrelated commercial/community actions remain `ineligible`.
5. **Duplicate / existing lifecycle guard** — inspect previous Shipmore state and any clear existing listing. Never blindly resubmit `submitted`, `submission_outcome_unknown`, `awaiting_approval`, `awaiting_email_verification`, or `published`.
6. **Account authentication** — ordinary email/password login, one free account registration when the site explicitly reports no account exists, and matching email verification are authorized through `account-authentication.md`. Execute that flow and continue after success. Use `blocked_account_or_email_policy` only when the required action falls outside that standing authorization.
7. **Required verified product data** — only after the route remains eligible, compare required form fields with the explicit Shipmore Product fields. Missing required independent facts become `blocked_missing_verified_data`.
8. **Verification challenge** — expose CAPTCHA, Turnstile, email challenge, or similar native verification. Unresolved manual verification becomes `blocked_manual_verification`.
9. **Form execution** — only now enter mutable product-listing fields and proceed toward a final action.

Example: if a directory both requires a contact email and mandates a reciprocal badge, register and verify the badge first. If verification times out, stop with a truthful blocked/ineligible result containing `backlink verification timeout`; do not relabel it as missing email and do not submit.

## Mandatory backlink registration and verification

After confirming that the live directory truly mandates a backlink or badge:

1. Confirm the claim's `runItemId`, `workerId`, `productUrl`, and `directoryUrl`; heartbeat and stop immediately on lease failure.
2. Run `python3 scripts/shipmore_queue_client.py add-outbound-link --run-item-id <id> --product-url <productUrl> --directory-url <directoryUrl>`.
3. The command posts `{runItemId, workerId}` to `POST {BACKLINK_APP_URL}/api/outbound-links`, then fetches only the Product homepage every 20 seconds for up to 6 attempts. It heartbeats before every fetch.
4. Accept success only when parsed homepage `<a href>` hostname and path exactly match parsed `directoryUrl`. Scheme, leading `www.`, and trailing slash may differ. Reject substring/suffix hosts and different paths.
5. The standard CLI checks server-returned HTML after normal redirects. If the link is client-rendered, inspect the final homepage DOM with an authorized browser using the same parsed-anchor rule. Do not inspect inner pages or bypass CAPTCHA/WAF/access controls.
6. Continue the original directory form only when the command returns JSON with `success=true` and `reason=backlink_verified` (or equivalent final-DOM evidence is established while the lease remains valid).
7. If registration fails, lease ownership is lost, or all 6 checks miss the link, stop before submission. Record `backlink verification timeout` for the six-attempt case and use the closest truthful blocked/ineligible state.

## Product-field mapping

Prefer explicit claim fields for directory forms:

| Directory field | Shipmore source |
| --- | --- |
| Product / tool name | `productName` |
| Website | `productUrl` |
| Tagline | `productTagline`; if blank, a truthful short derivation from `productDescription`/`productMarkdown` is allowed |
| Description | `productDescription`; length-constrained truthful rewrites may use `productMarkdown` |
| Category | `productCategoryId` plus directory-specific category choices; map semantically, do not invent a category claim |
| Pricing model | `productPricingModel`; otherwise verify from a current official product surface before using a pricing claim |
| Product Twitter / X | `productTwitterUrl` |
| GitHub repository / source code / repository URL | `productGithubRepoUrl` |
| Contact email | `productContactEmail` only, unless a current official product page explicitly verifies another authorized address |
| Company | `productCompanyName` |
| Founder | `productFounderName` |
| LinkedIn | `productLinkedinUrl` |
| Founder / your GitHub profile | `productFounderGithubUrl` |
| Logo | `productLogo` |
| Primary image | `productOgImage` |

Do not use the deprecated `productGithubUrl` alias for new field mapping. It exists only for backward compatibility and represents the founder GitHub value, not a repository.

Repository semantics are strict: `productGithubRepoUrl` may fill fields such as GitHub Repository, Source Code, Source URL, Repository URL, or Open Source URL. `productFounderGithubUrl` may fill fields such as Your GitHub, Founder GitHub, or GitHub Profile. Never swap these merely because both URLs use github.com.

A repository URL alone does not prove that a Product is open source. If a directory asks whether the Product is open source, requires an OSS license, or has OSS-only eligibility, verify that fact independently from an authorized current source. If it cannot be verified, do not answer `yes` based only on `productGithubRepoUrl`.

Do not derive independent identity/contact facts from marketing prose. In particular, never guess email addresses, founder names, company names, social accounts, launch dates, legal identity, or open-source status.

If a required field is absent after the eligible-route preflight and cannot be verified read-only from an official source, use `blocked_missing_verified_data`. Optional unknowns remain blank.

## Existing-state decisions

### Already published

Do not resubmit. Verify the public listing only when follow-up work is actually intended by the Run. Otherwise complete the Run Item as `skipped` and preserve `published`.

### Submitted / awaiting approval

Do not resubmit. Check only the available authorized follow-up surfaces when the Run is intended for follow-up. Otherwise skip and preserve the status.

### Awaiting email verification

Do not create another submission. Use the authorized `gws` mailbox workflow in `account-authentication.md` to find the matching post-trigger code/link, complete the site's native verification in the same browser session, and continue the appropriate follow-up. If no confident match arrives within the bounded poll window, preserve the lifecycle state and leave a follow-up.

## Default account authentication

When the directory requires an account, follow `account-authentication.md` instead of stopping with `account_strategy_required`:

1. Reuse an authorized existing session, otherwise attempt one login with runtime-secret variables.
2. Register one ordinary free account only after an explicit no-account/not-registered signal.
3. Use verified Shipmore fields for any required identity fields; never invent missing identity/contact data.
4. Retrieve only the matching verification message through `gws`; keep OTPs/magic links ephemeral and out of logs/evidence.
5. Heartbeat after login/registration navigation and while waiting for email.
6. After authentication succeeds, continue the same Run Item and original directory submission rather than completing it as blocked.
7. Stop on CAPTCHA, phone/KYC/passkey/manual approval, paid registration, ambiguous mailbox matches, missing required identity, rejected credentials without a safe registration path, or lease loss.

### Submission outcome unknown

Never press Submit again as the first response. Check, in order when available:

1. account/backend submission history;
2. authorized mailbox receipt;
3. public listing/search page.

If still unresolved, preserve `submission_outcome_unknown` and schedule follow-up.

## Heartbeat discipline

Heartbeat before any step that may mutate the site and after any step that consumes meaningful time.

For a 300-second lease, target 60–120 second heartbeat spacing.

Heartbeat again after:

- login or account navigation;
- page reload/redirect that changes the form state;
- manual verification handoff;
- asset upload;
- long content preparation;
- returning from user interaction;
- immediately before final submit if the previous heartbeat is no longer comfortably fresh.
- before outbound-link registration and before every homepage verification attempt.

If heartbeat returns 409, stop. Do not make a final submission or Complete request as if ownership were still valid.

## Final-action protocol

Immediately before final action:

1. Confirm the active Directory and submission route.
2. Confirm Product identity and canonical URL.
3. Review required fields for truthful values.
4. Ensure no unauthorized newsletter, promotion, payment, legal agreement, or unrelated action is selected; any mandatory backlink has already passed the authorized verification flow.
5. Recheck verification/challenge validity.
6. Heartbeat if needed.
7. Perform one final action.
8. Read the resulting state fresh.

Never infer success merely from the click itself.

## Evidence

Prefer an opaque evidence reference managed by the active runtime/evidence system. Do not store secrets or session material.

Useful evidence includes:

- exact confirmation message;
- server receipt identifier that is safe to retain;
- public listing URL;
- policy page showing ineligibility/paid-only state;
- explicit rejection message;
- authorized user confirmation for a manual step.

Do not duplicate `productContactEmail` or other private contact details into evidence labels, exact-result summaries, or shareable logs merely because they were used in the form.

## Stable completion event ID

The event ID must be stable for one logical Complete operation.

Recommended shape:

```text
shipmore:<runItemId>:complete:<opaque-random-id>
```

Generate it once before the first Complete attempt and retain it until a definite response is received.

If Complete times out or the connection drops after sending, retry with the same event ID and same logical completion fields.

Do not reuse that event ID for another Run Item or a different result.

## Complete result construction

Build the Complete payload from observed facts, not desired metrics.

Examples:

### Accepted for review

```json
{
  "status": "completed",
  "submissionStatus": "awaiting_approval",
  "verificationStatus": "no_verification_presented",
  "exactResult": "Your product has been submitted for review"
}
```

### Manual challenge

```json
{
  "status": "blocked",
  "submissionStatus": "blocked_manual_verification",
  "verificationStatus": "awaiting_manual_verification",
  "exactResult": "Turnstile challenge requires user completion"
}
```

### Missing verified data

```json
{
  "status": "blocked",
  "submissionStatus": "blocked_missing_verified_data",
  "exactResult": "Required founder name is not available in verified product data"
}
```

Use this only after paid-only, mandatory-backlink verification, other ineligibility, existing-state, and account-policy checks have already passed.

### Ambiguous final action

```json
{
  "status": "blocked",
  "submissionStatus": "submission_outcome_unknown",
  "exactResult": "Submit request timed out after final action; acceptance not confirmed",
  "followUpNote": "Check account history, mailbox, and public page before any retry"
}
```

### Browser/runtime failure before form work

```json
{
  "status": "failed",
  "submissionStatus": "not_attempted",
  "lastError": "No supported authenticated browser control surface is available"
}
```

Use the prior lifecycle status instead of `not_attempted` when stronger truthful state already exists.

## Recovery

Recovery is infrastructure-level queue repair, not evidence that a site action failed.

An expired lease may be recovered to `queued`. A later worker must re-read the claim payload and browser/site state before continuing. Never assume the previous worker did nothing merely because its lease expired.

If the previous worker may have performed a final action before lease loss, treat the site outcome as potentially ambiguous and inspect account/mailbox/public evidence before retrying.
