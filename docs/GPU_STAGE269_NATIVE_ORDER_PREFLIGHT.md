# Stage269 — native fail-closed triangle ordering preflight

Stage268's projected-triangle overlap crossing detector was host-only. Stage269
adds a separately compiled **native C99** guard to the real three-layer
Nintendo Switch research NRO, without modifying the already proven Stage267
executable or its shaders.

## Mode and behavior

```sh
make -f gpu/guarded_three_layer.mk verify
# build/foj-deko3d-three-layer-guarded-proof.nro
```

The opt-in build defines `FOJ_GPU_NATIVE_ORDER_GUARD` alongside the
existing three-layer alpha and depth flags.

After reading the entire **generated-only** FOJRM001 / FOJMAT01 / three DDS
bundle, but **before creating a GPU device**, it checks the nine projected
vertices in their three one-triangle material sections. Materials remain
0 near violet, 1 middle warm, 2 rear cool, with fixed GPU draw order
[2,1,0]. If any projected triangle has invalid/out-of-clip coordinates,
nonfinite Z/W, a degenerate projection, or a mismatch in the expected
material/vertex sections, fail closed with exit status 8.

For every transparent/transparent and transparent/opaque overlapping pair,
the guard clips their screen-space overlap polygon and barycentrically
interpolates the projected depths at each overlap vertex. The fixed
near-before-far relation must be strictly true over the complete overlap.
Depth equality and sign crossings are rejected: the application exits
before allocating a deko3d device. The diagnostic contains only an error
class, not any original material bytes, filenames, or private geometry.

Disjoint projected interiors are safe for this limited ordering check.
This is a static orthographic three-triangle guard, **not** polygon
splitting or general-purpose transparent rendering.

## Verification gates

```sh
for cc in gcc clang; do
    "$cc" -std=c11 -Wall -Wextra -Werror -pedantic \
      -Igpu -Icore \
      gpu/transparent_order_guard.c \
      tests/native/stage269_transparency_guard.c -lm \
      -o "/tmp/foj-order-guard-$cc"
    "/tmp/foj-order-guard-$cc"
done
```

The dedicated Stage269 GitHub Actions pipeline runs both host compilers,
then builds the native guarded NRO with devkitA64 and UAM shaders. Once
built, it executes three real NeXium GPU guests using the **same three
Stage267 scene cases and independent six-frame RGB probe verifier**.
A passing guarded NRO should preserve the baseline reference RGB values
(111,100,162), (59,137,210), and (127,128,123).

Native host negative tests check a crossing depth plane, coplanar and
near-equal intersections, an opaque rear drawn in front, invalid material
mapping, clip-space/NaN/W violations, degenerate geometry and wrong
section counts. A rejected case is **not** counted as GPU evidence.

## Limits

The guard currently accepts exactly three single-triangle, flat projected
sections with W=1 and depth compare GREATER. It does not extend to
multi-triangle meshes, perspective W, arbitrary alpha textures,
intersecting triangle splitting, order-independent transparency, actual
PS3 asset formats or retail Switch hardware. An additional **actual
NeXium negative guest scenario** remains needed to prove the native
pre-device rejection path end-to-end; the C host rejection and positive
GPU capture alone do not prove that negative guest behavior.

No original PS3 files enter this PR or public GitHub Actions. Keep the
PR Draft until all native, emulator and inherited regressions pass.
