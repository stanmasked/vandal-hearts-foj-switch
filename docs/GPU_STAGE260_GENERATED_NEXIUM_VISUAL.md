# Stage260 — actual NeXium GPU pixel evidence gate

This stage deliberately tests **only invented** FoJ research interchange
assets, but uses the **same Stage259 deko3d NRO and actual UAM shader
binaries** as the opt-in private GPU renderer.

## Isolated GPU fixture

The generated SD directory contains:
- `actor.fojrm`: two separate large triangles, 6 vertices, two ordered batches
- `actor.fojmat`: explicit batch-to-texture mapping 0 then 1
- `material0.dds`: solid warm red-orange 64×64 classic RGBA8
- `material1.dds`: solid cyan 64×64 classic RGBA8
- `foj_actor.vert.dksh` and `foj_triangle.frag.dksh`: generated
  exclusively by UAM from this repository's public shader source

The fixture generator refuses existing SD roots and never accepts a PS3
package, an original model/image, or a user-selected asset location. The
generated files are temporary CI files, not committed, and the report
does not contain filesystem source locations or source fingerprints.

## Real guest proof requirements

A dedicated two-job workflow builds the native
`foj-deko3d-private-actor-upload.nro` with devkitA64, compiles the DKSH
shaders with UAM, then opens **the real NRO** in a Linux NeXium guest
using an isolated generated-only SD under Vulkan Lavapipe/Xvfb.

The guest step takes **two direct NeXium window screenshots** and runs a
separate image classifier that requires:
- A sufficiently large red-orange and a sufficiently large cyan polygon
  near the middle of the 1280×720 guest viewport, not just UI markers
- The red-orange material visibly left of the cyan one, reflecting
  ordered material indices and separate texture descriptors
- Both colors present in both captures with stable relative positions

Unit tests intentionally draw synthetic fake screenshots to challenge
the classifier (missing material, swapped colors, blank screen, missing
second frame). **Those unit-test images never count as guest evidence.**

### Evidence interpretation

A successful stage can establish generated data was actually *visibly
rendered by NeXium* in the experimental GPU pipeline. A green compiler
job alone must NOT be called a visual success. An emulator unsupported
GPU path, missing virtual SD integration or failed Vulkan backend is an
explicit failed/incomplete runtime gate; diagnose from sanitized guest
logs and screenshots rather than fabricating success.

Even a successful generated asset screenshot does not prove:
- Any commercial PS3 FoJ model or DDS appears on a Switch
- Physical Switch GPU output, performance, memory, texture fidelity
- Animation/bone/camera/depth parity with the original FoJ or gameplay

Original game files remain on the user's private storage and must
never be copied to public GitHub Actions or uploaded as artifacts.
