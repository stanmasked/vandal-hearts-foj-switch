# Original FoJ rig-to-animation compatibility and experimental CPU skinning

**Research date: 2026-10-16.** All original resource counts and parent
hierarchy comparisons in this report were obtained from the user's own
`NPEB00148` split PS3 package → `USRDIR/cdata.psarc`. No original
geometry, texture, skin weight array or animation clip has been committed
to GitHub.

## Real original model and clip compatibility

Previous research recovered 89 original BMODEL skeletons and all 450
BANIM track hierarchies.

For each asset, the whole sequence of parent bone indices was compared,
not just its number of joints.

| Verified structural measure | Result |
| --- | ---: |
| Skeleton-bearing original BMODEL resources | **89** |
| Original BANIM clips | **450** |
| BMODEL rigs with at least one matching BANIM hierarchy | **89 / 89** |
| BANIM clips with at least one matching BMODEL hierarchy | **449 / 450** |
| Matching distinct hierarchy layouts | **24** |
| Possible model–animation pairs sharing complete parent layout | **4,011** |

The sole unmatched clip is
`data/actors/anims/brawler_hammer_smash.banim`: it has **74 tracks**;
none of the studied model skeletons has its exact ordered parent list.

Sample grounded compatible group:

- `avatar_body.bmodel` — 28-bone rig.
- `avatar_small_body.bmodel` — same 28-bone layout.
- `avatar_idle.banim`, `avatar_hit.banim`, `avatar_death.banim` — all
  match that complete parent list.

**Important:** equality of parent layout is *not* confirmation that every
matched model–animation combination is semantically intended, or that it
will render correctly. Different actors may share a rig layout with
different bind transforms and scale.

In all **87** original models with `0x0F` weighted vertex tables, every
bone index used by those weights is smaller than the actual number of
bones in that model's `0x0A` rig section. No out-of-range indices were
found in the complete local scan.

### Absolute or additive local transforms?

In `avatar_idle.banim`, comparing the first keyframe on each of its
28 tracks with the corresponding BMODEL rig entry:

- **27 of 28** track translations differ by less than 0.01 game units.
- Median absolute quaternion dot product is about **0.9738**, meaning
  the rotations often differ from the static rig pose.
- Its `avatar_hit` and `avatar_death` clips show similarly close
  translations but differing first-frame rotations.

This is **consistent with** local pose transforms, not definitive proof of
the original engine's transform blending convention. Do not assume
`BANIM[0]` should be identical to the rest pose; actual animation
can begin in a different pose.

## Reproducible aggregate audit

Source: [tools/audit_rig_clip_pairs.py](../tools/audit_rig_clip_pairs.py).
Generated-data tests: [tests/test_audit_rig_clip_pairs.py](../tests/test_audit_rig_clip_pairs.py).

Run locally (the program reads the two protected ZIP parts but reports
only hierarchy statistics and the name of any unmatched clip):

```sh
python3 -m tools.audit_rig_clip_pairs \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" > local-rig-compatibility.json
```

This does not export mesh/animation payloads and does not add protected
assets to the repository.

## Portable experimental skinning code

[core/skeletal_skin.c](../core/skeletal_skin.c) adds:

1. A bounded, topologically ordered parent–child affine transform
   hierarchy, with multiple independent roots supported.
2. Local quaternion XYZW + translation XYZ to row-major 3×4 matrices.
3. A bind-world matrix and its rigid inverse for each bone.
4. A skinning palette: `animated_world × inverse(bind_world)`.
5. Linear blend skinning for 1–5 bone influences per vertex, with an
   explicit unweighted/rigid vertex path and strict validation.
6. Direct integration with the already tested native BANIM quaternion
   interpolator `core/banim_core.c`, requiring identical parent layouts.

### Validation of the mathematical pipeline

Generated C fixtures verify that identical bind and animated poses produce
an identity deformation, a 90-degree child-joint rotation moves only the
child-weighted geometry, a 50/50 weight blend yields the expected midpoint,
and unrelated roots behave independently.

Invalid indices, malformed weights, unnormalized quaternion values,
mismatched parent hierarchies and insufficient buffers are rejected.
CI compiles under strict C11 flags and runs AddressSanitizer/UBSan.

**Caveat:** these tests verify our *chosen mathematical implementation*.
The original FoJ renderer's order of operations, coordinate handedness,
inverse-bind policy, transform conventions and animation blending are
still unconfirmed. Skinning real user-owned FoJ geometry must be validated
visually against original gameplay before claiming fidelity.

## Switch CPU skinning diagnostic

A seventh clean-room homebrew build,
**`foj-skinning-research.nro`**, includes this exact portable code.
It renders a **generated** articulated two-bone wireframe object; the upper
piece rotates relative to the lower piece and visibly demonstrates
weighted vertex deformation. It contains no original user game resources.

See [SKINNING_SWITCH_VIEWER.md](SKINNING_SWITCH_VIEWER.md).

## Remaining original-game milestones

- Verify BMODEL bind transforms and BANIM pose conventions against actual
  original-game appearance.
- Match compatible clips to particular actors by scene/character references,
  not just matching skeleton layouts.
- Create a user-local end-to-end pipeline for original vertex/weight/rig
  plus matching animation data, with no copyrighted assets in GitHub.
- Render the actual animated model with UV-correct DDS atlas, depth buffer
  and proper camera/lighting on desktop and Switch.
- Test the result on physical Switch hardware. The native NRO currently
  has only compilation/CI evidence, not an observed hardware run.
- Recover the original tactical engine, Lua callbacks, AI, UI and campaign.

**Status: structural compatibility and portable CPU-skinning mathematics
implemented; original skinned FoJ actor rendering remains unverified.**
