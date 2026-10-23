# Stage333 — Bounded PSARC short raw tail

The owner-local PS3 PKG inventory revealed a PSARC **short, incompressible final block** whose 16-bit length equals its 160-byte decoded remainder. Legacy `PSARC.entry_data` assumed every positive block length was zlib, causing a false corruption report before DDS decoding.

The parser now accepts this **one narrow case**: a nonzero block length equal to a positive remaining entry extent **smaller than the PSARC block size**, if zlib decompression fails **and** the bytes do not have a valid-looking RFC1950 zlib header. All other truncated, malformed or overinflated blocks continue to fail closed. The raw acceptance is an archive-format interpretation, not authentication of source data; package-byte integrity must be established separately.

The seven generated-only tests cover a raw partial tail, a compressed tail, the full-block zero sentinel, length mismatch, damaged zlib header, overinflation and unsafe truncated block. No original game bytes, keys, texture names or decoded images are present in GitHub or its CI.

Owner-only Stage333 pixel parity is a **separate** private gate: Stage332 C RGBA8 pixels compared to Pillow 12.3's independent DDS implementation on selected original PSARC DDS members. That local proof is stored only in Google Drive; it does not establish game runtime, native GPU texture mapping, physical Nintendo Switch performance or independent identity to the unsplit canonical PKG.
