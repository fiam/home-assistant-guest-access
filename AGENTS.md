# Working on Guest Access

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for
every commit: `type(optional-scope): short description`.

Use `feat` for new behavior, `fix` for bug fixes, `docs` for documentation,
`test` for tests, `refactor` for restructuring, `ci` for workflows, and `chore`
for maintenance. Write concise, imperative subjects. Mark breaking changes with
`!` and explain them in a `BREAKING CHANGE:` footer.

## Documentation

Write the README for people installing and using Guest Access. Lead with what
it does, show the controls, and give short installation and usage steps. Use
natural language and concrete examples. Avoid process commentary, internal
implementation jargon, and statements about how screenshots or documentation
were produced. Keep development instructions in CONTRIBUTING.md and detailed
security information in docs/security.md.

Keep HACS and Home Assistant Marketplace installation guidance accurate for the
versions being discussed. Check primary documentation before changing it. Do
not describe this repository as part of the default catalog unless it has been
accepted there.

## Privacy and verification

Never commit real Home Assistant configuration, private URLs, guest names,
entity identifiers, passwords, tokens, or session data. Use fictional fixtures
and the disposable preview for tests and screenshots. Keep browser chrome and
unrelated windows out of screenshots. Use a public or no-reply Git author email.

Follow CONTRIBUTING.md for checks and packaging. Do not test actions against
real devices. Release archives must contain only custom_components/guest_access.
