---
name: submit-producti-directories-merged
description: 外链自动提交合并版：在已授权范围内批量处理产品目录投递和一对一官方 Contact 邮件申请，包含去重、验证、结果取证与可恢复审计。用于执行或审计 SPD V1 外链投递任务。
---

# 外链自动提交合并版 — SPD IDP V1

## Version identity

- Canonical name: `submit-producti-directories-merged`.
- Chinese name: 外链自动提交合并版。
- Invocation: `$submit-producti-directories-merged`.
- Optimize for queue throughput, repeatability, verification handling, and recovery across large source lists.
- Apply a fast legitimacy gate, not the deeper editorial and referral-value analysis used by `$submit-product-directories-v2-quality`.
- Route campaigns requiring careful site selection, durable-placement analysis, or SEO-quality evidence to V2 Quality.
- Before planning or browser work, also read [SKILL-LOCAL-IMPROVEMENTS.md](SKILL-LOCAL-IMPROVEMENTS.md). Its local workflow additions apply alongside this core skill; where an instruction conflicts with platform policy or the user's current request, follow the higher-priority instruction.

## Core philosophy (user-confirmed 2026-08-26)

SPD IDP is **not** about full automation. Its core is: **efficiently batch-execute the simple, automatable outbound-link promotion work, then filter out the complex websites that require human execution, and hand them over to a human wrap-up at the end of the batch.** This raises batch throughput and improves the human-machine interaction experience.

- The machine's role is a "sweeper": run the whole automatable range (direct forms, routine registration/login and low-risk verification) at batch speed, with capture, judging, and evidence.
- The machine also acts as a filter: surface complex sites (strong anti-automation, payment, forced reciprocal linking, editorial-content or account-ownership anomalies, unreachable) into a manual queue, keeping the tab and field card for the human.
- The human only handles the filtered complex items, in a batched wrap-up at the end, guided by field cards — not interrupted site by site.

## Context-compaction recovery

After any context compression or summary-based continuation, re-read this `SKILL.md` and [SKILL-LOCAL-IMPROVEMENTS.md](SKILL-LOCAL-IMPROVEMENTS.md) before resuming. Re-inspect the current campaign workspace: its relevant product materials, configs, website list, records, evidence, and any in-progress queue state. Re-establish the last verified state from files and evidence rather than relying on the summary alone. If workflow confirmation or authorization is absent or uncertain after recovery, present the required workflow again and obtain confirmation before continuing. Do not take irreversible actions until this recovery is complete. After recovery, also pass the execution checklist below against the current batch before acting.

## Mandatory execution checklist (local EXEC-CHECKLIST.md)

Reading the skill files is **not** application. Before the final action on each site, and again after judging the outcome, pass the [EXEC-CHECKLIST.md](EXEC-CHECKLIST.md) items (reachability, exposure identification incl. project entries, do-not-stop-at-paid paths + redirect verification, on-site dedup, login ladder, fingerprint-browser master-client prohibition, flow/media pre-checks, controlled-form return-read, fail-fast, backend check, tab hygiene, truthful state) and record `checklist PASS/FAIL` (with the reason for any FAIL) in that site's record; do not submit before the checklist passes. New lessons must be added to the checklist as check items — not just to long-form documents.

## Mandatory workflow confirmation

At the beginning of every separate use of this skill, ask the user to confirm the workflow below in order. Do not treat confirmation from an earlier use as continuing authorization. If the workflow changes, present it again and obtain a new confirmation.

1. Confirm the internal materials: verified product profile, brand rules, contact and credential aliases, an authorized signed-in Gmail sender alias for any contact-email lane, approved copy, and compliant image assets.
2. Confirm the technical path and available tools: browser profile, CDP port, backend, automation boundaries, and reusable tools/scripts. Also ask the user whether to drive automation with **CDP (DevTools direct connection, recommended)** or **CU (Computer Use desktop control)**; do not start until the user chooses.
3. Confirm the required computer-system permissions and authorizations: for example browser control, screenshots/accessibility, workspace read/write access, authorization to call Feishu/Lark CLI for email verification, and—when contact-email outreach is in scope—authorization to send from the verified signed-in Gmail sender alias.
4. Only after steps 1–3 are confirmed, request or accept the website list and begin the work.

Standing authorization in local §18.4 covers ordinary registration/login and no-cost marketing-subscription opt-ins for future SPD IDP work; do not ask again for those actions unless the user revokes it. Official-contact email outreach is allowed only when the current batch authorization includes it and names the Gmail sender alias. Payment, recurring charges, forced reciprocal changes, account-ownership anomalies, strong anti-automation bypass, bulk mail, automatic follow-ups, and final publication outside the approved scope remain outside that standing authorization.

Do not start preflight, open a browser, enter data, submit forms, or modify campaign records until the user has confirmed the other applicable workflow steps.

## Load controls

1. Read the verified product profile, brand rules, contact and credential aliases, approved assets, source list, batch authorization, and existing record.
2. Read [references/workflow.md](references/workflow.md) before planning or browser work.
3. Read [references/status-model.md](references/status-model.md) before writing or auditing records.
4. Read [references/computer-use-bitbrowser.md](references/computer-use-bitbrowser.md) before controlling BitBrowser.
5. Copy [assets/submission-record-template.md](assets/submission-record-template.md) when no V1 Batch record exists.

Never invent product, company, founder, pricing, address, launch, ownership, contact, or legal facts. Keep optional unknowns blank and block required unknowns.

## Apply the batch legitimacy gate

Reject or separate any route that is irrelevant to the product, unavailable, unreleased-only, paid-link-only, **forced-reciprocal**, or prohibited for automated form work. An optional reciprocal-link field or optional reciprocal program is not a blocker: keep it blank unless a separate authorization covers providing it, and continue the ordinary free submission path. Do not select sites because they promise dofollow links, ranking gains, DA/DR, or backlink volume.

Use only the exact brand, product name, or naked canonical URL as public link text. Never request dofollow treatment or use repeated commercial exact-match anchors.

## Build the queue

1. Normalize hostnames and submission routes. Strip tracking parameters from the record while preserving required route parameters in controlled evidence.
2. Derive an idempotency key from platform domain, product canonical ID, account alias, and route.
3. Deduplicate before opening the browser. Never execute an idempotency key that is already submitted, awaiting approval, published, or outcome unknown.
3b. **Runtime on-site dedup (local §11.1):** before executing any site, first use the site's real native search control to search the official product/brand spelling, then its observed spelling and word-order variants, canonical URL (with and without a trailing slash), and bare hostname. For every query, capture the entered term, trigger action, result URL, result count, and visible candidate titles; do not treat an untriggered control, a stale page, or an unobserved asynchronous result as a no-result search. Also check account-backend records (My Listings/Submissions/drafts) and recent/category listings. Inspect every candidate result's outbound destination after URL normalization, rather than relying on title-text equality. If an entry resolves to the canonical hostname or canonical URL, record `duplicate — no action` with the query/result evidence and skip. If the required duplicate check cannot be proven complete, record `Duplicate check: inconclusive — user-authorized direct attempt`, the blocker, evidence, and the batch authorization reference; then complete one authorized final submission attempt, using the native duplicate receipt as outcome evidence. This exception never permits a retry: an ambiguous result still requires backend, mailbox, and public-page checks. A user-confirmed existing entry is sufficient duplicate evidence for the current batch and must not be rechecked or overridden automatically.
4. Assign stable queue IDs and execution shards. Treat shard size and maximum active tabs as operational settings, not SEO safety thresholds.
5. Classify every site into `direct form`, `account required`, `official-contact email`, `manual verification`, `email verification`, `paid/reciprocal`, `unavailable`, `ineligible`, or `unknown`.
6. Use batch-scoped authorization only when it names the allowed actions, source-list scope, approver alias, approval time, and expiry. Contact-email outreach must additionally name the authorized Gmail sender alias. Payments, reciprocal-site changes, DNS changes, and publication outside a directory require separate authorization.

## Discover verification, fully prefill, and preserve the handover page

1. Run a read-only preflight over each shard before entering product-listing fields.
2. Identify the earliest native CAPTCHA, Turnstile, image code, email check, login, or similar safeguard, but do not leave a discovered verification form blank.
3. When verification cannot be completed automatically, fill every applicable field with verified information, upload required compliant media, apply the standing no-cost marketing opt-in where present, re-read the values, and preserve the current browser tab for the manual queue. Leave only unknown or inapplicable fields blank, explain them in the record, and never close that handover tab.
4. After the user completes the queue, recheck token validity and process short-lived tokens first.
5. Do not hold more active challenge tabs than the configured browser capacity.

## Find the current submission entry point

For every website, begin navigation at its canonical homepage and locate the current submission entry point from there, using the site's own navigation, footer, account area, or other on-site links. Treat a saved, searched, or previously recorded submission URL only as historical context; do not navigate directly to it for submission. Record the currently discovered route and evidence after locating it. If no current on-site route is found, classify the site accordingly and do not infer or construct a submission URL.

**Brand-exposure identification (mandatory per site, local §19.1):** the goal is brand exposure, not only URL submission. At homepage discovery, check every executable exposure entry in the §19.1 checklist — business/merchant channel (preferred, §18.3), company/business/provider profile creation (incl. claim), directory/listing/URL-submit, free ad, press release, account-profile link slots, and **project/showcase/maker submission entries (submit the brand website homepage as a project — must be recognized and executed, not skipped)**. Separately identify any native short Note/status or long-form Post/Article editor only to record its §15 no-action classification; never use it as an execution type. Record the identified exposure entries and the chosen executable type per site. If a site has only a content editor, classify it `ineligible`; classify it `unavailable` only when it has no exposure entry at all.

**Official-contact email route (local §19.2):** A public recipient address or `mailto:` found on the target site's official Contact, submit, resource-recommendation, tool-listing, or partnership page is an additional execution type only when the current batch authorizes one-to-one contact-email outreach. Verify the signed-in Gmail sender alias, search Gmail Sent/Drafts/All Mail and the campaign record before drafting, and send at most one tailored initial request per target domain and official contact route. No CC/BCC, mailing list, automatic follow-up, resend, or identity invention is permitted.

**Content-editor exclusion (local §15 prevails):** Any general form-filling, verification, CAPTCHA-handoff, draft, or final-action instruction does not apply to a classified short, long, or unknown content editor. Record its classification evidence only; never enter or prefill content fields, save a draft, hand it to a human, submit, or publish.

**Do not stop at paid/partner paths (local §7.8):** when a Partner / Sponsored / Paid submission path is encountered, mark that paid path only as paid/skipped and keep searching the homepage for an ordinary free entry; complete the homepage-visible entry and site-redirect verification (follow 301/302/JS redirects to the final URL, record the redirect chain, and return to the homepage when a deep link is redirected into a paid/partner page) before classifying the site.

## Execute forms and official-contact emails at scale

For an official-contact email, use the verified signed-in Gmail alias only after confirming the recipient's official-contact evidence, mailbox pre-send check, and one-message limit. Compose a concise, truthful, site-relevant request for voluntary inclusion of the canonical URL. `Send` is a final action: click it once, with no CC/BCC and no retry. A Gmail send receipt proves only that the email was sent—not delivery, reply, listing, link placement, or publication.

1. Process only sites that passed the legitimacy gate, authorization check, and verification prerequisite, and either cleared the duplicate check or recorded the user-authorized direct-attempt exception.
2. Reuse approved field variants by length and category, while preserving exact public brand spelling and truthful meaning.
3. Default authorization covers ordinary registration/login and no-cost, clearly labeled marketing newsletters or promotions. Select them where present unless the user revokes this standing authorization; never select a paid plan, purchase, or recurring-charge option.
4. Review plan, cost, URL, identity, category, agreements, uploads, and verification immediately before submission.
5. Run the preflight and outcome-capture protocol below before any final action. Submit sequentially within a browser profile and record the result before advancing the queue cursor.
6. Never retry an ambiguous final action, including Gmail `Send`. For a form, run two or three bounded, read-only receipt-check passes across the current page/target, account backend, mailbox, and public page. For an official-contact email, check the Gmail compose/thread, Sent/All Mail, and Drafts/Outbox two or three times without sending again. Record the checks and preserve the page for human inspection if no decisive receipt appears.
7. Save drafts, transient failures, manual actions, and terminal outcomes as distinct states so the campaign can resume without replaying completed work.
8. **Tab hygiene (user requirement):** before opening a new batch of tabs, close/clean unrelated leftover tabs from previous batches (probe pages, hung/dead pages, completed-site leftovers) to keep active tabs within browser capacity and avoid crashes; exception: keep manual-queue handover tabs (local §4/§8.1).
9. **Controlled-form persistence and fail-fast (local §7.9):** for React/controlled forms, re-read field values after filling and before submit to confirm name/description persisted (if reset, re-fill via execCommand/native typing); on the first explicit error receipt ("Something went wrong", page error) stop the site immediately, record `outcome_unknown`/blocked with evidence, and do not retry or continue; verify backend for the product draft/pending record as success evidence; do not occupy necessary tabs (e.g., Gmail) during mailbox steps, except an authorized official-contact email lane using the verified alias, and restore them if used.
9c. **CDP retry deliberation (local §6.2):** a timeout, exception, or empty CDP response never authorizes re-running the same script. Before one changed retry, record the exact failure and current page/target state, form at least two plausible causes, and run the least-risk read-only test that distinguishes them. Never retry a final submit/publish action; repeated or unexplained failure ends the site action.
9b. **Continuous batch, no staged reports (user rule, local §8):** run the whole batch without interim progress or staged reports; after every site is attempted (blocked tabs preserved) and the record audit is completed, deliver one unified per-site report (§20). Only hard gates requiring user authorization/decisions, or the user asking, justify interrupting the batch.
10. **Fingerprint-browser master-client prohibition (user hard rule, local §6.1):** never modify the fingerprint browser server's master client (BitBrowser manager/console main window) or its window/settings under any circumstances. After context compression, re-identifying the fingerprint browser must be read-only (profile dir / DevToolsActivePort / CDP port, attach to business tabs only). The only permitted client-side action is re-opening/restarting a crashed browser profile to restore the environment (user-authorized 2026-08-28). For any other necessary action, ask the user and obtain explicit authorization before acting.

## Submission outcome protocol — transient receipts, three-signal proof, and one-shot deferral

This protocol is mandatory for every final form, native publish action, or authorized Gmail `Send`. Its purpose is to prevent a transient success page or Gmail toast from being missed by “click, sleep, read once”, and to prevent a generic thank-you page, stale tab, or unverified draft from being misreported as success. For an official-contact email, a Gmail send receipt proves only the send; it never proves delivery, reply, listing, link placement, or publication.

### 1. Preflight before action: decide first, then act

Perform a read-only preflight in this order:

1. **Reachability:** check the canonical homepage and the discovered current route with a bounded `curl`/HTTP or browser reachability check. Record status, redirect, timeout, and blocking behavior.
2. **Framework and route:** identify whether the current entry is a native form, account workflow, CMS/editor, or unsupported/unstable flow. Do not infer a route from a stale deep link.
3. **Login requirement:** determine whether login is required, whether an authorized account path is available, and whether the current browser profile is already authenticated. Do not start a form if the required identity path is unavailable or ambiguous.
4. **Category fit:** confirm that the site offers a truthful relevant category or content type for the product. If no honest category is available, classify the site before entering listing data.
5. **Hard-block decision:** if the site is unreachable, the framework cannot be operated within the authorized path, login is unavailable/ambiguous, the category is not a truthful fit, or the route requires payment, forced reciprocal linking, or a strong anti-automation challenge, record the exact blocker. For an unresolved verification on an otherwise reachable form, complete the verified-field prefill and retain the tab before deferring it; never hand over an empty form. Determine reciprocity from the native required state and explicit terms: optional reciprocal fields are left blank and do not block an otherwise eligible submission. Low-risk and ordinary native verification is attempted automatically first under the local §18.1 tiering (e.g., arithmetic fields, email codes/links, simple native click/slider steps ≤2/≤1 attempts); only after those attempts fail, or for strong anti-automation (reCAPTCHA/Turnstile/Cloudflare/complex image-selection), is it treated as an unresolved anti-automation challenge and deferred. This is a **one-shot decision**: do not keep probing or retrying the same site in the same batch.

### 2. `submitAndCapture`: capture the first state, not the eventual state

Use a `submitAndCapture()`-style helper for the one authorized click. The helper must:

- attach CDP network listeners before the click;
- click the final submit/publish control once;
- sample immediately at 0 ms and then at high frequency (roughly 100–200 ms) for a bounded capture window;
- capture, for every sample, the target/tab ID, URL, title, visible native body text, form/action state, and timestamp;
- preserve the **first state that leaves the form page** or shows a native success state, even if a 302/JS redirect immediately removes it;
- use the submission request's `Network.responseReceived` event and `Network.getResponseBody` as the fallback when the DOM success state is transient or the tab navigates away;
- never replace the captured first-success evidence with a later stale form, queue, or homepage read.

Do not use a long fixed sleep followed by a single page read as the primary evidence method. A later page read is only a bounded read-only supplement after capture, never a reason to click again.

### 3. `judgeOutcome`: require three signals and apply negative vetoes

`judgeOutcome()` must evaluate the captured evidence using three independent signals:

1. **Navigation/state signal:** the URL or native route changes away from the original form, or reaches a known success/receipt/status route.
2. **Native positive signal:** the captured page or response contains explicit positive wording tied to the current submission, such as submission received, successfully submitted, posted, listed, or awaiting review. For an official-contact email, a native Gmail “Message sent” receipt or matching Sent copy is the positive signal. Generic “thanks” text without submission context is insufficient.
3. **Independent confirmation signal:** the network response body, account submission status, mailbox receipt, or public listing/page provides corroborating evidence for the same product and action. For an official-contact email, the matching Gmail Sent copy or conversation thread is independent confirmation of the send only. Record the strongest available evidence; a public listing proves `published`, while a receipt/account state may prove only `submitted` or `awaiting approval`.

All three signals must agree for a fully confirmed submission or email send. Apply a negative veto whenever the evidence contains an error, validation failure, “not submitted”, “not yet”, “pending action”, login failure, payment requirement, Gmail draft/outbox state, or other wording that contradicts success. If signals conflict or any required signal is absent, record the appropriate unknown or blocked/manual state; do not infer success from a click, cleared form, redirect to home, generic thank-you URL, draft, or user-visible navigation alone.

### 4. Ambiguous and blocked outcomes

- A final action with no decisive result is never retried automatically. Perform two or three bounded, read-only receipt-check passes. For official-contact email, use Gmail compose/thread, Sent/All Mail, and Drafts/Outbox only; for forms, use the current target/page, account backend, mailbox, and public page as available. Record every pass, then retain the current page/target for manual inspection if no decisive receipt appears. These checks are evidence collection, never another Submit/Publish/Send click.
- A hard blocker discovered during preflight or submission is classified once and moved to the manual/deferred queue with the blocker, current route, target/tab ID, completed prefill state, and required human action. Preserve that tab; continue with the next eligible site.
- After a human completes a challenge or final action, verify the resulting receipt/status/public page without clicking submit again. User confirmation may be recorded as user-confirmed submission, but must remain distinct from independently captured `submitted` or `published` evidence.

The reusable implementation may expose `submitAndCapture()`, `judgeOutcome()`, and a CDP network-response adapter such as `createNetworkCapture()`. The campaign record must retain the captured timestamps, URL/route, target/tab identifier, native receipt summary, independent confirmation source, negative-veto result, and final state.

## Protect records

- Default recommendation: store aliases and controlled evidence IDs, not passwords, OTPs, recovery codes, cookies, OAuth parameters, magic links, raw session IDs, raw email addresses (including Contact recipients), phone numbers, or tokenized URLs.
- Local-record policy (user-confirmed 2026-08-26): this deployment's machine has leak protection, and the user authorizes plaintext credentials to be stored in the local campaign record; keep credentials out of any record that will be shared outside this protected machine, and separate the shareable campaign record from controlled evidence in that case.
- Treat a click, registration, draft, cleared form, or generic thank-you URL as insufficient submission evidence.

## Close and measure

Run:

```bash
python3 scripts/audit_submission_record.py path/to/v1-batch-record.md
python3 scripts/audit_submission_record.py path/to/v1-batch-record.md --json
# Only for a user-authorized record kept on the protected local machine:
python3 scripts/audit_submission_record.py path/to/v1-batch-record.md --record-scope local-controlled
```

Report totals by queue state, verification state, shard, and outcome. Report official-contact emails sent, email send outcomes unknown, and replies/link placements separately from directory submissions and published listings. Do not report an email send as delivery, reply, listing, link placement, publication, or proof of SEO value.

## Bundled resources

- [references/workflow.md](references/workflow.md): sharding, verification queues, execution, and recovery.
- [references/status-model.md](references/status-model.md): record schema and state invariants.
- [references/computer-use-bitbrowser.md](references/computer-use-bitbrowser.md): BitBrowser control rules.
- [assets/submission-record-template.md](assets/submission-record-template.md): privacy-safe V1 Batch template.
- `scripts/audit_submission_record.py`: batch integrity, secret, duplicate, and state auditor.
