# Changelog

## 0.5.0 — Unreleased

- Show only shared devices in the link editor, with more space between rows.
- Add and edit devices in a dialog; share all everyday controls or choose a subset.
- Group entities by their Home Assistant device and show room names in search.
- Keep maintenance actions separate, and preserve existing labels and permissions
  when devices are unavailable.

## 0.4.0 — 2026-10-31

- Select devices with their supported controls, or choose individual actions
  for narrower access. Existing links keep their current permissions.
- Group light, blind, switch, and fan controls into guest cards. Add brightness
  and blind-position sliders with Apply and confirmation, in all three languages.
- Detect failed policy writes before reporting success. Drain pending writes
  during cancellation and unload so stale data cannot overwrite newer changes.
- Pause and resume links without restoring stale permissions; reject concurrent
  edits that would overwrite a newer version.
- Keep rejected login attempts from consuming other guests' shared rate limit.
- Recover remembered guests after a pause or schedule extension, preserve
  keyboard focus while polling, and retain unconfirmed-command warnings.
- Support commands on local HTTP origins and reset the page when its link changes.
- Allow new buttons to be shared before their first press.

## 0.3.1 — 2026-10-31

First public release, following local development through 0.3.0.

- Password-protected guest links with editable schedules and individual actions.
- Administrator panel with per-link and global pause controls, custom labels,
  password recovery, and recent activity.
- Mobile guest page with confirmation dialogs, local icons, light/dark themes,
  English, Portuguese, and Spanish translations.
- Remembered browser sessions across Home Assistant restarts, with revocation
  when passwords change or links are deleted.
- HACS/custom repository packaging, Marketplace transition instructions,
  quick-install and setup buttons, and fictional demo screenshots.
- Automated HTTP, access-control, persistence, lifecycle, and frontend tests.
