#!/usr/bin/env python3
"""Read-only inspection of debug PS3 PKG -> PSARC -> file manifest.

Intended for legally obtained local backups. No extracted assets, executable
code, license material, or secret keys are written. Supports non-finalized
PS3 PKG revision 0x0000 in a regular STORED ZIP split into consecutive parts.
Does not support finalized retail PKGs, encrypted ZIPs or spanning ZIP disks.

References:
https://www.psdevwiki.com/ps3/PKG_files
https://www.psdevwiki.com/ps3/PlayStation_archive_%28PSARC%29
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import struct
import sys
import zipfile
import zlib

from tools.inspect_split_pkg import JoinedParts

MAX_ITEMS = 8192
MAX_NAMES = 1_000_000
MAX_TOC = 8_000_000
MAX_FILE_PREVIEW = 2_000_000
MAX_PSARC_ENTRIES = 200_000


class FormatError(ValueError):
    pass


def unpack_stored_zip(stream: JoinedParts, member: str | None = None):
    """Return (PKG position in concatenated ZIP, raw PKG size).

    Refuse compression or encryption to allow safe bounded random reads.
    """
    with zipfile.ZipFile(stream) as zf:
        candidates = [x for x in zf.infolist()
                      if not x.is_dir() and x.filename.lower().endswith(".pkg")]
        if member is not None:
            candidates = [x for x in candidates if x.filename == member]
        if len(candidates) != 1:
            raise FormatError("Exactly one PKG member required (or use --member)")
        entry = candidates[0]
        if entry.compress_type != zipfile.ZIP_STORED or entry.flag_bits & 1:
            raise FormatError("Only unencrypted ZIP_STORED entries are supported")
        if entry.file_size != entry.compress_size:
            raise FormatError("Stored ZIP entry has mismatched lengths")
        stream.seek(entry.header_offset)
        local = stream.read(30)
        if len(local) != 30 or local[:4] != b"PK\x03\x04":
            raise FormatError("Invalid ZIP local file header")
        name_len, extra_len = struct.unpack_from("<HH", local, 26)
        begin = entry.header_offset + 30 + name_len + extra_len
        if begin < 0 or begin + entry.file_size > stream.size:
            raise FormatError("PKG entry outside ZIP bounds")
        return begin, entry.file_size


def xor_debug_data(digest: bytes, absolute_data_offset: int, encrypted: bytes) -> bytes:
    """Random-access SHA1-XOR stream for *non-finalized* PKGs.

    Offset is relative to the beginning of the PKG data region. No external
    encryption keys or proprietary SDK are needed for this debug-style format.
    """
    if len(digest) != 16 or absolute_data_offset < 0:
        raise FormatError("Invalid debug PKG digest or offset")
    seed = bytearray(64)
    seed[0:8] = digest[0:8]
    seed[8:16] = digest[0:8]
    seed[16:24] = digest[8:16]
    seed[24:32] = digest[8:16]
    output = bytearray(len(encrypted))
    index = 0
    while index < len(encrypted):
        pos = absolute_data_offset + index
        seed[56:64] = (pos // 16).to_bytes(8, "big")
        mask = hashlib.sha1(seed).digest()
        start_in_block = pos % 16
        amount = min(16 - start_in_block, len(encrypted) - index)
        for j in range(amount):
            output[index + j] = encrypted[index + j] ^ mask[start_in_block + j]
        index += amount
    return bytes(output)


class DebugPKG:
    def __init__(self, stream: JoinedParts, begin: int, length: int):
        self.stream = stream
        self.begin = begin
        self.length = length
        stream.seek(begin)
        raw = stream.read(0xC0)
        if len(raw) < 0xC0 or raw[:4] != b"\x7fPKG":
            raise FormatError("No classic PKG header")
        revision, pkg_type = struct.unpack_from(">HH", raw, 4)
        if revision != 0 or pkg_type != 1:
            raise FormatError("Only PS3 non-finalized/debug revision PKGs are supported")
        self.item_count = struct.unpack_from(">I", raw, 0x14)[0]
        declared_size = struct.unpack_from(">Q", raw, 0x18)[0]
        self.data_offset = struct.unpack_from(">Q", raw, 0x20)[0]
        self.data_size = struct.unpack_from(">Q", raw, 0x28)[0]
        self.digest = raw[0x60:0x70]
        self.content_id = raw[0x30:0x60].split(b"\x00", 1)[0].decode("ascii", "replace")
        if not (1 <= self.item_count <= MAX_ITEMS):
            raise FormatError("Item count outside safety limit")
        if declared_size != length:
            raise FormatError("PKG length differs from header")
        if self.data_offset > length or self.data_size > length - self.data_offset:
            raise FormatError("PKG data region outside file")

    def read(self, offset: int, size: int) -> bytes:
        if size < 0 or size > MAX_FILE_PREVIEW or offset < 0:
            raise FormatError("Invalid or oversized PKG data request")
        if offset > self.data_size or size > self.data_size - offset:
            raise FormatError("PKG read outside encrypted data region")
        self.stream.seek(self.begin + self.data_offset + offset)
        encrypted = self.stream.read(size)
        if len(encrypted) != size:
            raise FormatError("Truncated PKG data")
        return xor_debug_data(self.digest, offset, encrypted)

    def items(self) -> list[dict]:
        raw = self.read(0, self.item_count * 32)
        entries = []
        for i in range(self.item_count):
            off, nbytes, data_off, size, flags, padding = struct.unpack_from(
                ">IIQQII", raw, i * 32
            )
            if not (0 < nbytes <= 1024 and off >= self.item_count * 32):
                raise FormatError(f"Bad PKG filename range at item {i}")
            if off > self.data_size or nbytes > self.data_size - off:
                raise FormatError(f"PKG filename outside data at item {i}")
            if data_off > self.data_size or size > self.data_size - data_off:
                raise FormatError(f"PKG file outside data at item {i}")
            if padding != 0 or flags & 0xFF not in (1, 3, 4):
                raise FormatError(f"Unexpected PKG item flags/padding at item {i}")
            name_bytes = self.read(off, nbytes)
            try:
                name = name_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise FormatError("Invalid PKG item filename encoding") from exc
            if name.startswith("/") or "\\" in name or ".." in name.split("/"):
                raise FormatError("Unsafe PKG item path")
            entries.append({
                "path": name, "size": size, "offset": data_off,
                "kind": "directory" if flags & 0xFF == 4 else "file",
            })
        return entries


class PSARC:
    def __init__(self, pkg: DebugPKG, start: int, size: int):
        self.pkg = pkg
        self.start = start
        self.size = size
        header = self.read(0, 32)
        (magic, version, comp, toc_len, ent_size, n_entries,
         block_size, flags) = struct.unpack(">4sI4sIIIII", header)
        if magic != b"PSAR" or comp != b"zlib":
            raise FormatError("Expected PSARC/zlib header")
        if (ent_size != 30 or n_entries < 2 or n_entries > MAX_PSARC_ENTRIES
                or block_size < 1024 or block_size > 1_048_576):
            raise FormatError("Unsupported PSARC TOC parameters")
        if flags & 4:
            raise FormatError("Encrypted PSARC TOC unsupported")
        if toc_len > MAX_TOC or toc_len > size or toc_len < 32 + ent_size * n_entries:
            raise FormatError("PSARC TOC extends beyond allowed range")
        self.version = version
        self.compression = comp.decode("ascii")
        self.flags = flags
        self.block_size = block_size
        toc = self.read(32, toc_len - 32)
        table_len = n_entries * ent_size
        if (len(toc) - table_len) % 2:
            raise FormatError("PSARC block-length table misaligned")
        self.blocks = list(struct.unpack(
            ">" + "H" * ((len(toc) - table_len) // 2), toc[table_len:]
        ))
        self.entries = []
        for i in range(n_entries):
            e = toc[i * ent_size:(i + 1) * ent_size]
            zindex = int.from_bytes(e[16:20], "big")
            length = int.from_bytes(e[20:25], "big")
            data_offset = int.from_bytes(e[25:30], "big")
            nblocks = (length + block_size - 1) // block_size
            if zindex + nblocks > len(self.blocks):
                raise FormatError("PSARC entry block index outside table")
            if data_offset > self.size:
                raise FormatError("PSARC entry offset outside archive")
            self.entries.append({
                "zindex": zindex, "length": length,
                "offset": data_offset,
            })

    def read(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > self.size or size > self.size - offset:
            raise FormatError("PSARC read outside declared file")
        return self.pkg.read(self.start + offset, size)

    def entry_data(self, i: int, *, limit: int = MAX_FILE_PREVIEW) -> bytes:
        entry = self.entries[i]
        if entry["length"] > limit:
            raise FormatError("PSARC entry exceeds preview limit")
        remaining = entry["length"]
        position = entry["offset"]
        pieces = []
        blocks_needed = (remaining + self.block_size - 1) // self.block_size
        for b in range(blocks_needed):
            raw_len = self.blocks[entry["zindex"] + b]
            packed_len = raw_len if raw_len else min(remaining, self.block_size)
            if packed_len > self.block_size:
                raise FormatError("PSARC stored block exceeds block size")
            packed = self.read(position, packed_len)
            if raw_len:
                try:
                    unpacked = zlib.decompress(packed)
                except zlib.error as exc:
                    raise FormatError("Invalid PSARC zlib block") from exc
            else:
                unpacked = packed
            if len(unpacked) > self.block_size or len(unpacked) > remaining:
                raise FormatError("PSARC inflated block too long")
            remaining -= len(unpacked)
            pieces.append(unpacked)
            position += packed_len
        if remaining != 0:
            raise FormatError("Incomplete PSARC entry")
        return b"".join(pieces)

    def manifest(self) -> list[str]:
        data = self.entry_data(0, limit=MAX_NAMES)
        try:
            paths = data.decode("utf-8-sig").splitlines()
        except UnicodeDecodeError as exc:
            raise FormatError("PSARC manifest is not UTF-8") from exc
        if len(paths) != len(self.entries) - 1:
            raise FormatError("PSARC manifest count does not match TOC")
        if any(not path or path.startswith("/") or "\\" in path
               or ".." in path.split("/") for path in paths):
            raise FormatError("PSARC contains unsafe or empty paths")
        return paths


def summarize(parts: list[str], member: str | None = None,
              map_name: str | None = None, header_samples: int = 0) -> dict:
    if header_samples < 0 or header_samples > 16:
        raise ValueError("--header-samples must be between 0 and 16")
    with JoinedParts(parts) as joined:
        begin, size = unpack_stored_zip(joined, member)
        pkg = DebugPKG(joined, begin, size)
        items = pkg.items()
        archive_files = [item for item in items if item["path"].lower().endswith(".psarc")]
        if len(archive_files) != 1:
            raise FormatError("Expected exactly one PSARC among PKG items")
        a = archive_files[0]
        psarc = PSARC(pkg, a["offset"], a["size"])
        paths = psarc.manifest()
        extensions = Counter()
        directories = Counter()
        for name in paths:
            ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name.rsplit("/", 1)[-1] else "(none)"
            extensions[ext] += 1
            directories["/".join(name.split("/")[:2])] += 1
        sample_magic = {}
        for ext in (".tga", ".bmodel", ".banim", ".lua", ".cgelf"):
            for i, name in enumerate(paths):
                if name.lower().endswith(ext):
                    raw = psarc.entry_data(i + 1)
                    from tools.inventory_game_files import detect_magic
                    sample_magic[ext] = detect_magic(raw[:16])
                    break
        model_anim_headers = {}
        if header_samples:
            from tools.inspect_bmodel_banim import (
                UnsupportedHeader, inspect_resource_header,
            )
            for ext in (".bmodel", ".banim"):
                examples = []
                for i, name in enumerate(paths):
                    if len(examples) >= header_samples:
                        break
                    if not name.lower().endswith(ext):
                        continue
                    if psarc.entries[i + 1]["length"] > MAX_FILE_PREVIEW:
                        continue  # large resources are outside this bounded probe
                    raw = psarc.entry_data(i + 1)
                    try:
                        result = inspect_resource_header(name, raw)
                    except UnsupportedHeader as exc:
                        result = {"unrecognized_header": str(exc)}
                    examples.append({"resource": name, **result})
                model_anim_headers[ext] = examples

        selected_map = None
        if map_name is not None:
            from tools.inspect_map_coll import (
                MapFormatError, summarize_collision, summarize_visibility,
                summarize_placement, validate_map_name,
            )
            validate_map_name(map_name)
            catalog = {path: i + 1 for i, path in enumerate(paths)}
            base = "data/maps/" + map_name
            selected_map = {"name": map_name}
            for ext, key, decoder in (
                (".coll", "collision", summarize_collision),
                (".vis", "visibility", summarize_visibility),
                (".ini", "placements", summarize_placement),
            ):
                entry_index = catalog.get(base + ext)
                if entry_index is not None:
                    data = psarc.entry_data(entry_index, limit=8_000_000)
                    selected_map[key] = decoder(data)
            if len(selected_map) == 1:
                raise MapFormatError("Selected map has no known COLL/VIS/INI resources")
        return {
            "content_id": pkg.content_id,
            "pkg_item_count": pkg.item_count,
            "pkg_items": [{"path": x["path"], "size": x["size"], "kind": x["kind"]}
                          for x in items],
            "psarc": {
                "path": a["path"], "size": a["size"], "version": f"0x{psarc.version:08x}",
                "compression": psarc.compression, "toc_entries": len(psarc.entries),
                "manifest_paths": len(paths), "block_size": psarc.block_size,
                "flags": psarc.flags,
                "extension_counts": dict(sorted(extensions.items())),
                "directory_counts": dict(sorted(directories.items())),
                "example_signatures": sample_magic,
            },
            "warning": "Only file listings and summary signatures; NO asset bytes exported.",
            **({"selected_map": selected_map} if selected_map is not None else {}),
            **({"model_anim_headers": model_anim_headers} if header_samples else {}),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", help="ZIP fragments in correct byte order")
    parser.add_argument("--member", help="Optional exact ZIP member name")
    parser.add_argument("--map", help="Optional map ID, e.g. map1-1; summary only")
    parser.add_argument("--header-samples", type=int, default=0,
                        help="Up to 16 examples each of .bmodel/.banim headers")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = summarize(args.parts, args.member, args.map, args.header_samples)
    except (FormatError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"PS3 asset inspection error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Content ID:", report["content_id"])
        print("Package items:", report["pkg_item_count"])
        print("PSARC entries:", report["psarc"]["toc_entries"])
        print("Manifest paths:", report["psarc"]["manifest_paths"])
        print("Extensions:", report["psarc"]["extension_counts"])
        print("Sample signatures:", report["psarc"]["example_signatures"])
        if "selected_map" in report:
            print("Map summary:", report["selected_map"])
        if "model_anim_headers" in report:
            print("3D resource header summaries:", report["model_anim_headers"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
