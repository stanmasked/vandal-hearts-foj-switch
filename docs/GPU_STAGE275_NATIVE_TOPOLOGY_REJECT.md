# GPU Stage275 — Native Unsafe Topology Rejection (Research Only)

Stage274 is proven on its [exact-head CI](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39520233159): the generated-only Switch NRO correctly drew two depth orders and refused a one-byte-transparent rear DDS **before** GPU initialization, with verified NeXium artifacts.

Stage275 is a deliberately separate, stacked Draft PR. It tests a missing invariant: the **dynamic sorter** must also refuse an unsafe projected triangle topology **before GPU initialization**, with a real native witness that cannot be produced by ordinary host fixture generation.

## Native behavior

`gpu/topology_reject_contract.mk` builds a new research NRO with the Stage274 pass-state protection and an *additional opt-in* `FOJ_GPU_TOPOLOGY_NEGATIVE_WITNESS` macro. The production source now separates:

1. Invalid actor batch counts and material ranges — refused without a topology witness.
2. Dynamic sorting returning `FOJ_ALPHA_SORT_INVALID` — refused without a topology witness.
3. `FOJ_ALPHA_SORT_UNSAFE` — refused **before creating a GPU device**, with an exclusive file `foj-native-topology-reject.txt` containing precisely `FOJ_NATIVE_TOPOLOGY_REJECT_V1 pre_gpu=1 unsafe=1` and one LF.
4. Valid sorted geometry — proceeds to the unchanged Stage274 alpha-state and deko3d command path.

This new witness cannot be confused with the existing native `foj-native-rear-alpha-reject.txt`, `foj-native-sort-pass.txt` or `foj-native-alpha-pass.txt`. All real negative guest scripts refuse pre-existing witness files.

## Generated-only test inputs

`tools/foj_stage275_negative_topology_sd.py` creates **two fresh** standalone synthetic SD roots, using the prior public Stage271 negative fixtures:

- `crossing`: the warm triangle crosses another projected triangle in depth.
- `coplanar`: positive-area overlapping triangles share ambiguous depth.

Both are checked against the Python depth-order reference before the root is created, then installed into otherwise unmodified synthetic three-material Scene `original`. Geometry SHA-256 is recorded in each generated manifest, and actual `actor.fojrm` bytes are independently checked **before and after** the real guest execution. No copyrighted PS3 resource is loaded.

The native NeXium driver requires the guest-exclusive unsafe marker, forbids positive draw-order, material-state and rear-DDS witnesses, and forbids any GPU boot journal. A missing marker or prematurely exited guest is a **failure**, not an assumed early rejection.

## CI gate

`.github/workflows/stage275-native-topology-reject.yml` builds the Stage275 opt-in NRO with devkitA64 and two public generated DKSH shaders. Its host job retains the Stage274 C11 material/depth regressions, randomized Stage272 DAG tests, the Stage274 six-module native C integration test and all Stage274 generated-only classifier tests, plus **nine new** Stage275 classifier tests.

The NeXium job requires **five** guest sessions using the *Stage275 NRO*:

1. An original valid overlap scene, with two independently verified RGB frames.
2. A reversed-depth valid overlap scene, with two further RGB frames.
3. An alpha-254 rear DDS invalid scene, with the Stage274 native pre-GPU rejection marker.
4. A crossing-depth invalid actor, with Stage275's own exclusive pre-GPU unsafe topology marker.
5. A coplanar-depth invalid actor with the same exact native unsafe marker, in a separate new SD root.

The unchanged Stage274 final evidence checker verifies the first three cases. The independent `foj_stage275_topology_evidence_check.py` verifies both topology refusals, actor SHA-256 observations, absence of contradictory GPU/success markers, plus the original valid positive GPU scene.

**A green C11 unit test is not native GPU proof.** Stage275 is only complete after exact-head devkitA64 and actual NeXium CI succeed and both archives are reviewed. Nothing establishes real PS3 gameplay, original material compatibility or physical Nintendo Switch hardware behavior.
