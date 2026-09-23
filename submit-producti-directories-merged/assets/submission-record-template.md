# [Campaign name] — SPD V1 Batch Record

Last updated: [ISO-8601 timestamp]

## Campaign controls

- SPD version: V1 Batch
- Campaign ID: [opaque ID]
- Product canonical ID: [opaque product ID]
- Canonical URL: [public URL]
- Source-list reference: [controlled reference]
- Batch authorization reference: [opaque authorization ID]
- Execution-shard size: [number]
- Maximum active tabs: [number]
- Credential policy: aliases only; no secrets in record
- Evidence policy: controlled evidence IDs only
- Duplicate policy: never execute a completed or pending idempotency key
- Ambiguous-outcome policy: backend, mailbox, and public-page checks before retry
- Ranking manipulation prohibited: yes
- Record scope: shareable

## Source list

1. [submission URL]

## [Queue ID] — [Website name]

> `Content surface` 对非内容编辑器入口填 `not applicable`。若仅识别到短贴、长文或无法分类的内容编辑器，填相应的 `— no action` 值并保留分类证据；不得填写内容、存草稿、交人工、提交或发布。

- Queue ID: [stable ID]
- Website: [normalized submission URL]
- Platform domain: [domain]
- Route: [directory listing / claim / product profile]
- Account alias: [alias or not applicable]
- Idempotency key: [domain|product|account|route]
- Execution shard: [shard ID]
- Legitimacy gate: [passed / failed]
- Authorization reference: [opaque authorization ID]
- Status: not attempted
- Action channel: web form
- Recipient contact alias: not applicable
- Contact-source evidence: not applicable
- Mailbox pre-send check: not applicable
- Mailbox pre-send evidence: not applicable
- Email send attempts: 0
- Gmail send receipt: not applicable
- Content surface: not applicable
- Content-surface evidence: not applicable
- Verification preflight: not checked
- Duplicate check: not checked
- Duplicate evidence: not applicable
- Direct-attempt authorization: not applicable
- CDP retry decision: not applicable
- CDP retry evidence: not applicable
- Outcome-check attempts: 0
- Handover page: not applicable
- Fields entered: none
- Fields omitted: all
- Agreements/subscriptions: none
- Submit timestamp: not submitted
- Exact result: not attempted
- Evidence reference: not applicable
- Public listing URL: not applicable
- Backend checked: not applicable
- Mailbox checked: not applicable
- Public page checked: not applicable
- Last checked: [ISO-8601 timestamp]
- Follow-up: [action, owner alias, deadline]

### Attempt log

- [ISO-8601 timestamp] | event_id=[opaque ID] | action=[canonical action] | result=[result] | evidence=[opaque reference]
