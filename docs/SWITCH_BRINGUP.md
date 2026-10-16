# Nintendo Switch homebrew bring-up

This phase verifies **compiler/toolchain integration and a synthetic tactical
logic demonstrator**, using console text and no game files. The NRO is **not**
the PS3 game.

## Build

Requires a recent devkitPro devkitA64 / libnx toolchain and the usual Switch
Homebrew SDK support.

From the repository root:

```sh
make -f switch/Makefile verify
```


Produces `build/foj-switch-research.nro` and checks magic,
declared file size, and segment bounds.

GitHub Actions uses `devkitpro/devkita64:latest` to compile the
research NRO and uploads the result as `foj-switch-research-nro`.
See [Switch NRO workflow](../.github/workflows/switch-nro.yml).

## Controls

- D-pad: move a cursor across the invented 8×6 battlefield.
- A: select the hero at H, or attempt a reachable move.
- B: cancel a selection.
- Plus: exits to the homebrew loader.

The invented elevation- and obstacle-aware movement uses `core/tactical_demo.c`.
A breadth-first search computes reachable tiles with a four-step budget and
maximum one-level climb per step. This is **not** the original game's battle
rules, meshes, renderer, menus, save system, PS3 executable or data.

## Portable movement core

Host-side tests in `tests/test_tactical_demo.c` validate reachability, slope
limits, blocking, selection, rejection, cancellation and cursor clamping.
They are executed through `.github/workflows/ci.yml` with the system C compiler.
The same core source is linked into the Switch `NRO` build.

## Evidence ladder

1. Successful host-side unit tests — parser and validation only.
2. Successful NRO compiler/linker run — shell builds for ARM64.
3. NRO0 header/segment validation — structural plausibility only.
4. Emulator launch and input smoke test — runtime evidence on emulator.
5. Physical Switch run — hardware compatibility evidence.
6. Original FoJ game asset/render/gameplay tests — true porting progress.

Only claim levels that were specifically measured. Neither the build nor
the NRO metadata validator proves proper runtime behavior.

## Security and distribution

No downloaded game, game patches, PSN entitlements, cryptographic material or
copyrighted commercial assets are ever included in this CI workflow. Keep
original game files local.
