# Stage 218 — local COLL raw records beside the synthetic battle

This is a **read-only diagnostic connection** between the already implemented
PS3 COLL parser and the Stage217 generated 8×6 tactical demo. The four
numeric fields and two flags per COLL record have **unverified meanings**.
In particular, they must not be automatically interpreted as original
elevation, obstacles, passability, movement cost or attack range.

## Local-only behavior

`foj-switch-research.nro` optionally attempts to load a user-supplied file at:

    sdmc:/switch/foj/maps/map1-1.coll

A bounded read (up to 1 MiB) must pass the existing strict C11
`foj_coll_parse` grammar and field checks. If successfully parsed,
`foj_coll_battle_window` copies the **center 8×6 records** into a
small diagnostic buffer. For the observed original 50×50 dimensions
this corresponds to source coordinates x=21–28 and y=22–27.
The original file stays on the owner's SD card. No data, private
paths, values, hashes or screenshots are uploaded automatically.

Move the cursor with D-pad and press L/R to switch between the four raw
floating-point channels and the two boolean flags. A local text line
shows the selected raw value plus its original COLL grid coordinate.
The *battle terrain, units, movement, height differences and attacks*
remain the invented Stage217 state; neither map rows nor boolean flags
are used to modify tactical rules.

If the local file is absent, malformed, truncated, too large or smaller
than the complete 8×6 diagnostic window, the NRO retains the Stage217
synthetic map and explicitly says no private COLL window was loaded.

The isometric research NRO remains synthetic in this stage. Only the
console research NRO gets the COLL diagnostic readout.

## Independent portable C tests

`core/coll_battle_window.[ch]` is a fixed-size, allocation-free,
platform-neutral bridge. It enforces window bounds, copies exactly 48
records, rejects nonfinite samples and non-boolean flags, provides bounded
channel access and zeroes the output on rejection. It neither accepts
nor writes a `FojDemo` gameplay state.

`tests/test_coll_battle_window.c` uses generated values with 50×50
grid dimensions and a synthetic minimal 8×6 grid. It verifies exact
source-cell identity and all six channels, boundary rejection,
nonfinite input handling, output zeroing and unchanged synthetic
tactical terrain. GitHub Actions runs strict C11 compilation and UBSan;
no original game resources are required.

## Status and limitations

This connects a locally owned real-format COLL file to a visible
battle-side **research readout** only. It does not recover mission scripts,
map object placement, original combat behavior, original terrain
semantics or a playable PS3 conversion. Attribution of file provenance
remains a separate, owner-private evidentiary task.

Stage217 PR #101 has passed its CI and merged to `main` in commit
`e63281450a6ce2fb322fdf920230efffc6c9eb50`. Stage218 now targets
`main` and requires separate Python 3.11/3.13, strict C11 and Switch
NRO checks before merging.
