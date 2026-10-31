# Security policy

Report vulnerabilities through [GitHub's private vulnerability reporting](https://github.com/fiam/home-assistant-guest-access/security/advisories/new).
Do not include active guest links, passwords, cookies, Home Assistant tokens,
or private configuration in a public issue.

Include the affected version, reproduction steps using synthetic devices, and
the expected impact. The latest release receives fixes; no response-time SLA is
promised.

See [the security design](docs/security.md) for authentication, data storage,
revocation, and limitations. A full Home Assistant configuration backup contains
both access data and its password-recovery key and must be protected accordingly.
