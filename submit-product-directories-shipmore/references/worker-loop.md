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
2. **Paid-only / forced reciprocal / forced badge / clearly ineligible** — if the route requires payment that is not authorized, classify `paid_only`; if it requires a reciprocal link, badge, site modification, or the product clearly does not meet eligibility, classify `ineligible` and stop. Do not continue collecting missing profile fields for a route that must not be submitted.
3. **Duplicate / existing lifecycle guard** — inspect previous Shipmore state and any clear existing listing. Never blindly resubmit `submitted`, `submission_outcome_unknown`, `awaiting_approval`, `awaiting_email_verification`, or `published`.
4. **Account or email policy** — if the next required action is an unauthorized login, account creation, mailbox action, or account-policy step, classify `blocked_account_or_email_policy`.
5. **Required verified product data** — only after the route remains eligible, compare required form fields with the explicit Shipmore Product fields. Missing required independent facts become `blocked_missing_verified_data`.
6. **Verification challenge** — expose CAPTCHA, Turnstile, email challenge, or similar native verification. Unresolved manual verification becomes `blocked_manual_verification`.
7. **Form execution** — only now enter mutable product-listing fields and proceed toward a final action.

Example: if a directory both requires a contact email and mandates a reciprocal badge, the mandatory badge decides the result first. The correct state is `ineligible`, not `blocked_missing_verified_data`.

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

Do not create another submission. Use an authorized mailbox only if that capability is available and allowed. Otherwise block/preserve the existing lifecycle state and leave a follow-up.

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

If heartbeat returns 409, stop. Do not make a final submission or Complete request as if ownership were still valid.

## Final-action protocol

Immediately before final action:

1. Confirm the active Directory and submission route.
2. Confirm Product identity and canonical URL.
3. Review required fields for truthful values.
4. Ensure no unauthorized newsletter, promotion, payment, reciprocal link, legal agreement, or unrelated action is selected.
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

Use this only after paid/reciprocal/ineligibility, existing-state, and account-policy checks have already passed.

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
