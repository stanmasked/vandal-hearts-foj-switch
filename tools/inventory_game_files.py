#!/usr/bin/env python3
"""Read-only, local inventory of *already accessible* game resource files.

No decryption, extraction, upload, or proprietary bytes in the JSON output.
By default only aggregate extension/signature counts are written; individual
relative paths are optional (--include-paths). No symlink traversal.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path

MAX_FILES = 50000
MAX_SAMPLES = 100
SENSITIVE_EXTENSIONS = {".rap", ".rif", ".edat", ".key", ".act"}
SENSITIVE_NAMES = {"act.dat", "idps", "eid_root_key"}


def detect_magic(header: bytes) -> str:
    if header.startswith(b"\x7fPKG"):
        return "PS3_PKG"
    if header.startswith(b"SCE\x00"):
        return "PS3_SELF_SPRX"
    if header.startswith(b"\x00PSF"):
        return "PS3_PARAM_SFO"
    if header.startswith(b"DDS "):
        return "DDS_TEXTURE"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG_IMAGE"
    if header.startswith(b"OggS"):
        return "OGG_AUDIO"
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "WAV_AUDIO"
    if header.startswith(b"PSMF"):
        return "PSMF_VIDEO"
    if header.startswith(b"VAGp"):
        return "VAG_AUDIO"
    if header.startswith(b"\x7fELF"):
        return "ELF"
    return "unknown"


def inventory(root: Path, *, include_paths: bool = False) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Input root must be an existing directory")
    extension_counts: Counter[str] = Counter()
    signature_counts: Counter[str] = Counter()
    count = 0
    total_size = 0
    skipped_symlinks = 0
    skipped_sensitive = 0
    samples: list[dict] = []

    for current_dir, dirs, files in os.walk(root, followlinks=False):
        ordinary_dirs = []
        for dirname in dirs:
            entry = Path(current_dir) / dirname
            if entry.is_symlink():
                skipped_symlinks += 1
            else:
                ordinary_dirs.append(dirname)
        dirs[:] = sorted(ordinary_dirs)

        for filename in sorted(files):
            path = Path(current_dir) / filename
            if path.is_symlink():
                skipped_symlinks += 1
                continue
            if not path.is_file():
                continue
            if filename.lower() in SENSITIVE_NAMES or path.suffix.lower() in SENSITIVE_EXTENSIONS:
                skipped_sensitive += 1
                continue
            count += 1
            if count > MAX_FILES:
                raise ValueError("Too many files: aborting bounded inventory")
            size = path.stat().st_size
            with path.open("rb") as source:
                magic = detect_magic(source.read(16))
            ext = path.suffix.lower() or "(none)"
            extension_counts[ext] += 1
            signature_counts[magic] += 1
            total_size += size

            if include_paths and len(samples) < MAX_SAMPLES:
                samples.append({
                    "relative_path": path.relative_to(root).as_posix(),
                    "size_bytes": size,
                    "extension": ext,
                    "signature": magic,
                })

    report = {
        "file_count": count,
        "total_bytes": total_size,
        "extension_counts": dict(sorted(extension_counts.items())),
        "signature_counts": dict(sorted(signature_counts.items())),
        "skipped_sensitive": skipped_sensitive,
        "skipped_symlinks": skipped_symlinks,
        "notes": [
            "Signatures are indicative only, not proof of game format compatibility.",
            "Unknown signatures may still contain valid proprietary assets.",
            "No file contents, keys, decrypted binaries or hashes were included.",
            "Inventory must use already lawfully accessible local files.",
        ],
    }
    if include_paths:
        report["sample_files"] = samples
        report["sample_limit"] = MAX_SAMPLES
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Already accessible local asset directory")
    parser.add_argument("--include-paths", action="store_true",
                        help="Include at most 100 relative filenames (off by default)")
    parser.add_argument("--json", action="store_true", help="Print pretty JSON")
    args = parser.parse_args(argv)
    try:
        result = inventory(args.directory, include_paths=args.include_paths)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Inventory error: {exc}\n")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Files: {result['file_count']}  Bytes: {result['total_bytes']}")
        print("Extensions:", result["extension_counts"])
        print("Signatures:", result["signature_counts"])
        print("Skipped:", result["skipped_sensitive"], "sensitive;",
              result["skipped_symlinks"], "symlinks")
        if args.include_paths:
            print("Samples:", result["sample_files"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
