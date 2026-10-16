# Nintendo Switch homebrew bring-up

This phase verifies **compiler/toolchain integration only**, using generated
console text and no game files. The NRO is **not** the PS3 game.

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

- A: records an A button press.
- B: records a B button press.
- Plus: exits to the homebrew loader.

These input events are solely an interactive smoke test. They are **not**
Flames of Judgment's original menus, save system, tactics rules, renderer,
PS3 executable, or game assets.

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
