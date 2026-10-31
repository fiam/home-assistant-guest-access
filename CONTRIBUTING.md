# Contributing

Use fictional devices and guests in tests, screenshots, and bug reports. Never
commit Home Assistant configuration, `.storage`, tokens, real guest URLs, or
passwords. The repository contains no runtime configuration.

## Checks

The tests run against Home Assistant's real HTTP/authentication middleware,
config-entry lifecycle, and service registry with synthetic handlers. They do
not connect to a real installation or actuate devices.

```sh
docker build -t guest-access-test:2026.10.4 -f tests/Dockerfile .
docker run --rm --network none -v "$PWD:/work:ro" \
  guest-access-test:2026.10.4 -q
node --test tests/test_frontend.mjs
uvx ruff@0.17.3 check .
uvx ruff@0.17.3 format --check .
```

Use Node.js 24 and Python 3.14.2 or newer. To test another Home Assistant version,
pass `--build-arg HA_VERSION=<version>` to Docker. The Docker container is only
a test dependency, not part of the installed integration.

## UI preview and screenshots

```sh
sh tests/preview.sh
```

Open `http://127.0.0.1:39282/preview-admin` or `/preview-guest`.
Use the demo password `synthetic-preview-password`. The preview exposes a
**test-only administrator shortcut** on loopback, uses disposable configuration,
and registers no-op services for fictional devices. Never expose the preview
publicly or install its code in a real Home Assistant instance.

Capture only the page content, not browser chrome, account names, or unrelated
windows. Store reviewed screenshots in `docs/screenshots/`. Stop the demo with
`docker stop guest-access-preview`.

## Release

1. Update the version in the manifest, `pyproject.toml`, and frontend asset URLs.
2. Update the changelog; run tests, Ruff, hassfest, and HACS validation.
3. Run `python3 scripts/package.py`. Inspect the archive: it must contain only
   `custom_components/guest_access`, with no configuration, tests, or secrets.
4. Scan the source/history and archive for private data. Use a public/no-reply
   Git author email. All screenshots must use the synthetic preview.
5. Tag the commit `v<version>` and create a GitHub release. Attach the versioned
   ZIP and `.zip.sha256`; a tag alone is not a GitHub release.

HACS and Marketplace install from the tagged repository tree. The attached ZIP
is for manual installation; `hacs.json` does not enable `zip_release`.
This repository is distributed as a custom repository until separately accepted
into the shared catalog.
