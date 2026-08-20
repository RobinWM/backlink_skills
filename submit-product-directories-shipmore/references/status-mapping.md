# Shipmore status mapping

This reference maps browser-observed outcomes to the current Shipmore canonical submission state and terminal Run Item result.

## Canonical submission statuses

```text
not_attempted
form_in_progress
draft_saved
submitted
submission_outcome_unknown
awaiting_approval
awaiting_email_verification
published
blocked_manual_verification
blocked_missing_verified_data
blocked_account_or_email_policy
unavailable
paid_only
ineligible
duplicate_no_action
terminated_by_user
rejected
```

## Verification statuses

```text
not_checked
automatic_verification_passed
awaiting_manual_verification
manual_verification_completed
verification_unavailable_before_form
verification_expired_reset
no_verification_presented
deferred_by_user
```

## Run Item statuses

```text
completed
blocked
failed
skipped
```

The Run Item status describes the result of this execution attempt. The Submission status describes the Product × Directory lifecycle. Do not conflate them.

## Mapping guidance

| Browser / site outcome | Run Item | Submission status | Notes |
| --- | --- | --- | --- |
| Form accepted; no publication yet | `completed` | `submitted` | Requires concrete acceptance evidence, not just a click |
| Site says queued/pending review | `completed` | `awaiting_approval` | Record exact queue/review message |
| Site requires post-submit email verification | `blocked` | `awaiting_email_verification` | Set appropriate verification state and follow-up |
| Public listing verified | `completed` | `published` | `publicListingUrl` is mandatory |
| Final submit action happened but result cannot be determined | `blocked` | `submission_outcome_unknown` | Never blindly resubmit; schedule follow-up/checks |
| CAPTCHA/Turnstile/manual challenge blocks progress | `blocked` | `blocked_manual_verification` | Usually `awaiting_manual_verification` |
| Required truthful product field is unavailable | `blocked` | `blocked_missing_verified_data` | Do not invent data; use only after earlier terminal eligibility/policy checks pass |
| Account/email policy prevents authorized execution | `blocked` | `blocked_account_or_email_policy` | Preserve exact policy/result |
| Route/site unavailable | `completed` | `unavailable` | Use structured evidence when possible |
| Only paid placement is available and payment is not authorized | `completed` | `paid_only` | Do not pay |
| Forced reciprocal link, badge, site modification, or other prohibited placement condition | `completed` | `ineligible` | Stop before collecting missing form data or solving verification |
| Product is not eligible for this directory | `completed` | `ineligible` | Record reason |
| Directory detects an existing listing and no action is needed | `completed` or `skipped` | `duplicate_no_action` | Use only when duplicate is actually established |
| User explicitly stops this item | `skipped` | `terminated_by_user` | Do not continue later without a new Run/action |
| Directory explicitly rejects the submission | `completed` | `rejected` | Preserve exact rejection reason |
| Operational browser/backend failure before meaningful form progress | `failed` | preserve current truthful status, often `not_attempted` | `lastError` required |
| Operational failure after fields were entered but before final action | `failed` | `form_in_progress` or `draft_saved` if truly saved | Do not label submitted |

## Preflight precedence

When multiple conditions are present, classify the first decisive condition in this order:

```text
unavailable
→ paid_only / forced reciprocal / ineligible
→ duplicate or existing lifecycle guard
→ blocked_account_or_email_policy
→ blocked_missing_verified_data
→ blocked_manual_verification
→ form execution
```

This avoids false attention work. A directory that mandates a reciprocal badge is already ineligible under the worker policy; the fact that its form also requires an email must not turn it into `blocked_missing_verified_data`.

## Preserve prior lifecycle state when skipping

A Run may contain an item whose previous submission snapshot already has meaningful state.

If no new action is appropriate, `status=skipped` does not imply `submissionStatus=not_attempted`.

Examples:

```text
previous submissionStatus = published
current Run Item result   = skipped
complete submissionStatus = published
```

```text
previous submissionStatus = awaiting_approval
current Run Item result   = skipped
complete submissionStatus = awaiting_approval
```

This prevents the execution queue from destroying the lifecycle snapshot.

## Submitted is not published

Never use `published` unless a public listing URL has been verified. Shipmore enforces a nonblank `publicListingUrl` for the `published` state.

A form acceptance, review queue, email receipt, dashboard record, or pending moderation state is not publication.

## Ambiguous final action

Use `submission_outcome_unknown` when all of the following are true:

1. a final action may have reached the site;
2. the worker cannot prove acceptance or failure;
3. retrying Submit could create a duplicate or repeated application.

Set the Run Item to `blocked`, preserve the exact result/error, record backend/mailbox/public-page checks when performed, and schedule follow-up when appropriate.

Do not convert ambiguity to `failed` merely to make the queue look cleaner.

## Manual verification

Typical mapping:

```text
Run Item status     = blocked
submissionStatus    = blocked_manual_verification
verificationStatus  = awaiting_manual_verification
```

After a user legitimately completes the challenge, a later authorized execution may continue through a new/recovered Run Item. Recheck challenge validity before form submission.

## Missing product data

Use:

```text
Run Item status    = blocked
submissionStatus   = blocked_missing_verified_data
```

Only use this after the route remains eligible and account-policy checks have passed.

Prefer explicit Shipmore Product fields such as `productContactEmail`, `productCompanyName`, `productFounderName`, `productPricingModel`, and the verified social URLs. Examples of legitimate missing-data blockers include a required founder name, company identity, contact email, legal identity, pricing fact, or other independent fact that is absent from verified Product data and cannot be established read-only from an official source.

Optional unknown fields should remain blank instead of causing a block.

## Operational failures

A browser crash, unsupported control backend, transient network failure, or tool/runtime exception is not automatically a directory rejection.

Use `failed` for the Run Item and keep the closest truthful Submission state. Always send `lastError`.

Do not overwrite a known `published`, `awaiting_approval`, or other stronger existing lifecycle state with `not_attempted` because the current worker failed.
