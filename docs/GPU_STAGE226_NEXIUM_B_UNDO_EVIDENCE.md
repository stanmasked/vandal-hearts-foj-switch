# Stage226 — prove B-move undo in an actual NeXium synthetic guest

The portable Stage225 tactical engine implements a generated-only
single-movement undo. Stage226 tests **what the interactive Switch research
NRO actually does when the emulator injects controller input**.

The workflow compiles and validates `foj-isometric-research.nro` and
launches it under NeXium with Xvfb and software Vulkan. It captures
four genuine guest screenshots, sending the previously confirmed
default keyboard bindings from NeXium's `controller_config.rs`:

1. Initially hero is at (1,2) and the invented enemy at (6,3).
2. Press Switch **A** (`c`), Right twice, **A** to move hero to (3,2).
   The small mint marker proves B undo is available.
3. Press **B** (`x`). Hero must return to (1,2), with undo marker gone.
4. Press **A**, Right once, **A**. Hero must move to the different
   destination (2,2), with undo once again available.

The verifier requires the synthetic background, blue hero and red enemy
in all frames. It compares blue hero centroids, accepts the initial
position after B within five pixels, rejects static frames, requires
the final alternate position distinct from both previous positions,
checks the mint indicator exactly when undo is available and ensures
the enemy never moves during hero-only actions. Eight generated PNG
fixture tests exercise valid/invalid outcomes.

A passing result supports only **real emulator input processing of the
invented homebrew combat**, not original PS3 rules or execution on a
physical Nintendo Switch. Game data, PS3 assets and COLL files are
never committed to this repository or passed through CI.

Stage225 PR #109 passed all ten workflows and merged with `main`
at `189b1a0fe5772df70090266faff462924114c174`. Stage226 now targets
`main` and requires a fresh independent Python 3.11/3.13, NRO and
NeXium guest evidence run before merging.
