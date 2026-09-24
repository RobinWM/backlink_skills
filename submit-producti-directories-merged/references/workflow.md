# 外链自动提交合并版 — SPD V1 Batch workflow

## 1. Preflight the campaign

Create one verified product profile with approved short, medium, and long descriptions; pricing; categories; contact aliases; policy URLs; social handles; and asset references. Separate public facts from credentials and controlled evidence.

Record:

- campaign ID and `SPD version: V1 Batch`;
- product canonical ID and canonical URL;
- source-list reference and authorization reference;
- execution-shard size and maximum active tabs;
- permitted actions, scope, approver alias, approval time, and expiry;
- prohibited actions, including payment, reciprocal-site modification, and DNS changes unless separately approved.

## 2. Normalize and deduplicate

For every source URL:

1. lowercase the hostname;
2. remove fragments and tracking parameters;
3. preserve route parameters required to reach the form only in controlled evidence;
4. derive `platform domain | product canonical ID | account alias | route`;
5. merge exact and tracking-only duplicates;
6. search existing records and public listings before scheduling a final action.

Assign a stable queue ID. Never renumber existing entries after execution begins.

## 3. Run fast triage

Inspect enough page state to classify the route without entering product fields.

Pass only legitimate, relevant product-directory routes with a usable submission or claim path. Remove or isolate unavailable, paid-link-only, forced-reciprocal, unrelated, unreleased-only, and terms-prohibited routes.

Classify passing routes by operational lane:

- direct form;
- account required;
- official-contact email;
- registration email required;
- manual verification likely;
- verification unavailable before form;
- unknown interactive route.

## 4. Create execution shards

Split the passing queue by route and browser capacity. Configure shard size explicitly; a practical default may be chosen for local resources, but it is not a search-engine safety threshold.

Within each shard:

1. order account and email-verification work first;
2. order short-lived verification tokens immediately before their forms;
3. cap active tabs at the recorded limit;
4. keep one queue cursor and one immutable attempt log;
5. isolate browser profiles when account identity or session ownership differs.

## 5. Run verification preflight

Visit every site in the shard before form entry. Expose the earliest verification or login boundary. Attempt only ordinary native automatic verification. Preserve interactive challenges in their original tabs and add them to the manual queue.

Record one state:

- `automatic verification passed`;
- `awaiting manual verification`;
- `manual verification completed`;
- `verification unavailable before form`;
- `verification expired/reset`;
- `no verification presented`;
- `deferred by user`.

Do not bypass challenges or move issued challenges between browser profiles.

## 6. Resolve one manual queue

Present site, queue ID, browser tab, challenge type, exact blocker, and required user action. After user completion, immediately re-inspect each tab and record whether the challenge completed, expired, reset, or remained blocked.

Do not keep solved short-lived tokens waiting behind unrelated work.

## 7. Execute form lanes

Process eligible items sequentially within a profile:

1. confirm authorization and idempotency;
2. confirm verification validity;
3. fill approved facts and the nearest truthful category;
4. leave unknown optional fields blank;
5. keep optional subscriptions off;
6. verify free/paid plan and reciprocal requirements;
7. submit only when the final action is allowed;
8. capture exact server text and controlled evidence reference;
9. advance the queue cursor only after the record is saved.

Never retry an ambiguous final action. For a form, mark `submission outcome unknown`, then inspect the account backend, mailbox, and public search before any future attempt. For an official Contact email, use the email-specific unknown state in §7.1 instead.

## 7.1 Execute an official Contact-email lane

Use this lane only when the current batch explicitly authorizes one-to-one official Contact email outreach and names the signed-in Gmail sender alias.

1. Obtain the recipient only from the target site's own Contact, submit, resource-recommendation, tool-listing, or partnership page; record the public source as controlled evidence and keep the actual address out of a shareable record.
2. Search the campaign record and Gmail Sent, Drafts, and All Mail using the product brand, canonical URL, target domain, and contact route. A prior draft, sent message, or conversation is `duplicate — no action`; never start another message.
3. Verify the Gmail `From` alias, the one recipient, blank CC/BCC, and a concise truthful request tailored to the target. Do not request dofollow, reciprocal links, ranking guarantees, a short post, a long article, or guest-content publication.
4. Click `Send` once. Record the native Gmail receipt or matching Sent copy as controlled evidence. `email sent — awaiting reply` proves only Gmail sent the message; it does not prove delivery, a reply, a listing, a link, or publication.
5. If the send result is unclear, make two or three read-only checks of compose/thread, Sent/All Mail, and Drafts/Outbox. Preserve the Gmail page and record `email send outcome unknown`; never send again, follow up, or reply automatically.

## 8. Recover without replay

- Re-inspect after navigation, modal changes, user interaction, or page reloads.
- Reacquire accessibility elements instead of using stale identifiers.
- Retry transient loading once in the current tab and once in a fresh tab.
- Resume from the first queue item without a terminal or pending state.
- Never reopen completed idempotency keys for final action.
- Preserve exact error text and distinguish site failure from local browser failure.

## 9. Close the batch

Audit the record, reconcile ambiguous entries, and report:

- total source URLs, normalized routes, duplicates removed, and routes rejected;
- eligible queue size and completed shards;
- submitted, awaiting approval, awaiting email verification, published, unknown outcome, blocked, unavailable, paid-only, and ineligible;
- official Contact emails sent, email send outcomes unknown, and any independently verified link placements, reported separately;
- manual-verification queue size and completion rate;
- operator time, verified submissions per hour, recovery rate, and outstanding queue.

Do not equate `submitted` with `published` or use volume as evidence of SEO value.
