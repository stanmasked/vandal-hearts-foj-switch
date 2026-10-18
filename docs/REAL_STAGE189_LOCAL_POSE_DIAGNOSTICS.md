# Stage 189 — local BMODEL bind vs BANIM sample diagnostics

This stage extends Stage 188's **exact parent-topology** candidate census
with two **experimental numerical measurements**, sampled at t = 0 seconds.
It is NOT automatic original model/animation matching.

## Diagnostics

The offline analyzer loads BMODEL rig bind-like *local* transforms and
retained BANIM keyframes using the previously verified original FoJ
binary readers. A candidate is compared **only when the full ordered
parent hierarchy matches**. For each structural candidate pair it samples
the BANIM *local* pose at t=0, respecting the source clip's track-specific
first/last-key clamping and quaternion shortest-path interpolation.

Two source-space measurements are computed:

1. **Translation RMS:** square root of the mean squared Euclidean
   difference in the per-bone local XYZ translation vectors.
   The original game's coordinate scales and bind-pose application
   are not confirmed.
2. **Quaternion dissimilarity:** average over bones of
   1 - abs(normalized_quaternion_dot). Opposite-sign quaternions
   represent the same orientation, so their metric is zero.

The JSON report contains cumulative **counts** of candidate pairs
under fixed translation cutoffs 0.01 / 0.1 / 1.0 / 10.0 in **unverified
source units**, and rotation cutoffs 0.0001 / 0.01 / 0.1. It also counts
pairs below both translation 1.0 and rotation 0.01, and records simple
global minima and maxima. Source bytes, filenames, directory names,
full bone parents, quaternion vectors and transforms are not exported.

**Interpretation is strictly provisional.** Even a perfect numerical
match could be an unrelated model with a shared hierarchy and a
generic idle pose; different coordinate frames, reference/rest poses
and retargeting would also make a correct game pairing differ greatly.
Therefore the measurements must NOT be used to exclude pairs, label
actors, choose motion assets, infer gameplay behaviour or claim engine
retargeting has been recovered. The report includes explicit
false evidence flags.

## Run against your own private game archive

    python3 -m tools.foj_stage189_local_pose_aggregate \
      "/path/to/NPEB00148.pkg.zip.001" \
      "/path/to/NPEB00148.pkg.zip.002" \
      > private-local-pose-aggregate.json

The PS3 ZIP parts and underlying cdata.psarc stay on the user's
computer. The tool reuses bounded stream readers: at most 2,000 BMODEL,
2,000 BANIM, 4 MiB/model, 16 MiB/clip and **250,000 pose comparisons**.
One BANIM's keyframes are held in memory at a time. No extraction,
upload, decrypted executable, game keys, original vertex data or
renderable clip can be published.

GitHub Actions exercises **nine generated-only tests** including
different hierarchies, multi-root rigs, quaternion sign equivalence,
nonzero rotation and offset, absence of compatible candidates,
malformed assets, bounded workload, legal zero-duration clips and a
fully synthetic debug PKG. GitHub does **not** scan the original
605 MB user-owned package: only local execution could produce
measurements from real FoJ resources.

## Next evidence gate

Validate possible candidate bindings **only** against independent
original-game metadata or an authorized observation of original
runtime behaviour, not the numerical score alone. It remains unknown
how the PS3 engine composes global bone matrices and inverse bind
matrices. Neither a playable FoJ Switch port nor physical console
display has been established by this offline analysis.
