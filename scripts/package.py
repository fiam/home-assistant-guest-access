"""Create a deterministic source-only installation archive."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

root = Path(__file__).resolve().parents[1]
component = root / "custom_components/guest_access"
version = json.loads((component / "manifest.json").read_text())["version"]
output = root / "dist"
output.mkdir(exist_ok=True)
archive = output / f"guest-access-{version}.zip"
with ZipFile(archive, "w", ZIP_DEFLATED) as target:
    for source in sorted(component.rglob("*")):
        if source.is_symlink():
            raise ValueError("Symlinks must not be included in the package")
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        info = ZipInfo(str(source.relative_to(root)), (2026, 1, 1, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        target.writestr(info, source.read_bytes())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n")
print(f"Created {archive.name}")
print(f"SHA-256: {digest}")
