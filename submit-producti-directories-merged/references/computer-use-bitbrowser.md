# BitBrowser through Computer Use

Use Computer Use as the sole automation backend for persistent BitBrowser directory campaigns. Preserve the user's existing BitBrowser profile, cookies, tabs, saved sessions, and visible collaboration state.

## Required setup

1. Read the installed `computer-use` Skill completely before any UI action.
2. Target the exact BitBrowser application path when multiple Chromium-family apps or BitBrowser runtimes exist.
3. Call `get_app_state` before the first action and after every navigation, modal, menu expansion, reload, user intervention, or site error.
4. Record the BitBrowser workspace/profile name, visible window title, runtime version, and active URL.

## Interaction rules

- Use `node_repl` with `@oai/sky`; do not use BrowserAct, AppleScript, System Events, or synthetic shell input unless the user explicitly requests another mechanism.
- Prefer fresh accessibility element indices. Never reuse an index after state changes.
- Use direct accessible controls first, deterministic keyboard navigation second, and screenshot coordinates only as a local fallback.
- Keep account creation, email confirmation, CAPTCHA, and submission work in the same BitBrowser profile and original tab whenever possible.
- Preserve every verification tab during the batch-wide verification sweep and manual checkpoint.
- Re-inspect CAPTCHA state before form entry because verification may expire or reset.

## Authentication and verification

- Reuse the authorized logged-in BitBrowser profile before creating a duplicate account.
- Try only the site's ordinary native verification after applicable action-time authorization.
- Never add an external CAPTCHA solver, proxy, fingerprint rotation, stealth mode, or anti-detection escalation.
- For interactive challenges, preserve the tab and add it to the batch manual-verification queue.
- Pause for ambiguous account selection, security keys, recovery prompts, or unexpected permission grants.

## Recovery

- If a UI action fails, refresh state once and reacquire the control.
- If an accessibility action still fails, use a verified keyboard or coordinate fallback without changing browser profiles.
- If the site returns a server error, preserve exact text, avoid duplicate submission, and check the registered inbox for a receipt.
- Never infer submission success from a click, disabled button, navigation, cleared form, or HTTP error alone.
