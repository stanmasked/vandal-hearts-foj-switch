# Stage 186 — COLL bounds in an actual NeXium guest session

The Stage 184/185 COLL controls are tested at their exact min/max
limits with real NeXium window captures, not only native compilation.

After the previous stage ends with cursor (25,25), tile size 12,
channel 0, the workflow sends the following key sequences:

| State | Expected cursor | Tile size | Key |
| --- | --- | --- | --- |
| left-edge | (0,25) | 12 | Left |
| top-edge | (0,0) | 12 | Up |
| min-zoom | (0,0) | 4 | R = ZL |
| max-zoom | (0,0) | 30 | T = ZR |
| right-edge | (49,0) | 30 | Right |
| bottom-edge | (49,49) | 30 | Down |

For each boundary the CI captures the normal state, then sends four
more outward inputs, captures a second screenshot and rejects any
meaningful new change. This catches off-by-one movement, zoom
overshoot or repeated-key activation errors.

The portable C host program already used in Stage 184 produces an
independent 1280×720 reference for each expected state. Stage 186
requires each guest capture and repeated capture to match the correct
C reference and to preserve the source-generated status rectangle.

All experiments use the invented 50×50 fallback grid without
original FoJ resources. Passing this test in NeXium establishes
**emulator behavior** for the synthetic COLL homebrew, not original
PS3 height/collision semantics or physical Nintendo Switch GPU output.

The workflow retains all prior Stage 182–185 checks, releases
screenshots and a JSON receipt into
`foj-stage186-nexium-coll-bounds-evidence` and runs six generated-only
negative/positive verifier tests before launching guest scenarios.
