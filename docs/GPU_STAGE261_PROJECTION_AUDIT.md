# Stage261 — actual GPU silhouette vs. independent camera projection

Stage260 proved a generated two-material static GPU image is visible in
NeXium. Stage261 adds a **geometric pixel-level regression**, not just color
counts: two fresh real emulator screenshots must agree with an independently
implemented clean-room orthographic camera projection.

The projected polygons come from the invented Stage260 FOJRM001 fixture:
- warm: (-0.86,-0.42), (-0.03,-0.42), (-0.44,+0.64)
- cool: (+0.03,-0.42), (+0.86,-0.42), (+0.44,+0.64)
- camera center=(0,0), yaw=pitch=0, extent=2, zoom=1
- 1280x720; projected pixel scale=0.84*720/2=302.4 px per coordinate

The independent image checker projects these into pixel-space predicted
triangles, builds masks with Pillow, and compares those masks with
the actually colored GPU polygons. Each polygon must satisfy:
- intersection-over-union at least 0.78
- precision at least 0.90 and recall at least 0.81
- plausible bounding box and warm-left/cool-right material ordering
- silhouette stability in two separate real NeXium screenshots
- independently changed clear-color background, not a duplicate screenshot

The tolerances explicitly account for host window viewport adjustments,
raster edge rules, and antialiasing. They must **not** be used to justify
claims of exact GPU/CPU pixel parity.

Positive and negative classifier unit tests use invented PIL screenshots,
but only the **separate real NeXium NRO run** may satisfy the guest evidence
gate. Cases with absent, reversed, shifted, or scaled triangles fail closed.

The dedicated `.github/workflows/stage261-gpu-projection-audit.yml`
rebuilds the real Stage259 private-capable NRO plus generated UAM shaders,
constructs only invented FOJRM001/FOJMAT01/DDS on isolated virtual SD,
captures fresh frames, and validates color and geometric projections.

No copyrighted FoJ resources are embedded, uploaded or used in CI.
This is generated static geometry on the NeXium GPU backend, **not**
original character fidelity, original animations, a PS3 camera
reconstruction, physical Nintendo Switch graphics, or a playable port.
