# Stage 199 — multi-window motion timing consensus (private only)

Stages 196–198 introduced geometric, temporal and ambiguity diagnostics
for annotated original-PS3 versus research-viewer landmarks. Stage 199
checks whether a **candidate offset is reproducible across multiple
separately annotated motion windows**, rather than selected from one
potentially repeating animation.

This work is **research tooling**, not extraction or verification of
original FoJ engine pacing, PS3 player capture, model pairing or Switch
visual authenticity.

## Analysis contract

`tools/foj_stage199_private_multiwindow.py` reads 2–4 nested private
Stage 196 observation documents, each satisfying Stage 197's 8–12
ordered frames, exact landmark naming, minimum geometric motion,
bounded timestamps and common comparison interval.

The program calls Stage 197 and Stage 198 for **every window**. It
then computes a constant lag grid shared by all of them. For every
candidate shift, each window contributes its **own training and
holdout residual**, combined by root-mean-square with **equal weight
per window** (not per number of frames). The winning lag is chosen
from training residuals alone.

Safety rules:

- A window that disagrees materially with the other estimated lags
  prevents a tentative common-shift conclusion.
- A cyclic/ambiguous window identified in Stage 198 cannot be
  upgraded merely because other windows produce a clean minimum.
- Alternative **distant** offsets competitive on *both* training and
  holdout data prevent confident interpretation.
- The fit must remain stable when an entire window is excluded
  (leave-one-window-out sensitivity); the positive result is
  downgraded if removing a window changes the chosen lag.
- A source motion must be marked `distinct_actions_operator_declared`
  and both captured series in every window must be marked as
  operator-reported recorded. These statements are **not verified**.
- A search-edge minimum or insufficient combined shape agreement
  is not a successful synchronization diagnosis.

The output classifies the result as `tentative_common_shift`,
`no_clear_common_shift`, `ambiguous_multiwindow`,
`inconsistent_window_offsets` or `unresolved_across_windows`.
A tentative label remains a **hypothesis** about the operator's
annotations, not proof of original PS3 playback timing.

## Offline private usage

Create a blank two-window template, which cannot claim any
observation without explicit operator input:

```sh
mkdir -p local-data/observations
python3 -m tools.foj_stage199_private_multiwindow \
  --init local-data/observations/motion-windows-private.json
```

This intentionally has `motion_independence_declaration` set to
`not_established`, both nested Stage 196 observations blank and
both `capture_recorded` declarations false.

After privately capturing and annotating at least two
**different authorized character motion actions**, populate the
nested `observations` list. A schematic, not an example claiming
actual motion acquisition:

```text
schema: foj.stage199.private_multiwindow_consensus.v1
motion_independence_declaration: distinct_actions_operator_declared
observations:
  - full original Stage 196 JSON with 8–12 frame pairs
  - another full original Stage 196 JSON from a different action
  - optional third/fourth action
```

The program checks literal duplicate windows but **cannot** establish
that visually similar actions are genuinely independent. Do not fake
this operator assertion. Do not upload captures or annotation JSON.

Run the comparison locally:

```sh
python3 -m tools.foj_stage199_private_multiwindow \
  --analyze local-data/observations/motion-windows-private.json \
  --max-shift .2 --step .025 \
  > local-data/observations/motion-consensus-private.json
```

The input accepts at most 512 KiB, rejects paths pointing to symlinks
or non-regular files and duplicates in JSON object keys, and enforces
Stage 197/198 limits on all subreports. No network requests or original
PS3 package parsing occur.

The returned diagnostic is deliberately aggregate-only: it omits
screenshots, image paths, labels, coordinates, user filenames, mesh
content, BANIM keyframes, and capture hashes. **Keep even these
aggregate metrics private**, because they may still describe
owner-held original game resources.

## Synthetic evidence and remaining uncertainty

`tests/test_foj_stage199_private_multiwindow.py` uses only invented
2D landmark motion and verifies common positive/negative/zero offsets,
two/three-window agreement, conflicting windows, cyclic ambiguity,
a corrupted frame, lack of declared independence, duplicated inputs,
malformed times, strict bounds and CLI privacy.

The synthetic tests do not provide independent original PS3 captures.
Even if the operator reports separate actions, shared alias periods
across all windows or perspective changes can still mimic a common
offset. No exact original engine state graph, controller scheduling,
frame pacing, bind convention or identity of BANIM-to-character
association is established.

**Future evidence gate:** independently time-stamped, authorized
PS3 and experimental research captures from *distinct real motions*,
privately reviewed before interpreting any timing agreement.
