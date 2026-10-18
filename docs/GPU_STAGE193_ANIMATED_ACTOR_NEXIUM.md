# Stage 193 — controller-driven animated actor in a real Switch NRO

This stage connects the Stage 192 production `FojAnimPlayer` C controller
to `foj-animated-actor-research.nro`, a **separate** generated-only
Nintendo Switch research homebrew. It intentionally does not change the
existing BMODEL/BANIM readers or viewers.

## Implemented path

`switch/source/anim_player_main.c` constructs two invented two-bone
`FojAnimClip` values with matching hierarchies, an invented skinned
hinged-strip mesh and bind pose. Every rendered guest frame takes the path:

1. `foj_player_advance` / `foj_player_switch` / `foj_player_pause`;
2. `foj_player_palette` using the production C local-pose blending and
   experimental skeleton/inverse-bind matrix implementation;
3. `foj_skin_deform` weighted vertices;
4. `foj_obj_wireframe` into the libnx framebuffer.

Input uses NeXium's existing research-key mapping:

| Button | Action |
| --- | --- |
| A (C key in NeXium) | Pause or resume current clip and any fade |
| B (X key) | Reset to clip A at t=0 and pause |
| Y (Z key) | Crossfade 0.5s to the other invented clip |
| D-pad right (Right key) | Advance 0.125s while paused for exact fade steps |
| Plus | Exit |

The NRO starts **paused** on the first frame, avoiding unreliable real-time
capture cadence for its deterministic NeXium test. While playing, the
research loop advances by a *nominal* 1/60s per rendered iteration; actual
guest frame interval/timing is not asserted or measured here. Timeline
end behavior saturates as documented at Stage 192.

The picture intentionally includes diagnostic swatches: red = generated
only, cyan/orange = clip A/B, green/magenta = paused/playing, yellow =
crossfade with 0/25/50/75% stepping squares. These **are not** original
game UI or graphics.

## Automated emulator regression

`.github/workflows/stage193-nexium-animation.yml` builds a distinct
libnx NRO in devkitA64, launches it inside NeXium under Xvfb/Lavapipe,
sends discrete A/B/Y/D-pad-right inputs, and captures nine guest
screenshots to a separate Actions artifact. The fail-closed checker:

- requires a real nonempty wireframe and generated-only source marker;
- checks clip A and B status after actual emulated inputs;
- checks paused geometry stays unchanged between two samples;
- checks starting a fade with 0% weight does not jump;
- checks 25%, 50%, and 75% progression with staged input and
  changed skinned geometry; also verifies promotion to B;
- refuses absent, blank, wrong-size, unchanged, mislabelled or
  incorrectly progressing images.

The checker has eight synthetic positive/negative fixture tests to
exercise rejection paths. Synthetic fixtures by themselves are **not**
evidence that NeXium launched the NRO. Only the actual workflow guest
screenshots and a successful post-build checker establish that.

## Reproduction

```sh
make -f switch/Makefile build/foj-animated-actor-research.nro
python3 tools/validate_nro.py build/foj-animated-actor-research.nro
# Host-side unit tests: require Pillow
python3 -m unittest discover -s tests/emulator \
    -p 'test_stage193_animation_frame_check.py' -v
```

## Limits

This is a newly invented 2-bone animation that uses the experimental
FoJ research math. The precise original PS3 animation blending,
model/clip pair associations, timing, animation state machine, meshes,
textures and battle gameplay remain unverified. No original game bytes
are committed or shared; no physical Switch execution or playable
FoJ port is claimed.
