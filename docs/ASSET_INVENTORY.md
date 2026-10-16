# Gate 1 — local game-asset inventory

The verified package report is [REAL_PKG_NPEB00148.md](REAL_PKG_NPEB00148.md).
The submitted PKG is tagged **non-finalized/debug-style** (`0x0000`), has
21 declared items and a large data region. **The item table, executable and
actual game assets have not yet been read**; the PKG's visible header alone
cannot establish any resource formats or the original engine.

## Input contract

If and when you have lawfully accessible, already extracted game files on your
own computer, point the research-only tool at a directory containing them.
The tool does **not** decrypt, unpack, modify or upload PS3 data.

```sh
python3 -m tools.inventory_game_files "/path/to/accessible/game-directory" --json > foj-asset-inventory.json
```

It reports aggregate file count, total size, extension histogram and magic
signature histogram. It recognises a small subset of standard container
signatures (SFO, SELF, PKG, DDS, PNG, Ogg, WAV, PSMF and VAG) and labels all
other bytes `unknown` — this does **not** mean they are unusable.

To include up to 100 relative filenames for local investigation, add
`--include-paths`. Paths are excluded by default. License material with
`.rap`, `.rif`, `.edat`, `.key`, `.act`, and several known sensitive
filenames is skipped, as are symlinks. The inventory reads only 16 bytes per
non-skipped file.

If original game assets cannot be accessed, **do not** infer their format
from random encrypted bytes or from the synthetic Switch renderer. Record the
blocker instead.

## Safety notes

- Do not upload the PKG, commercial game files, executable, licenses or keys
  to GitHub, even to a private repository.
- Upload only the text statistics if desired, after reviewing them for
  sensitive paths (especially if using `--include-paths`).
- No extraction/decryption/bypass capability is included in this tool.
- Possessing a copy does not grant a general right to redistribute its assets.

## Next research outputs

- Data-format discovery matrix with `confirmed` / `hypothesis` flags.
- One reproducible, independent parser for a confirmed resource format.
- An actual asset preview on desktop, followed by a Switch proof-of-concept.
- Engine and gameplay investigation only after identifying which real files
  are legally and technically accessible.
