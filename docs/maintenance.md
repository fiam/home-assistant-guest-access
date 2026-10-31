# Updates, backups, and removal

## Updates

HACS and Marketplace offer updates from GitHub releases. Install the update,
restart if prompted, and reload your browser afterward.

For a manual installation, download the release ZIP and verify its SHA-256.
Replace only `custom_components/guest_access` in your Home Assistant configuration
directory, then restart Home Assistant. Your saved links live outside that
folder and stay in place.

## Backups

Native Home Assistant backups include the integration and its access settings.
Keep backups private: they include both guest records and the password-recovery
key. If you copy configuration yourself, include both `.storage/guest_access`
and `.storage/guest_access_key`.

Restoring a backup restores its saved links and sign-ins too. Review the links
and their dates after a restore, especially if you revoked access since the
backup was made.

## Removal

First remove Guest Access from **Settings → Devices & services**. This deletes
its saved links, password-recovery key, and remembered sign-ins. Then uninstall
its files through HACS or Marketplace and restart when prompted.

For a manual installation, remove `custom_components/guest_access` after removing
the integration, then restart Home Assistant.
