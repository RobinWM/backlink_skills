---
name: submit-product-directories-shipmore
description: Shipmore-backed product-directory submission worker. Consume durable submission runs from the Shipmore Queue API, keep leases alive, use the returned Product/Directory/Submission snapshot as the source of truth, execute authorized browser form work with SPD V1 Batch safety rules, classify the exact result, and complete the run item idempotently. Use when Shipmore has already created a submission run and Codex should act as the browser worker. Do not create a second local queue or overwrite Shipmore state with inferred success.
---

# Shipmore Directory Submission Worker

## Role

This Skill is an execution worker, not a queue owner.

Shipmore is authoritative for:

- Product × Directory current state (`product_directory`);
- durable Run / Run Item ordering;
- active-work deduplication;
- worker leases and recovery;
- append-only completion events;
- follow-up scheduling;
- verified Product facts and effective submission identity supplied to directory forms.

This Skill is authoritative only for the browser-side observation and action performed while it owns a valid lease.

Never create a parallel Markdown queue, local queue cursor, or second canonical submission record.

## Required configuration

Use non-secret runtime environment variables. Never print the agent token.

```text
BACKLINK_APP_URL=https://shipmore.app
BACKLINK_AGENT_TOKEN=<secret>
BACKLINK_WORKER_ID=<stable worker alias, e.g. codex-windows-01>
```

The caller must also provide a Shipmore `runId`.

Read these references before mutable work:

1. [references/shipmore-api.md](references/shipmore-api.md)
2. [references/status-mapping.md](references/status-mapping.md)
3. [references/worker-loop.md](references/worker-loop.md)
4. [references/browser-control-routing.md](references/browser-control-routing.md)
5. [references/account-authentication.md](references/account-authentication.md)

## Source-of-truth rules

1. Always `claim` before opening or mutating a directory submission flow.
2. Treat `data.id` from a successful claim as the `runItemId`.
3. Treat the claim payload as the verified task envelope. Do not replace its Product, Directory, or previous Submission fields with guesses, and do not reconstruct Shipmore's internal default/override logic in the Skill.
4. Prefer explicit Product facts (`productTagline`, `productPricingModel`, `productTwitterUrl`, `productGithubRepoUrl`) and effective submission identity (`productContactEmail`, `productCompanyName`, `productFounderName`, `productLinkedinUrl`, `productFounderGithubUrl`) before deriving anything from `productDescription` or `productMarkdown`.
5. `productGithubRepoUrl` is a Product repository; `productFounderGithubUrl` is a person/profile URL. Never substitute one for the other. The legacy `productGithubUrl` field is compatibility-only and represents founder GitHub.
6. A GitHub repository URL alone does not prove open-source status, license, or OSS eligibility.
7. Summarizing or shortening supported product copy is allowed. Inventing independent facts such as emails, founders, companies, legal identity, pricing, social accounts, or open-source status is not.
8. `reason=claimed` means a new item was leased. `reason=reused` means this worker already owns a live item; resume that same item rather than advancing the queue.
9. Never act on a Run Item after its lease expires. Heartbeat first if there is any doubt.
10. Never change Shipmore state by direct database access from this Skill. Use the Queue API and the authorized outbound-link endpoint.
11. Do not turn a previously truthful state such as `published` or `awaiting_approval` into `not_attempted` merely because the current Run Item is skipped.

## Worker lifecycle

For each item:

1. Claim one item from the specified Run.
2. If the Run is paused, terminal, or empty, stop or wait as described in the API reference.
3. Inspect the returned previous Submission snapshot before browser work.
4. If the snapshot already proves that no new form action is appropriate, finish the Run Item as `skipped` while preserving the current submission status.
5. Heartbeat before mutable browser work and again after meaningful navigation, verification, user handoff, or long reasoning. A 300-second lease should normally receive a heartbeat at least every 60–120 seconds; longer browser work may request a larger lease within the API limits.
6. Apply the mandatory preflight order from [references/worker-loop.md](references/worker-loop.md): unavailable → paid-only → mandatory-backlink registration and verification → other ineligibility → existing lifecycle/duplicate → authorized account login/registration/email verification → missing verified data → other verification → mutable form execution.
7. Perform only truthful, authorized form work. Keep optional unknown fields blank and block required unknown fields only after earlier terminal eligibility/policy checks have passed.
8. Record the exact visible/server outcome and an opaque evidence reference when evidence exists.
9. Classify the result using [references/status-mapping.md](references/status-mapping.md).
10. Before the first `complete` attempt, choose one stable `eventId`. Reuse that exact event ID if the HTTP response is lost or the request must be retried.
11. Complete the item. Never generate a new event ID for the same logical completion.
12. Claim the next item only after the previous item has a terminal Run Item result.

## Browser execution rules

- Prefer the supplied `submitUrl`; inspect and normalize it before navigation if the site redirects.
- Reuse an authorized existing session when available. Do not inspect cookies, saved passwords, local storage, recovery codes, or hidden authentication material.
- When a directory requires authentication, follow [references/account-authentication.md](references/account-authentication.md). Use the claim payload's effective `productContactEmail` as the account email and attempt the authorized methods in order: existing Google session, existing GitHub session, native email code/magic link (for a Google-hosted mailbox, use authorized `gws` first; only if `gws` is unavailable, use an existing matching Gmail session at `https://mail.google.com`), then email/password. Create one ordinary free account only when the site explicitly reports that no account exists, then continue the original submission after successful authentication.
- Never print, persist, screenshot, or place credentials, OTPs, magic links, or mailbox content in Shipmore evidence. Runtime credentials live outside the repository in the configured secret file.
- Never bypass CAPTCHA, Turnstile, email verification, browser security warnings, or site access controls. Completing the site's normal email verification with the authorized mailbox is allowed; bypassing or weakening it is not.
- Do not subscribe to newsletters, accept optional promotions, pay fees, manually edit the Product site, change DNS, or create unrelated public content. A mandatory backlink/badge is handled only through Shipmore's authorized outbound-link endpoint and the verification flow below.
- When the directory mandates a backlink or badge, heartbeat, call `POST /api/outbound-links` with the leased `runItemId` and same `workerId`, then verify the Product homepage before doing any directory form work. Do not classify it immediately as `ineligible`.
- Poll `productUrl` homepage HTML every 20 seconds, at most 6 attempts. Heartbeat before registration and every attempt; stop immediately if lease ownership is lost. Continue the original directory submission only after an exact parsed `<a href>` match for `directoryUrl` is visible in homepage HTML (or the final browser DOM when HTML is client-rendered).
- Link comparison uses parsed hostname and path: scheme and query/fragment are not identity, while leading `www.` and a trailing slash are normalized. Hostname and path must otherwise match exactly. Never use substring matching. Do not bypass CAPTCHA, WAF, or access controls to verify the page.
- If all 6 checks fail, do not submit. Complete with the closest truthful blocked/ineligible state and include `backlink verification timeout` in the exact result/error.
- Do not invent founder, company, address, launch, pricing, contact, legal, ownership, or open-source facts.
- Use the returned verified Product fields as primary form inputs. `productDescription` and `productMarkdown` may support truthful length-constrained copy generation, but must not be used to fabricate independent identity/contact facts.
- Treat `productContactEmail` as form input, not logging material. Do not duplicate it into `exactResult`, evidence labels, or shareable attempt notes merely because it was submitted.
- A click, navigation, cleared form, disabled button, or generic thank-you page is not by itself proof of submission.
- `submitted` is not `published`.
- A final-action ambiguity must become `submission_outcome_unknown`; never blindly press Submit again.

## Existing-state guard

Before form work, inspect `submissionStatus` from the claim payload.

Do not automatically resubmit when it is already one of:

```text
submitted
submission_outcome_unknown
awaiting_approval
awaiting_email_verification
published
```

For these states, perform only the appropriate verification/follow-up work or skip while preserving the current status. An ambiguous prior final action must be checked through available account/backend, authorized mailbox, or public-page evidence before any retry. For `awaiting_email_verification`, use the authorized Gmail mailbox workflow in `account-authentication.md`: prefer `gws`, with the existing matching Gmail web session as the fallback only when `gws` is unavailable.

## CLI helper

Use the bundled standard-library client:

```bash
python3 scripts/shipmore_queue_client.py claim --run-id <runId>
python3 scripts/shipmore_queue_client.py heartbeat --run-item-id <runItemId>
python3 scripts/shipmore_queue_client.py add-outbound-link \
  --run-item-id <runItemId> \
  --product-url <productUrl> \
  --directory-url <directoryUrl>
python3 scripts/shipmore_queue_client.py recover --run-id <runId>
```

On Windows, `python` or `py -3` may be used when available.

Completion example:

```bash
python3 scripts/shipmore_queue_client.py complete \
  --run-item-id <runItemId> \
  --event-id <stableEventId> \
  --status completed \
  --submission-status awaiting_approval \
  --verification-status no_verification_presented \
  --exact-result "Submission accepted and queued for review"
```

Do not place `BACKLINK_AGENT_TOKEN` on the command line when an environment variable can be used.

## Stop conditions

Stop browser execution and preserve truthful state when:

- the lease is missing, expired, or owned by another worker;
- the Run is paused/cancelled/completed;
- the route is paid-only without payment authorization;
- mandatory backlink registration is rejected, the lease is lost while polling, or homepage verification times out after 6 attempts;
- required verified product data is missing after earlier eligibility/policy checks pass;
- manual verification or authentication cannot safely continue;
- account/email policy requires an action outside the standing authorization in `account-authentication.md`;
- the final submission outcome is ambiguous;
- the execution backend cannot safely control the required authenticated surface.

Use a blocked/failed/skipped Run Item result and the closest truthful submission status defined in the mapping reference.

## Bundled resources

- [references/shipmore-api.md](references/shipmore-api.md): API contract and response semantics.
- [references/status-mapping.md](references/status-mapping.md): canonical Shipmore status mapping.
- [references/worker-loop.md](references/worker-loop.md): deterministic worker procedure, product-field mapping, preflight precedence, and retry rules.
- [references/browser-control-routing.md](references/browser-control-routing.md): backend-neutral browser selection and verification rules.
- [references/account-authentication.md](references/account-authentication.md): authorized default-account login, free registration, secure runtime credentials, and Gmail verification through `gws` with a Gmail web fallback when `gws` is unavailable.
- `scripts/shipmore_queue_client.py`: dependency-free Queue/outbound-link API client and homepage backlink verifier.
