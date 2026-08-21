# Shipmore Queue API contract

## Endpoint

Queue claim/heartbeat/complete/recover operations use this authenticated endpoint:

```text
POST {BACKLINK_APP_URL}/api/backlinks/agent/queue
Authorization: Bearer {BACKLINK_AGENT_TOKEN}
Content-Type: application/json
```

Never log or persist the bearer token in campaign records, evidence, screenshots, or completion metadata.

Mandatory backlink registration uses a separate endpoint implemented by the Shipmore application (not by this repository):

```text
POST {BACKLINK_APP_URL}/api/outbound-links
Authorization: Bearer {BACKLINK_AGENT_TOKEN}
Content-Type: application/json
```

Exact request body:

```json
{
  "runItemId": "<leased-run-item-id>",
  "workerId": "<same-worker-id-used-to-claim>"
}
```

Heartbeat before this call. A non-success response or a lost/foreign/expired lease is terminal for this worker attempt: stop and do not continue the directory submission.

The bundled `add-outbound-link` command performs registration plus verification. After the POST succeeds it fetches only the `productUrl` homepage, follows ordinary HTTP redirects, parses `<a href>` values, and polls every 20 seconds for at most 6 attempts. It heartbeats before each fetch. Success emits JSON with `success=true`, `reason=backlink_verified`, the attempt number, final Product URL, and matched URL. Timeout prints `backlink verification timeout` and exits nonzero.

Matching compares parsed normalized hostname and path, not raw substrings. `http`/`https`, a leading `www.`, and trailing slash differences are accepted; a suffix host such as `directory.example.evil.test` or a different path does not match. Query and fragment do not replace the required exact hostname/path identity.

The CLI verifies server-returned homepage HTML. If a Product renders the link only client-side, an authorized browser worker may instead inspect the final homepage DOM with the same parsed-anchor matching rule. Do not crawl inner pages, bypass CAPTCHA/WAF, or weaken matching to make verification pass.

## Claim

Request:

```json
{
  "operation": "claim",
  "runId": "<run-id>",
  "workerId": "<stable-worker-id>",
  "leaseSeconds": 300
}
```

Successful new claim:

```json
{
  "success": true,
  "reason": "claimed",
  "data": {
    "id": "<run-item-id>",
    "runId": "<run-id>",
    "queueOrder": 0,
    "status": "claimed",
    "claimedBy": "<worker-id>",
    "leaseExpiresAt": "...",
    "productDirectoryId": "...",
    "submissionStatus": "not_attempted",
    "verificationStatus": "not_checked",
    "directoryId": "...",
    "directoryName": "...",
    "directoryUrl": "...",
    "submitUrl": "...",
    "productId": "...",
    "productName": "...",
    "productUrl": "...",
    "productDescription": "...",
    "productCategoryId": "...",
    "productTagline": "...",
    "productPricingModel": "...",
    "productTwitterUrl": "...",
    "productGithubRepoUrl": "...",
    "productContactEmail": "...",
    "productCompanyName": "...",
    "productFounderName": "...",
    "productLinkedinUrl": "...",
    "productFounderGithubUrl": "...",
    "productGithubUrl": "..."
  }
}
```

The actual payload also includes prior submission metadata, directory attributes, Product assets, `productMarkdown`, and `productTemplate` when available.

`productGithubUrl` is a backward-compatible alias for `productFounderGithubUrl`. New worker logic must use the explicit names `productGithubRepoUrl` and `productFounderGithubUrl` so repository and personal-profile fields cannot be confused.

`data.id` is the `runItemId` used by heartbeat and complete.

### Claim reasons

- `claimed`: a queued item was newly leased to this worker.
- `reused`: this same `runId + workerId` already owns a live claimed/running item. Resume the returned item; do not advance to another one.
- `run_paused`: do not perform mutable browser work.
- `run_terminal`: Run is completed or cancelled; stop.
- `queue_empty`: no queued item remains. Stop this worker loop after any required reconciliation delay.
- `run_not_found`: invalid Run; treat as configuration/error state.

A retry of a claim whose response may have been lost must use the same `runId` and `workerId`. `reused` is the expected safe-retry result.

## Heartbeat

Request:

```json
{
  "operation": "heartbeat",
  "runItemId": "<run-item-id>",
  "workerId": "<same-worker-id-used-to-claim>",
  "leaseSeconds": 300
}
```

Success:

```json
{
  "success": true,
  "data": {
    "id": "<run-item-id>",
    "run_id": "<run-id>",
    "status": "running",
    "heartbeat_at": "...",
    "lease_expires_at": "..."
  }
}
```

The heartbeat moves a claimed item to `running` and extends the lease from the heartbeat time.

A `409` with `Lease is missing, expired, or owned by another worker` means this worker must stop mutating the directory flow and must not call complete as if it still owned the item.

## Complete

Request shape:

```json
{
  "operation": "complete",
  "eventId": "<stable-id-for-this-logical-completion>",
  "runItemId": "<run-item-id>",
  "workerId": "<same-worker-id>",
  "status": "completed",
  "submissionStatus": "awaiting_approval",
  "verificationStatus": "no_verification_presented",
  "exactResult": "Submission accepted and queued for review",
  "evidenceReference": "ev-opaque-123",
  "publicListingUrl": null,
  "followUpAt": null,
  "followUpNote": null
}
```

Terminal Run Item `status` values:

```text
completed
blocked
failed
skipped
```

Optional fields supported by the current endpoint:

```text
verificationStatus
lastError
exactResult
evidenceReference
publicListingUrl
backendCheckedAt
mailboxCheckedAt
publicPageCheckedAt
followUpAt
followUpNote
```

Date/time strings must be ISO 8601 date-time values accepted by the API.

`failed` requires a nonblank `lastError`.

`published` requires a nonblank public listing URL. Do not classify a listing as published merely because a form was submitted.

### Completion idempotency

`eventId` identifies one logical completion operation.

Before the first Complete request, select and retain one stable event ID. If the HTTP response is lost or uncertain, retry the identical logical completion with the same event ID.

Expected first success:

```text
idempotent = false
```

Expected same-operation retry:

```text
idempotent = true
```

Never generate a new event ID merely because a network response was lost.

## Recover

Recover all expired leases:

```json
{
  "operation": "recover"
}
```

Recover only one Run:

```json
{
  "operation": "recover",
  "runId": "<run-id>"
}
```

Example success:

```json
{
  "success": true,
  "data": {
    "recoveredCount": 1,
    "runIds": ["<run-id>"]
  }
}
```

Recovery changes expired `claimed`/`running` items back to `queued`, clears their worker/lease fields, and records a recovery error note. Lease expiry by itself does not instantly rewrite the row; recovery or a later claim triggers that state transition.

## Lease policy

The API currently accepts lease values from 30 to 3600 seconds.

For interactive browser work:

- 300 seconds is appropriate for short automated tests;
- heartbeat approximately every 60–120 seconds when using a 300-second lease;
- use a longer lease when a legitimate browser step is predictably long, while still heartbeating periodically;
- before a user handoff, extend the lease when possible, but do not assume the user will respond before expiry;
- after expiry, stop acting as owner and let recovery/reclaim establish a new lease.

## Claim payload as task envelope

Use the returned claim payload as the worker contract. The worker must not depend on Shipmore's internal database layout: a value may originate from a Product fact, a user submission default, or a product-specific override. Shipmore resolves that internally before returning the task.

### Run Item

```text
id
runId
queueOrder
status
claimedBy
claimedAt
heartbeatAt
leaseExpiresAt
```

### Previous Submission snapshot

```text
productDirectoryId
submissionStatus
verificationStatus
route
accountAlias
submittedAt
exactResult
evidenceReference
publicListingUrl
backendCheckedAt
mailboxCheckedAt
publicPageCheckedAt
lastCheckedAt
followUpAt
followUpNote
```

### Directory

```text
directoryId
directoryName
directoryUrl
submitUrl
directoryPricing
directoryCategory
directoryDofollow
directoryAccountRequired
```

### Product facts and content

```text
productId
productName
productUrl
productDescription
productCategoryId
productTagline
productPricingModel
productTwitterUrl
productGithubRepoUrl
productLogo
productOgImage
productMarkdown
productTemplate
```

`productGithubRepoUrl` is the official repository/source-code URL for the Product. Its presence alone does **not** prove that the Product is open source; do not answer an open-source eligibility question affirmatively without separate verified evidence.

### Effective submission identity

```text
productContactEmail
productCompanyName
productFounderName
productLinkedinUrl
productFounderGithubUrl
```

These are already effective values resolved by Shipmore from account defaults plus any product-specific override. Do not try to reconstruct fallback logic in the Skill.

Use explicit verified fields before deriving anything from prose. `productMarkdown` may be used to summarize or shorten already-supported product facts, but it is not permission to invent independent facts such as a founder, company identity, email address, launch date, pricing claim, social account, or open-source status.

If a required field has a dedicated claim property and that property is blank, do not silently infer it from unrelated text. A read-only check of the official product site may establish a current fact when the runtime can verify it clearly; otherwise use `blocked_missing_verified_data`.

`productContactEmail` is provided because some legitimate directory forms require it. Use it only for the authorized form. Do not copy the raw address into `exactResult`, evidence labels, attempt notes, screenshots, or other shareable logs unless the site itself necessarily displays it and the evidence policy explicitly permits that capture.

Do not treat `directoryDofollow` as an instruction to manipulate ranking or request a followed link. It is directory metadata only.
