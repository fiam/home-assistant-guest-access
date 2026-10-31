#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker run --rm --name guest-access-preview \
  -p 127.0.0.1:39282:18123 \
  -v "$PWD:/work:ro" -e PYTHONPATH=/work --entrypoint python \
  guest-access-test:2026.10.4 tests/preview.py
