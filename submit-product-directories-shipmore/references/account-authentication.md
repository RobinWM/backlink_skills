# Directory account authentication

## Authorization scope

Brennan has authorized this worker to use the configured default directory account for ordinary free login and account creation needed to submit legitimate Product listings. This standing authorization covers:

- logging in with the configured email/password;
- creating a free account when the site clearly reports that no account exists;
- retrieving the site's login/registration verification email from the authorized Gmail mailbox with `gws`;
- entering a one-time email code or opening the site's ordinary verification link in the same browser session;
- continuing the original directory submission after authentication succeeds.

It does not authorize payment, paid trials, phone verification, identity/KYC checks, social/OAuth account linking, optional newsletters/promotions, unrelated public posts, multiple-account creation, or bypassing CAPTCHA/Turnstile/access controls.

## Runtime credentials

Credentials are runtime secrets, not repository content. Load them from:

```text
/root/.config/backlink-skills/directory-account.env
```

Expected variables:

```text
DIRECTORY_ACCOUNT_EMAIL
DIRECTORY_ACCOUNT_PASSWORD
```

Load without printing:

```bash
set -a
source /root/.config/backlink-skills/directory-account.env
set +a
```

Never run `env`, `set`, `printenv`, shell tracing (`set -x`), or commands that echo these values. Pass shell variable references to the browser command rather than embedding literal credentials in commands, notes, screenshots, Shipmore payloads, or evidence. Do not commit the runtime file.

## Login and registration decision tree

1. Reuse a clearly authorized existing authenticated session when available.
2. If the site requests login, load the runtime credentials and attempt one normal login.
3. If login succeeds, heartbeat and continue the original submission in the same session.
4. If the site explicitly says the account does not exist, user is not registered, or equivalent, switch to the ordinary free registration flow.
5. Do not infer non-registration merely from a generic `invalid credentials` message. Check for an explicit registration signal or use the site's normal password-reset/account-existence surface only when it is non-destructive and does not send unrelated messages.
6. During registration, use the configured email/password. Fill any required name/company fields only from verified Shipmore Product identity fields. Keep optional unknown fields blank; do not invent a person, company, phone number, address, or username.
7. Accept only agreements strictly required to create the ordinary free account and use the directory submission feature. Leave newsletters, promotions, partner offers, trials, and unrelated consent unchecked.
8. After successful registration, remain in the same session and continue the original submission.
9. Do not create a second account if registration says the email already exists. Return to login once; if that still fails, classify the exact blocker truthfully instead of looping.
10. Limit the combined login/registration cycle to one login attempt, one registration attempt, and one post-registration login attempt unless the page itself performs a normal redirect/retry without duplicating actions.

## Gmail verification with gws

Use only `gws` against the already-authorized Gmail account. Reading a matching verification email is authorized; sending/replying/deleting/archiving email is not needed.

1. Record the UTC time immediately before triggering the verification email. Heartbeat first if a Shipmore lease is active.
2. Trigger the site's ordinary email verification once. Do not repeatedly request codes unless the site explicitly reports that the first code expired or was not sent.
3. Search for recent candidate messages, narrowing by the directory's visible brand/domain and common verification terms. Example shape:

   ```bash
   gws gmail users messages list --params '{"userId":"me","q":"newer_than:1d (verification OR verify OR code OR OTP)","maxResults":20}'
   ```

4. Read only candidate messages with:

   ```bash
   gws gmail +read --id <message-id> --headers --format json
   ```

5. Select the newest message received after the trigger time whose sender/subject/body clearly matches the active directory. Never consume a code or magic link from an unrelated service.
6. Extract only the required one-time code or verification URL. Do not print it, persist it, include it in evidence, or copy the rest of the mailbox content into logs.
7. Enter the code or open the verification URL in the same authorized browser session, then re-read the page to confirm verification succeeded.
8. Poll every 10 seconds for at most 2 minutes, heartbeating as needed. If no matching mail arrives, preserve `awaiting_email_verification` or use the closest truthful blocker/follow-up state rather than registering again.
9. Treat OTPs and magic links as ephemeral secrets. Never save them to Shipmore, repository files, screenshots, durable notes, or command history.

## Stop and classify

Stop automatic authentication and classify truthfully when:

- CAPTCHA, Turnstile, phone verification, KYC, security-key/passkey approval, or manual approval is required;
- the only registration route requires payment or a paid trial;
- required registration identity data is unavailable from verified Product fields;
- the mailbox message cannot be confidently matched to the active directory;
- credentials are rejected without an explicit safe registration path;
- the site forbids or technically blocks the available automation surface;
- the lease is lost or expires.

`blocked_account_or_email_policy` remains valid for authentication steps outside the authorization above. Do not emit `account_strategy_required` merely because ordinary email/password login or free registration is required; execute this authorized flow first.
