# Browser control routing for the Shipmore worker

Select a control surface from runtime capabilities instead of hard-coding a browser, operating system, executable path, extension, automation library, keyboard shortcut, or display geometry.

Shipmore owns durable submission state. Browser/backend diagnostics are runtime details unless they are captured through an opaque evidence reference or another explicitly supported Shipmore field. Do not recreate the old Markdown campaign record solely to persist browser state.

## Capability preflight

Before mutable browser work, determine:

- normalized host platform: `windows`, `macos`, `linux`, or `other`;
- UI environment: desktop, remote desktop, headless, or unknown;
- user-requested browser/app constraint, if any;
- whether an authorized authenticated browser/app binding already exists;
- available connector, API, CLI, browser-runtime, connected-extension, and desktop-control capabilities;
- whether each candidate backend actually supports the current platform and required interaction scope.

Select by demonstrated capability. Never infer platform support from a backend name.

## Routing order

1. Honor a browser/app explicitly named by the user. Do not silently switch surfaces.
2. If a purpose-built connector/API/CLI can perform the semantic operation and visible browser interaction was not explicitly required, prefer that supported capability.
3. Otherwise prefer an installed browser runtime or connected browser extension that can preserve the intended authenticated session.
4. Use desktop UI control only when a more specific supported browser runtime cannot address the requested surface and the adapter explicitly supports the current platform.
5. If no safe compatible backend exists, preserve the Shipmore task state and hand off rather than substituting an uncontrolled browser/session.

The active runtime/Skill documentation is authoritative for tool-specific selectors, confirmation rules, keyboard behavior, screenshot handling, and supported platforms.

## Session rules

- Reuse an authorized existing session before creating a duplicate account.
- Keep login, verification, form work, and final result inspection on the same surface/session when the site requires continuity.
- Treat browser and tab bindings as separate. Recover a stale tab from the existing browser binding when possible rather than recreating the whole runtime.
- Never inspect cookies, local storage, saved passwords, profile stores, recovery codes, raw session IDs, magic links, or hidden authentication material.
- Do not copy opaque browser/profile identifiers between machines as if they were portable.

## Structured interaction first

When the active browser runtime supports it:

1. read fresh page/DOM/accessibility state;
2. prefer semantic/structured controls;
3. reacquire controls after navigation, reload, modal changes, user intervention, or unexpected results;
4. use keyboard or coordinate fallback only when the runtime documentation permits it and structured control is insufficient.

Never reuse stale DOM handles, accessibility indices, menu items, or coordinates after state changes.

## Desktop-control fallback

Use desktop UI control only when necessary and explicitly supported.

Before each fallback action:

- verify the focused app/window;
- verify the intended profile/workspace/session through non-secret visible identity;
- read fresh UI state;
- recheck layout/display scaling/zoom before coordinate interaction.

Do not assume macOS, Windows, or Linux shortcuts are interchangeable.

Do not introduce AppleScript, PowerShell UI automation, xdotool, standalone automation servers, or other UI technologies unless the user explicitly requests them and the active runtime policy permits them.

## Authentication and verification

- Never bypass, outsource, weaken, or evade CAPTCHA, Turnstile, email verification, browser security warnings, or access controls.
- For this Shipmore worker, ordinary email/password login, one explicitly-needed free registration, and matching Gmail verification are authorized as defined in `account-authentication.md`. Load credentials only from the runtime secret file, never from repository content.
- Expose and complete the site's ordinary native email verification flow through authorized `gws`; this is not a bypass. Keep the code/link ephemeral and use the same browser session.
- After successful authentication, continue the original directory task. Do not stop solely because an account was required.
- If manual user action is required, heartbeat before handoff when the lease is valid and preserve the current Shipmore state truthfully.
- After user intervention, re-read the page and recheck challenge validity before continuing.
- If the lease expires during handoff, do not continue acting as owner. Reclaim/recover according to the Queue protocol and inspect site state before retrying any action.

## Lease-aware browser work

Browser execution is subordinate to the Shipmore lease.

Before a mutable step:

1. ensure the current Run Item is still owned by this worker;
2. heartbeat when the remaining lease margin is not comfortably larger than the next action;
3. stop immediately on lease-conflict/expiry response.

A browser page remaining open does not grant execution ownership after the lease expires.

## Final-action safety

Never infer submission success from any one of these alone:

- clicking Submit;
- a disabled button;
- form fields clearing;
- navigation;
- a generic thank-you URL;
- a transport timeout/error.

After the final action, read the resulting page/state fresh and classify only what can be supported.

If the final action may have reached the server but the outcome cannot be determined:

1. do not press Submit again;
2. check available authorized account/backend history;
3. check an authorized mailbox when available;
4. check the public listing/page when appropriate;
5. if unresolved, complete the Shipmore item as `submission_outcome_unknown` with follow-up rather than retrying blindly.

## Product data rules

Use the Product data returned by the Shipmore claim payload as the primary verified input.

You may summarize or adapt `productDescription` / `productMarkdown` to an honest field-length/category requirement, but do not invent:

- founder/company identity;
- address/location;
- launch date;
- pricing or plan claims;
- contact details;
- ownership/legal facts;
- product capabilities not supported by the returned data or a separately verified source.

Keep optional unknowns blank. Required unknowns should become `blocked_missing_verified_data`.

## Agreements, payments, reciprocal links, and promotions

Do not automatically:

- pay a listing fee;
- buy a link or ranking package;
- add a reciprocal backlink by directly editing the Product site (the
  lease-bound Shipmore outbound-link flow below is the only exception);
- change DNS/site content;
- accept optional newsletters/promotions;
- publish unrelated articles/posts;
- request dofollow treatment or exact-match commercial anchor text.

These are separate actions requiring their own authorization when they are legitimate at all.

The Shipmore mandatory-backlink flow is the narrow authorized exception: the worker calls `POST /api/outbound-links` and verifies the Product homepage, but never edits Product code/content directly. A verified link may be present in returned SSR HTML or the final homepage DOM. Apply exact parsed hostname/path matching and the lease/timeout rules in `worker-loop.md`; do not bypass CAPTCHA/WAF.

## Evidence and diagnostics

Persist only information supported by the Shipmore API contract:

- exact result text;
- opaque evidence reference;
- public listing URL;
- backend/mailbox/public-page checked timestamps;
- follow-up time/note;
- canonical submission and verification status.

Runtime-local diagnostics may temporarily include a non-secret browser/backend alias when useful for recovery, but do not create a second durable queue/state record just to store it.

Never persist passwords, tokens, OTPs, cookies, raw email addresses, phone numbers, authentication URLs, local application paths, process arguments, or session secrets in Shipmore evidence/result fields. The configured account email may be used as browser form input but must not be copied into evidence or exact-result text.
