# GPU Stage285 — two-dimensional U/V alpha intersection audit

**Stacked on:** [Stage284 PR #169](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/169), successful real-NeXium workflow [#39628839955](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39628839955).

Stage284 established horizontal U and vertical V boundaries independently in the same generated DDS and audited 324 one-dimensional RGB samples per two-frame capture set. Stage285 adds a strict 17×17 raster audit centered on their crossing.

## Intersection contract

- Expected U boundary: X = 649.
- Expected V boundary: Y = 395.
- Sample window: X = 641…657 and Y = 387…403 (17×17 = 289 pixels per frame).
- Both actual NeXium frames must contain the same exact 2-D profile: clear-source RGB \`(126, 129, 123)\` everywhere except the southeast 9×9 quadrant, which must be opaque-source RGB \`(96, 72, 201)\`.
- Four quadrant counts must be 64 northwest-clear, 72 northeast-clear, 72 southwest-clear and 81 southeast-opaque samples.
- The four pixels surrounding the crossing are checked explicitly; a one-pixel shift or a leak into any transparent quadrant is rejected.
- The full 289-pixel intersection patch must be byte-for-byte stable between the two captured frames.

The auditor first reruns Stage284's provenance, DDS identity, viewport, one-dimensional edge, distinct-frame and native sort/blend/depth checks. The new grid is then measured from the captured RGB frames, not reconstructed from the expected mask.

## Limits

This remains a generated-only GPU experiment. It does not use or claim original PS3 resources, infer sampler filtering, or prove physical Nintendo Switch execution. Synthetic PNG tests only validate rejection behavior; they are not accepted as guest evidence.
