# Shipmore Queue API contract

## Endpoint

All worker operations use one authenticated endpoint:

```text
POST {BACKLINK_APP_URL}/api/backlinks/agent/queue
Authorization: Bearer {BACKLINK_AGENT_TOKEN}
Content-Type: application/json
```

Never log or persist the bearer token in campaign records, evidence, screenshots, or completion metadata.

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
    "productContactEmail": "...",
    "productCompanyName": "...",
    "productFounderName": "...",
    "productPricingModel": "...",
    "productTwitterUrl": "...",
    "productLinkedinUrl": "...",
    "productGithubUrl": "..."
  }
}
```

The actual payload also includes prior submission metadata, directory attributes, Product assets, `productMarkdown`, and `productTemplate` when available.

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

Use these fields from the returned payload rather than re-discovering them from unrelated sources when they are present.

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

### Product identity and content

```text
productId
productName
productUrl
productDescription
productCategoryId
productLogo
productOgImage
productMarkdown
productTemplate
```

### Verified directory-submission facts

```text
productTagline
productContactEmail
productCompanyName
productFounderName
productPricingModel
productTwitterUrl
productLinkedinUrl
productGithubUrl
```

Use the explicit verified fields before deriving anything from prose. `productMarkdown` may be used to summarize or shorten already-supported product facts, but it is not permission to invent independent facts such as a founder, company identity, email address, launch date, pricing claim, or social account.

If a required field has a dedicated claim property and that property is blank, do not silently infer it from unrelated text. A read-only check of the official product site may establish a current fact when the runtime can verify it clearly; otherwise use `blocked_missing_verified_data`.

`productContactEmail` is provided because some legitimate directory forms require it. Use it only for the authorized form. Do not copy the raw address into `exactResult`, evidence labels, attempt notes, screenshots, or other shareable logs unless the site itself necessarily displays it and the evidence policy explicitly permits that capture.

Do not treat `directoryDofollow` as an instruction to manipulate ranking or request a followed link. It is directory metadata only.
