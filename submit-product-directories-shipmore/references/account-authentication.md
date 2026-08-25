# Directory account authentication

## Account identity source

Use `productContactEmail` from the Shipmore claim payload as the directory-account email. It is the effective submission identity resolved by Shipmore:

1. `productSubmissionOverride.contactEmail` for this Product, when present;
2. otherwise the Product owner's `userSubmissionProfile.contactEmail`.

Do not derive, guess, or replace this email from Product prose, the site domain, a founder profile, or a browser account. Do not copy it into evidence, exact results, screenshots, or logs. A site account visibly signed in under a different email is not interchangeable; use it only if Shipmore later returns that email as the effective identity.

## Authorization scope

Brennan has authorized this worker to use the effective directory-account email above to authenticate and create an ordinary free account when needed for a legitimate Product listing. The permitted authentication order is:

1. Google OAuth through an already-authorized existing browser session;
2. GitHub OAuth through an already-authorized existing browser session;
3. the directory's native email code or magic-link flow, retrieving only the matching message through authorized `gws` for a Google-hosted mailbox, or an existing matching Gmail web session only when `gws` is unavailable;
4. ordinary email/password login.

The worker may continue the original submission after successful authentication. It may create one ordinary free account only after the site explicitly reports that the effective email has no account.

It does not authorize payment, paid trials, phone verification, identity/KYC checks, passkeys/security keys, linking a different Google/GitHub identity, optional newsletters/promotions, unrelated public posts, multiple-account creation, or bypassing CAPTCHA/Turnstile/access controls.

## Runtime credentials

The claim payload supplies the email; it is not read from a local secret file. The optional password is a runtime secret, never repository content, and may be loaded from:

```text
/root/.config/backlink-skills/directory-account.env
```

Expected optional variable:

```text
DIRECTORY_ACCOUNT_PASSWORD
```

Load it only when the fourth authentication method is necessary, without printing it. Never run `env`, `set`, `printenv`, shell tracing (`set -x`), or commands that echo it. Do not put the effective email or password in command arguments, notes, screenshots, Shipmore payloads, or evidence. Do not commit the runtime file.

## Login and registration decision tree

1. Reuse a clearly authorized existing directory session when available.
2. If the directory offers Google sign-in, use it only when an existing browser Google session visibly corresponds to the effective email. Do not enter Google credentials, choose a different account, grant extra permissions, or create/link a new Google identity. On success, heartbeat and continue the original submission.
3. Otherwise, if it offers GitHub sign-in, use it only when an existing browser GitHub session visibly corresponds to the effective email. Do not enter GitHub credentials, choose a different account, authorize scopes beyond ordinary sign-in, or create/link a new GitHub identity. On success, heartbeat and continue.
4. Otherwise, if the directory offers an ordinary email code or magic link, enter the effective email, trigger one verification message, then use the bounded Gmail retrieval workflow below. For a Google-hosted mailbox, prefer `gws`; only if it is unavailable in the current environment, use an existing matching Gmail web session. On success, continue in the same browser session.
5. Otherwise, if the directory supports email/password and `DIRECTORY_ACCOUNT_PASSWORD` is available, attempt one normal login with the effective email and runtime password. On success, heartbeat and continue.
6. If the site explicitly says this email has no account, register one ordinary free account using the effective email and the available method. Fill required name/company fields only from verified Shipmore Product identity fields. Keep optional unknown fields blank; do not invent a person, company, phone number, address, or username.
7. Accept only agreements strictly required to create the ordinary free account and use the directory submission feature. Leave newsletters, promotions, partner offers, trials, and unrelated consent unchecked.
8. Do not infer non-registration from a generic login failure. Do not retry a failed provider, email send, password attempt, or registration cycle unless the site explicitly reports that the preceding attempt expired or did not complete.
9. Do not create a second account if registration says the email already exists. Return to a supported sign-in method once; if that fails, classify the exact blocker truthfully.
10. Limit the whole cycle to one attempt per offered provider, one email-verification send, one password login, one registration, and one post-registration authentication attempt unless the site performs its own normal redirect/retry without duplicating actions.

## Gmail verification (`gws` first, Gmail web fallback)

For a Google-hosted effective email, use only `gws` against the already-authorized Gmail account when `gws` is available. If `gws` is unavailable in the current environment, the permitted fallback is an already-signed-in Gmail browser session at `https://mail.google.com` that visibly corresponds to `productContactEmail`. Reading a matching verification email is authorized; sending, replying, deleting, archiving, changing mailbox settings, or using a different account is not needed.

1. Determine whether `gws` is available. If it is, confirm that its authorized mailbox corresponds to `productContactEmail`; otherwise do not request a code/link. If `gws` is unavailable, open `https://mail.google.com` and confirm that an existing signed-in Gmail session visibly corresponds to `productContactEmail`. Do not enter Google credentials, select a different account, grant permissions, or create/link an account. If neither permitted mailbox surface can be confirmed, stop before requesting a code/link. Record the UTC time immediately before triggering the verification email. Heartbeat first if a Shipmore lease is active.
2. Trigger the site's ordinary email verification once. Do not repeatedly request codes unless the site explicitly reports that the first code expired or was not sent.
3. If using `gws`, search for recent candidate messages, narrowing by the directory's visible brand/domain and common verification terms. Example shape:

   ```bash
   gws gmail users messages list --params '{"userId":"me","q":"newer_than:1d (verification OR verify OR code OR OTP)","maxResults":20}'
   ```

4. Read only candidate messages with:

   ```bash
   gws gmail +read --id <message-id> --headers --format json
   ```

5. If using the Gmail web fallback, search the existing matching mailbox for recent candidate messages by the directory's visible brand/domain and common verification terms, then read only candidates needed to identify the newest matching message. Do not search or read unrelated mail.
6. Select the newest message received after the trigger time whose sender, subject, and body clearly match the active directory. Never consume a code or magic link from an unrelated service.
7. Extract only the required one-time code or verification URL. Do not print it, persist it, include it in evidence, or copy the rest of the mailbox content into logs.
8. Enter the code or open the verification URL in the same authorized directory browser session, then re-read the page to confirm verification succeeded. Do not use the message to authenticate a different email identity.
9. Poll every 10 seconds for at most 2 minutes, heartbeating as needed. If no matching mail arrives, preserve `awaiting_email_verification` or use the closest truthful blocker/follow-up state rather than registering again.
10. Treat OTPs and magic links as ephemeral secrets. Never save them to Shipmore, repository files, screenshots, durable notes, or command history.

## Stop and classify

Stop automatic authentication and classify truthfully when:

- CAPTCHA, Turnstile, phone verification, KYC, security-key/passkey approval, or manual approval is required;
- the only registration route requires payment or a paid trial;
- the offered Google/GitHub session is absent, uses a different identity, or asks for credentials/account linking beyond ordinary sign-in;
- required registration identity data is unavailable from verified Product fields;
- the mailbox message cannot be confidently matched to the active directory;
- credentials are rejected without an explicit safe registration path;
- the site forbids or technically blocks the available automation surface;
- the lease is lost or expires.

`blocked_account_or_email_policy` remains valid for authentication steps outside the authorization above. Do not emit `account_strategy_required` merely because ordinary email/password login or free registration is required; execute this authorized flow first.
