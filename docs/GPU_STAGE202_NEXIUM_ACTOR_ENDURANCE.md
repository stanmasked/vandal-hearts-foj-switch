# Stage 202 — generated-only NeXium A/B/A actor endurance

Stage 201 confirmed that the *actual* original-data-capable
`foj-rigged-actor-research.nro` can read invented FOJRM001 and
two compatible BANIM animations from NeXium's `sdmc:` host mapping
and produce ten separately captured, validated guest frames.

Stage 202 extends this to **six consecutive A → B → A cycles**
in the *same* running NeXium guest process. The test does not upload,
run or inspect any user-owned PS3 file.

## Repeatable actual guest workflow

`.github/workflows/stage202-nexium-actor-endurance.yml`:

1. Compiles the existing production actor viewer NRO with devkitA64
   and checks NRO format.
2. Creates an isolated `NEXIUM_DATA_ROOT` with the Stage201
   *generated-only* rig and two generated animation clips. All
   original-game resource paths are rejected: only static Python
   fixture builders are accepted. No original data is packaged.
3. Starts the same actor NRO in NeXium with that virtual SD and
   captures an initial screenshot. Then in each of **six cycles**:
   reset to primary t=0, step A twice while paused (2 × 0.125s),
   capture A pose and a repeated paused frame, request a 0.5-second
   fade to B (4 steps), capture B pose, request the reverse
   0.5-second fade to A (4 steps), capture returned A pose.
4. Captures one host process RSS checkpoint before the cycles and
   one after each cycle; verifies the emulator process is alive for
   every controller event.
5. Fails if any of the 31 expected guest frames is missing, if
   research-source or secondary-clip markers disappear, if the wire
   rig freezes, if paused geometry changes, if reset fails to
   return to the initial pose, or if repeated equivalent states
   diverge by more than the tolerance. Coarse host RSS budget
   guards unexpectedly large memory expansion but does **not**
   prove absence of a leak.
6. Uploads only the **invented** guest screenshots, reproducibility
   checksum of the NeXium release, sanitized RSS records and
   numerical checker receipt.

The user-private PS3 package, BMODEL/BANIM/FOJRM001 exports and
any screenshots rendered from them must NEVER enter public CI, Git,
PR discussions or the test artifact ZIP.

## Validated sequence and limitations

`tools/foj_stage202_nexium_actor_endurance.sh` sends NeXium's
source-verified default keyboard mappings: **X → Switch B reset**,
**E → Switch R paused step** and **Z → Switch Y fade**. The original
actor NRO remains paused unless advanced explicitly. Captured
pixel geometry comes from the *real* NeXium framebuffer, not an
offline fabricated comparison. The independent checker calls Stage
201's accepted dual-BANIM, amber-marker and wireframe pixel
classifier.

`tools/foj_stage202_nexium_actor_endurance_check.py` verifies:
- 6 × 5 screenshots plus one initial frame (31 total);
- equal reset frame for each cycle and stillness during a pause;
- visible A, A→B and B→A motion, each cycle;
- repeatability of corresponding A, B and return-A geometry;
- host RSS checkpoints with a broad safety budget.

`tests/test_foj_stage202_nexium_endurance_check.py` tests those
guardrails with **invented** wire pixel sets, including frozen
motion, drifting pause, divergent repeated cycles, missing/invalid
markers and missing/malformed host RSS observations. These unit
tests do **not** constitute guest evidence; only the NeXium job
can do that.

## Owner-local PS3 evidence remains separate

Stage 200's owner-local SD preparation and nine-frame host-renderer
smoke test can be used offline with the user's own compatible
FOJRM001/BANIM exports. Those images must remain private and may
be compared with independently authorized, timestamp-matched PS3
capture only using the offline Stage196–199 tools.

Passing the Stage 202 generated-data NeXium test confirms
repeatable **research-viewer** guest input, loading, and CPU
animation rendering. It does NOT validate original FoJ PS3 engine
animation math, source actor/clip identity, gameplay, graphical
fidelity, memory-leak absence, or physical Switch execution.
