# Authentication and access control

- The URL has a random 256-bit link identifier in its fragment (`#…`). Browsers
  do not send that fragment in ordinary page requests or HTTP referrers. The
  identifier is sent to the login endpoint in the JSON body.
- The link alone is insufficient. Passwords are stored as salted scrypt hashes
  (`N=32768, r=8, p=1`) and verified off HA's event loop. An encrypted Fernet copy
  supports **Show password** through the administrator-only API. A separate
  private HA Store holds the encryption key; native backups must include both
  stores. Full access to the HA configuration and key permits decryption.
  Passwords are never stored as plaintext and do not appear in
  links, audit events or integration logs. Administrator password submission
  uses authenticated HTTP rather than a WebSocket command with debug logging.
  Ordinary list/guest responses exclude passwords and ciphertext. Explicit
  reveals are audited and sent with `Cache-Control: no-store`; the UI hides the
  revealed password after one minute.
- **Remember this browser** is on by default. After login, a host-only,
  `HttpOnly`, `SameSite=Strict` cookie holds a random sign-in token. On HTTPS the
  cookie also uses `Secure` and the `__Secure-` prefix. It is scoped to the guest
  API and separately named for each link. The browser never stores the password
  in local storage or cookies, and JavaScript cannot read the cookie.
- HA persists only token hashes. Remembered sign-ins survive HA/browser restarts
  and have a rolling one-year lifetime, renewed while used. Closing a private
  browsing session, clearing cookies, or prolonged browser inactivity can still
  require signing in again. Unchecking Remember uses a browser-session cookie
  with a server-side 12-hour limit, which does not survive HA restarts.
- Sign out, a password change, or deleting the link revokes the saved sign-in.
  Pausing and the current access window always block actions, including with a
  remembered cookie. Resuming or extending an access window does not require
  re-entering the password on a remembered browser. Session tokens cannot
  authenticate to HA itself. No automatic action retries are made.
- Every request checks the current global enable switch, link status, start,
  expiry and password revision. Every action resolves its target from current
  server-side permissions. A guest session cannot authenticate to HA itself.
- Login attempts are limited per client address (10/min), per link (5/min) and
  globally (60/min). Only two password checks can run concurrently. HA must have
  correctly configured trusted proxies for accurate client-address limits.
- One action can be in flight per link, with a three-second cooldown and
  ten-minute request-ID replay suppression. There are no automatic command
  retries. “Request sent” means HA accepted the request, not that a door was
  physically observed opening.
- At most 100 links, 32 actions per link, 256 sign-ins and 100 audit records
  are retained. Login counters and non-remembered sessions are memory-only. A persistence
  failure pauses access in the running process and reports a failure.

Use the existing **HTTPS** HA URL externally. Anyone holding both the link and
password has the same access; this is shared-secret guest access, not identity
verification or phishing-resistant MFA. An already-authorized browser holds a
session credential. Keep all same-origin HA custom frontend code trustworthy.
If a backup is restored, it restores the saved link policy too; review links
after restoring. This integration has automated tests and local UI verification,
not an independent security audit or a physical-door test.
