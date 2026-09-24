# 外链自动提交合并版 — 批次状态模型

## Required campaign controls

- SPD version: `V1 Batch`
- Campaign ID and last-updated timestamp
- Product canonical ID and canonical URL
- Source-list reference
- Batch authorization reference
- Execution-shard size and maximum active tabs
- Credential and evidence policy
- Duplicate and ambiguous-outcome policy

## Required site fields

- Queue ID
- Website and platform domain
- Route and account alias
- Idempotency key
- Execution shard
- Legitimacy gate
- Authorization reference
- Status
- Action channel: `web form` or `official contact email`; legacy records without this field are treated as `web form`
- Recipient contact alias: required for `official contact email`; never a raw email address in a shareable record
- Contact-source evidence: required for `official contact email`; controlled proof of the official Contact/submit/partner page or `mailto:`
- Mailbox pre-send check: `cleared`, `prior outreach found`, or `inconclusive — user-authorized direct attempt` for `official contact email`
- Mailbox pre-send evidence: controlled evidence of Gmail Sent/Drafts/All Mail and record search for `official contact email`
- Email send attempts: `0` or `1`; required for `official contact email`
- Gmail send receipt: `not applicable`, `Gmail confirmed sent`, `sent copy verified`, `no clear receipt`, or `send failed`
- Content surface: exactly one of `not applicable`, `short note — no action`, `long post — no action`, or `unknown — no action`
- Content-surface evidence: for non-`not applicable`, the native entry URL, label, editor, or workflow evidence used to classify it
- Verification preflight
- Outcome-check attempts: `0` unless a final action has an ambiguous result; then exactly `2` or `3` read-only receipt-check passes
- Handover page: `not applicable`, or the retained target/tab identifier and current route for a verification or ambiguous-outcome handoff
- Fields entered and omitted
- Agreements and subscriptions
- Submit timestamp
- Exact result
- Evidence reference
- Last checked
- Follow-up

## Canonical statuses

- `not attempted`
- `form in progress`
- `draft saved`
- `submitted`
- `email sent — awaiting reply`
- `email send outcome unknown`
- `submission outcome unknown`
- `awaiting approval`
- `awaiting email verification`
- `published`
- `blocked — manual verification`
- `blocked — missing verified data`
- `blocked — account or email policy`
- `unavailable`
- `paid-only`
- `ineligible`
- `duplicate — no action`
- `terminated by user`

## Verification states

- `not checked`
- `automatic verification passed`
- `awaiting manual verification`
- `manual verification completed`
- `verification unavailable before form`
- `verification expired/reset`
- `no verification presented`
- `deferred by user`

## Invariants

- Use `submitted` only with a submit timestamp, exact server acknowledgment, and evidence reference. Use `email sent — awaiting reply` only for an official Contact email with a Gmail send receipt; it proves only that Gmail sent the message, not delivery, reply, listing, link placement, or publication.
- Use `published` only after checking a public listing URL.
- Use `submission outcome unknown` after an ambiguous final action; never retry it. Complete exactly two or three bounded, read-only receipt-check passes across the current page/target, backend, mailbox, and public page as available, then preserve the page for manual inspection if no decisive receipt exists.
- Keep `not attempted` free of entered listing fields, agreements, and submit timestamps.
- An official Contact-email route is a separate non-content-editor route. It requires current-batch email authorization, a verified Gmail sender alias, one public official recipient route, a pre-send Gmail/record duplicate check, and no CC/BCC. One target domain and official contact route may receive at most one initial email per product per authorized batch. Do not follow up, reply, resend, or switch recipient automatically.
- For an official Contact email record, `Platform domain` is the target registrable root domain and must equal the Website host or be its parent domain. The audit strips a leading `www.` and permits only one official Contact-email record for the same product and target root domain in a batch; resume that record instead of creating another route or recipient.
- Use `email send outcome unknown` only after one `Send` action with no decisive Gmail receipt. Complete exactly two or three read-only checks of the Gmail compose/thread, Sent/All Mail, and Drafts/Outbox; retain the page and do not send again. Do not apply form-only backend/public-page checks to this email state.
- A `web form` must not use either email-specific state. An `official contact email` must not use `submitted`, `submission outcome unknown`, `awaiting approval`, `awaiting email verification`, or `published`; it instead uses the email-specific state above.
- `official contact email` must use `Content surface: not applicable`. A Contact email request may not ask the recipient to create a short post, long post, guest article, draft, or other content-editor entry; the short/long-content no-action rule remains unchanged.
- When verification is unresolved, prefill every field that can be truthfully completed, upload applicable media, and retain the handover page; only unknown or inapplicable fields may remain blank with a recorded reason. Do not close the tab or click the final action.
- Do not execute a failed legitimacy gate or missing/expired authorization.
- Do not enter fields or submit unless the brand-first on-site duplicate check is recorded as `cleared`, `not available — user-authorized direct attempt`, or `inconclusive — user-authorized direct attempt`. The latter two require evidence of the incomplete check and a batch authorization reference, permit exactly one final submission attempt, and never permit a retry.
- Keep idempotency keys unique across the campaign.
- Treat registration, login, draft save, navigation, a click, or a generic thank-you page as insufficient evidence of submission.
- `short note — no action`, `long post — no action` and `unknown — no action` all prohibit content entry or prefill, draft saving, manual handoff, submission and publication. Record classification evidence only. A content-editor-only site is `ineligible`, not `unavailable`; a generic `Post` label creates no exception.
- Registration, login and no-cost, clearly labeled marketing-subscription opt-ins require current-batch authorization. They never authorize a paid plan, auto-renewal, purchase, donation, or added legal/financial commitment.
- Never store secrets, raw contact data, private session IDs, or tokenized authentication URLs in the shareable record.

## Audit commands

在技能根目录执行：

```bash
python3 scripts/audit_submission_record.py path/to/record.md
python3 scripts/audit_submission_record.py path/to/record.md --json
```
