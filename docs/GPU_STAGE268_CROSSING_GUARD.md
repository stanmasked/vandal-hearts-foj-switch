# Stage268 — conservative triangle-order guard for translucent geometry

This is a **CPU-only geometry diagnostic**, stacked above Stage267 (#151),
Stage266 (#150), and Stage265 (#149). It does **not** modify the native
deko3d renderer, shaders, extracted PS3 graphics, or NeXium GPU evidence.

## Why it exists

Stage267 demonstrates **two translucent, fully overlapping, fixed-depth**
surfaces over one opaque background. The renderer can draw back-to-front.
For two translucent triangles whose depths cross *inside the same screen
pixels*, neither triangle can be drawn entirely before the other with
correct standard source-over alpha. A simple scalar depth sort is not
sufficient; the eventual renderer will need splitting, per-pixel
compositing, depth peeling, or an appropriate order-independent technique.

Stage268 conservatively detects this limitation before any false
"sorted transparency" claim.

## Host analyzer

`tools/foj_stage268_transparency_crossing.py`:

- Accepts 1 to 64 *invented* projected translucent triangles, three
  finite clip-space (x,y,z) coordinates each; XY in [-1,1], Z in [0,1].
  A **larger Z is nearer**, matching Stage263's GREATER convention.
- Rejects missing/duplicate IDs, degenerate screen projections,
  NaN/inf/out-of-range coordinates and unsupported geometry.
- Clips each projected triangle against the other using winding-aware
  Sutherland-Hodgman clipping. A zero-area point/edge contact is
  treated as disjoint.
- Uses barycentric interpolation to evaluate their respective
  projected depths at **every overlapping polygon vertex**. Affine
  depth differences attain extrema at vertices, so a strict fixed sign
  across all overlap vertices proves one triangle stays behind the
  other *within this clipped region*.
- Builds far-to-near ordering constraints for overlapping pairs and
  performs deterministic topological sorting. Rejects ambiguous
  near-coplanar overlap, any sign-crossing and cyclic dependencies.

The analyzer is intentionally conservative: nearly equal depth,
including tangential depth equality at a boundary, is rejected rather
than presented as a proof of order.

## What is tested

```sh
python3 -m unittest discover -s tests/emulator \
  -p 'test_stage268_transparency_crossing.py' -v
python3 -m tools.foj_stage268_transparency_crossing
```

The unit suite covers Stage267's safely ordered generated layout,
depth crossings, both triangle windings, safe near/far reversals,
disjoint interiors and edge contacts, partial screen overlap,
contained triangles, coplanar and near-coplanar conflicts, malformed
geometry and deterministic results under input permutations.

## Limits and next gate

This model assumes triangles are already projected orthographically
and Z interpolates affinely over screen XY, as in the current research
stream with constant homogeneous W. It does not model
perspective-correct depth conventions, clipping against the near plane,
stencil effects, alpha test, non-triangle topology, transparent textures
with partially empty regions, screen subdivision or triangle splitting.

Most importantly, the host analyzer is **not yet called by the native
NRO**. Its rejection is a planning guard, not an existing runtime
fail-closed check. The next implementation step is to connect a
validated scene preflight to the actual renderer and add a real
NeXium negative scenario for crossing layers, without weakening the
Stage267 six-frame success oracle. This PR must remain Draft until
the new Python CI and inherited checks are complete.
