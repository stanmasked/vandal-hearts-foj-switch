# Stage271 — real NeXium negative proof for native transparency guard

**Stacked Draft** above Stage270 [PR #155](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/155), which is already separate from the proven Stage267 positive test.

Stage270's NRO accepts only an orthographic 3-layer scene whose overlapping transparent triangles have strict, fixed depth ordering. Stage271 adds a separate, strictly opt-in negative test target for real guest *rejection* rather than guessing from a blank screenshot.

## Diagnostic-only NRO

```sh
make -f gpu/native_alpha_reject.mk verify
# build/foj-deko3d-native-alpha-rejection-proof.nro
```

The new NRO retains `FOJ_GPU_NATIVE_ALPHA_ORDER_GUARD` and adds
`FOJ_GPU_NEGATIVE_GUEST_RECEIPT`. The latter is intentionally **not**
present in Stage267 or normal Stage270 builds.

On an `FOJ_THREE_ORDER_UNSAFE` result and only then, the NRO attempts
an exclusive-create `fopen(".../foj-native-unsafe-reject.txt","wx")`
before returning from `main`. The file contains exactly:

```text
FOJ_NATIVE_UNSAFE_REJECT_V1 exit=8 pre_gpu=1
```

No original model bytes, filenames, paths, hashes, personal assets,
or gameplay imagery are ever written to that receipt.

Because this diagnostic branch occurs **before** the first
`dkDeviceCreate` or boot journal call, a real guest marker is direct
evidence that the NRO executed the early rejection branch. The text's
`exit=8` is a code-path declaration, not independent measurement of
the emulator's host process exit code.

## Three deliberately unsortable fixtures

The test generator accepts no game content and refuses an existing
output root. It starts from Stage267's invented three-triangle actor
and changes **only** the corresponding Z floats.

| Case | Reason for native rejection |
|---|---|
| `crossing` | The warm triangle crosses violet in Z over the same projected area |
| `reversed` | Violet becomes entirely behind warm, contrary to fixed draw order |
| `coplanar` | Violet and warm overlap at the same depth |

Stage269 host preflight rejects each case by design. To exercise the
native NRO's own guard, Stage271 deliberately installs the rejected
**synthetic** actor in a newly generated NeXium SD root. This is an
explicit negative test, **not** a bypass in private game-data loading.

## Genuine NeXium acceptance

The workflow builds the distinct diagnostic NRO through devkitA64,
runs host-only tests and starts **three separate** NeXium guest
processes. For each it requires:

- Marker absent before guest launch; marker appears afterwards, has
  exact expected bytes and is not a symlink.
- No `foj-boot-*.txt` journal before or after rejection.
- Guest process log and generated-only input receipt.
- Independent final audit checks all three cases, then uploads logs,
  marker copies and JSON report as a GitHub Actions artifact.

A timeout, missing marker, wrong result, or accidental GPU boot
journal causes the workflow to fail. Python-generated test markers in
unit tests are classifier fixtures, *not emulator evidence*.

This establishes only native early refusal of the three fabricated
cases when an actual NeXium runner confirms it. It is **not** polygon
splitting, true order-independent transparency, real PlayStation 3
content rendering, or validation on physical Switch hardware.
