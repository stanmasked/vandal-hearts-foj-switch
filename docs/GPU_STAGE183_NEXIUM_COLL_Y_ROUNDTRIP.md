# Stage 183 — NeXium COLL-viewer Y-button roundtrip

This stage extends the already validated Stage 182 **real NeXium guest
runtime** smoke test to verify that the native `foj-coll-map-research.nro`
actually responds to the Switch **Y** button by switching the visible
COLL map presentation from heatmap to diagnostic isometric mode and back.

The NeXium source `nexium-gui/src/controller_config.rs` documents its
default keyboard mapping: **Z = Switch Y**. The CI runner sends Z twice
with a key-down/up pair and captures real NRO guest frames before,
after the first Y and after the second Y.

## Two independent source-derived references

`tools/foj_stage183_coll_mode_reference.c` constructs a **generated-only
50×50 map** with the same formula as the viewer fallback. It compiles
against the **actual portable C renderer modules used by the Switch
NRO**: `core/coll_view.c` and `core/coll_iso_view.c`. It produces one
reference PNG for the 2D heatmap and one for the isometric data plot,
including the red synthetic-fallback status rectangle.

The host reference is never accepted as guest evidence. The verifier
takes **three separately captured NeXium screenshots** and requires:

- Initial frame agrees with the C 2D heatmap reference.
- After a Y/Z key press, the frame agrees with the C isometric reference
  and differs substantially from the previous guest frame.
- After pressing Y/Z again, the new guest frame returns to the heatmap
  reference and approximately matches the first guest frame.
- Mode-specific gold cursor colors and the persistent red synthetic
  status marker are present in each state.

The verifier uses reference palette/count overlap to tolerate shifts
caused by emulator window borders without equating screenshots to
pixel-identical host framebuffers. Seven invented positive/negative
regressions reject a blank frame, wrong order, unchanged toggle,
failure to return, missing status marker or mismatched references.
These regressions alone do not establish runtime; the **NeXium-runner
screenshot capture** is what validates guest execution.

## Evidence

GitHub Actions workflow:
`.github/workflows/stage182-nexium-smoke.yml` (display name begins
"Stage 183 NeXium COLL Y roundtrip"). It still exercises the Stage 182
isometric tactics scene and prior screen-checker before the new COLL
roundtrip. It publishes the guest screenshots, both generated reference
PNGs, startup logs, NeXium nightly archive digest, and JSON receipts
under `foj-stage183-nexium-coll-y-runtime-evidence`.

The generated isometric COLL view **does not** interpret numeric
`.coll` columns as gameplay height or collision fields. All art is
invented; no original PlayStation 3 asset or executable is uploaded.
A successful emulator session is **not** proof of display or performance
on a physical Nintendo Switch, nor of original FoJ gameplay fidelity.
