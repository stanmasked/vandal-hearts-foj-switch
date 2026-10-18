# Stage 184 — NeXium cursor, zoom and six-channel COLL input test

This stage expands the Stage 183 **real guest window** test with
**D-pad Right**, **ZR**, and **six consecutive R presses**. The tested
application is `foj-coll-map-research.nro`, containing only independently
generated fallback data unless a user independently supplies a COLL
file on their own system. CI does not supply any original PS3 assets.

## Verified emulator keyboard defaults

The upstream NeXium `nexium-gui/src/controller_config.rs` maps
Switch D-pad Right → `ArrowRight`, ZR → `T` and R → `E`.
Its Y → `Z` mapping was already tested by Stage 183.

The test begins immediately after successful Y → isometric view → Y
→ heatmap roundtrip, in the **same running emulator guest**. It records:

| State | Cursor | Display tile | Raw COLL column |
| --- | --- | --- | --- |
| cursor-right | 26,25 | 12 px | 0 |
| zoom | 26,25 | 14 px | 0 |
| ch1 through ch5 | 26,25 | 14 px | 1–5 |
| ch0 | 26,25 | 14 px | 0 (wrap) |

## Reference comparison

The host-only `tools/foj_stage183_coll_mode_reference.c` still
supports its previous two-argument form, plus a validated optional
cursor X/Y, tile size and channel. It uses the exact **portable C
heatmap renderer linked into the NRO** and the generated 50×50
fallback data. Eight new PNG references are created in CI.

`tools/foj_stage184_coll_input_check.py` checks each of the eight
**real NeXium guest PNG captures** against the corresponding C
reference, locating the persistent red synthetic-data marker
to account for window-border offsets. It samples hundreds of
**non-background map pixels at known locations**, not just aggregate
RGB counts, and requires substantial guest frame changes after
presses. The sixth R press must restore channel 0 with the cursor
and zoom preserved.

Six invented-only regressions reject unresponsive controls,
a wrong channel, missing synthetic status, a failed wrap or
mismatched reference dimensions. These tests are not a substitute
for the actual emulator guest run.

Evidence remains in the GitHub Actions workflow
`.github/workflows/stage182-nexium-smoke.yml`, now displayed as
**Stage 184 NeXium COLL six-channel guest input**.

**Limits:** Passing establishes input-driven visualization within
NeXium only. No Nintendo Switch physical hardware display, original
FoJ combat semantics, COLL column interpretations or commercial
PS3 assets are validated.
