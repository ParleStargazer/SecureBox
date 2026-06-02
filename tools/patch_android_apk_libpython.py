"""Patch libpython ELF files inside an Android APK.

The output APK is unsigned. Run zipalign and apksigner after this script.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from patch_android_libpython_elf import patch_elf

SIGNATURE_SUFFIXES = (".RSA", ".DSA", ".EC", ".SF", ".MF")


def _copy_info(info: ZipInfo) -> ZipInfo:
    copied = ZipInfo(info.filename, info.date_time)
    copied.comment = info.comment
    copied.compress_type = info.compress_type
    copied.create_system = info.create_system
    copied.external_attr = info.external_attr
    copied.extra = info.extra
    return copied


def _is_old_signature_entry(name: str) -> bool:
    upper = name.upper()
    return upper.startswith("META-INF/") and upper.endswith(SIGNATURE_SUFFIXES)


def patch_apk(input_apk: Path, output_apk: Path) -> list[str]:
    patched: list[str] = []
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        with ZipFile(input_apk, "r") as zin, ZipFile(output_apk, "w") as zout:
            for info in zin.infolist():
                if _is_old_signature_entry(info.filename):
                    continue

                data = zin.read(info.filename)
                if info.filename.startswith("lib/") and info.filename.endswith(
                    "/libpython3.12.so"
                ):
                    lib_path = tmp_dir / info.filename.replace("/", "_")
                    lib_path.write_bytes(data)
                    changes = patch_elf(lib_path, backup=False)
                    data = lib_path.read_bytes()
                    if changes:
                        patched.append(info.filename)

                zout.writestr(_copy_info(info), data)
    return patched


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_apk", type=Path)
    parser.add_argument("output_apk", type=Path)
    args = parser.parse_args()

    patched = patch_apk(args.input_apk, args.output_apk)
    if not patched:
        print("no libpython files required patching", file=sys.stderr)
    else:
        print("patched APK entries:")
        for name in patched:
            print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
