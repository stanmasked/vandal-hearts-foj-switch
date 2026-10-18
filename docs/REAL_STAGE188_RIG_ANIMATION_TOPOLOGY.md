# Stage 188 — original BMODEL/BANIM hierarchy-candidate census

This is an **asset-free GitHub implementation** of a read-only
local research step for the existing FoJ PS3 package. It is the first
aggregate comparison across original-game rig and animation
**parent-index topologies**, rather than just testing a single
manually selected model/clip pair.

## What is tested

The already established decoders can read a BMODEL's big-endian
skeleton footer and a BANIM's little-endian track hierarchy.
Stage 188 checks, for every skeleton-bearing BMODEL and every
BANIM accessible from a privately held user-owned debug-style PKG:

- Number of rig bones vs number of animation tracks.
- Ordered parent index of **each** bone vs matching animation track.
- Number of exact-topology candidate model/animation pairs.
- How many candidates are *ambiguous* because multiple original
  resources share one indistinguishable hierarchy.
- How many models and clips have **no** topology candidate.

Rigless models are counted but cannot be paired to bone-track
animation clips. The report also distinguishes weak
*equal-count-only* candidates from stricter
*full-parent-topology* candidates. A multi-root skeleton is valid.
The comparison uses structural data already verified from the
private PS3 archive and does not invent game-engine semantics.

**A matching topology is not a verified model-animation pairing.**
Different characters, objects and clips may have identical bone
hierarchies. The report deliberately does **not** select files for
automatic playback or assert original engine clip/rig binding,
rest-pose correction, retargeting or skin transform accuracy.

## Local-only command

On the owner's computer, using original PKG archive parts:

    python3 -m tools.foj_stage188_private_topology_audit \
      "/path/to/NPEB00148.pkg.zip.001" \
      "/path/to/NPEB00148.pkg.zip.002" \
      > private-topology-aggregate.json

The tool streams resource entries from the local debug PKG / PSARC,
validates each model and clip in bounded memory and prints only
aggregate numbers/booleans and a warning about unverified semantics.
It never writes original model bytes, animation keys, asset paths,
bone-parent arrays, original filenames or hashes to the report.
It does not unpack the game to disk, change any original asset,
perform external network calls or upload copyrighted game material.

Review all locally generated reports before sharing. **Do not upload
the original PS3 PKG, decoded BMODEL, BANIM or other game assets to
GitHub.**

## Safety and evidence

Input upper bounds: at most 2,000 BMODEL and 2,000 BANIM records;
4 MiB per model and 16 MiB per animation. Existing format parsers
enforce parent topology, timestamp, marker, weight and quaternion
checks. Incorrect/truncated records fail instead of silently being
treated as compatible.

GitHub CI exercises only independently invented fixtures, including
two different two-bone hierarchies, duplicate-clip ambiguity,
rigless models, mismatched parent indices, malformed records and a
nested *synthetic* local debug PKG.

This is a reproducible **capability**, not a claim that the user's
protected archive was reopened in GitHub Actions or that original
model/BANIM bindings have been discovered. Confirmed results from
real assets require running this local-only tool privately.
