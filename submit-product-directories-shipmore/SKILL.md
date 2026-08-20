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
- follow-up scheduling.

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

## Source-of-truth rules

1. Always `claim` before opening or mutating a directory submission flow.
2. Treat `data.id` from a successful claim as the `runItemId`.
3. Treat the claim payload as the verified task envelope. Do not replace its Product, Directory, or previous Submission fields with guesses.
4. `reason=claimed` means a new item was leased. `reason=reused` means this worker already owns a live item; resume that same item rather than advancing the queue.
5. Never act on a Run Item after its lease expires. Heartbeat first if there is any doubt.
6. Never change Shipmore state by direct database access from this Skill. Use the Queue API.
7. Do not turn a previously truthful state such as `published` or `awaiting_approval` into `not_attempted` merely because the current Run Item is skipped.

## Worker lifecycle

For each item:

1. Claim one item from the specified Run.
2. If the Run is paused, terminal, or empty, stop or wait as described in the API reference.
3. Inspect the returned previous Submission snapshot before browser work.
4. If the snapshot already proves that no new form action is appropriate, finish the Run Item as `skipped` while preserving the current submission status.
5. Heartbeat before mutable browser work and again after meaningful navigation, verification, user handoff, or long reasoning. A 300-second lease should normally receive a heartbeat at least every 60–120 seconds; longer browser work may request a larger lease within the API limits.
6. Apply the legitimacy, duplicate, verification, authorization, and browser-routing controls from SPD V1 Batch.
7. Perform only truthful, authorized form work. Keep optional unknown fields blank and block required unknown fields.
8. Record the exact visible/server outcome and an opaque evidence reference when evidence exists.
9. Classify the result using [references/status-mapping.md](references/status-mapping.md).
10. Before the first `complete` attempt, choose one stable `eventId`. Reuse that exact event ID if the HTTP response is lost or the request must be retried.
11. Complete the item. Never generate a new event ID for the same logical completion.
12. Claim the next item only after the previous item has a terminal Run Item result.

## Browser execution rules

- Prefer the supplied `submitUrl`; inspect and normalize it before navigation if the site redirects.
- Reuse an authorized existing session when available. Do not inspect cookies, saved passwords, local storage, recovery codes, or hidden authentication material.
- Never bypass CAPTCHA, Turnstile, email verification, browser security warnings, or site access controls.
- Do not subscribe to newsletters, accept optional promotions, pay fees, add reciprocal links, change DNS/site content, or create unrelated public content unless separately authorized.
- Do not invent founder, company, address, launch, pricing, contact, legal, or ownership facts.
- Use the returned Product fields and `productMarkdown` as source material. Summarization is allowed; factual invention is not.
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

For these states, perform only the appropriate verification/follow-up work or skip while preserving the current status. An ambiguous prior final action must be checked through available account/backend, authorized mailbox, or public-page evidence before any retry.

## CLI helper

Use the bundled standard-library client:

```bash
python3 scripts/shipmore_queue_client.py claim --run-id <runId>
python3 scripts/shipmore_queue_client.py heartbeat --run-item-id <runItemId>
python3 scripts/shipmore_queue_client.py recover --run-id <runId>
```

On Windows, `py -3` may be used instead of `python3`.

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
- required verified product data is missing;
- manual verification or authentication cannot safely continue;
- the site requires an unauthorized payment or reciprocal-site change;
- the final submission outcome is ambiguous;
- the execution backend cannot safely control the required authenticated surface.

Use a blocked/failed/skipped Run Item result and the closest truthful submission status defined in the mapping reference.

## Bundled resources

- [references/shipmore-api.md](references/shipmore-api.md): API contract and response semantics.
- [references/status-mapping.md](references/status-mapping.md): canonical Shipmore status mapping.
- [references/worker-loop.md](references/worker-loop.md): deterministic worker procedure and retry rules.
- [references/browser-control-routing.md](references/browser-control-routing.md): backend-neutral browser selection and verification rules.
- `scripts/shipmore_queue_client.py`: dependency-free Queue API client.
