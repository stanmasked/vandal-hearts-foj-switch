# Stage321 — three-slot texture residency and explicit four-page deferral

## Why three slots matter

Stage320 passed all four native GCC/Clang/sanitizer jobs for stable batches of
synthetic normalized UV triangles, grouped by positive-area geometric page
masks and continuous bilinear page dependency masks. These filter masks may
require four or more distinct decoded BC1 atlas pages, while our research
renderer presently supports only three simultaneously bound texture slots.

It would be incorrect to silently drop the fourth source page or to claim
that a batch with four original textures can be sent to a three-slot pipeline.

## Planner contract

foj_stage321_plan_three_slots accepts Stage320's canonical sorted batches
(maximum 128), validates the masks and contiguous original-index ranges, and
produces one transactionally staged command per batch.

For batches with ONE, TWO or THREE distinct filter-source pages:
- DIRECT command enumerates every required page in increasing page order and
  its actual physical slot (0, 1, or 2).
- Already-resident pages are retained. Missing pages are loaded into the
  lowest numbered empty slot; when all slots are full the highest numbered
  slot whose page is not required by the new batch is replaced.
- Per-command uploaded_page[slot] explicitly distinguishes a load from a
  retained resident page; resident_page[slot] holds the resulting slot state.
- No source page may be silently omitted.

For batches with FOUR or more distinct pages:
- PATCH_REQUIRED command has no bindings and no uploads.
- All three texture slots retain their old state unchanged.
- A later texture patch builder must produce a verified material before this
  batch may be rendered. Stage321 does NOT perform the patch.
- It is expressly forbidden to count PATCH_REQUIRED as a successful draw.

Reports count direct versus deferred batches, actual planned page uploads,
cached binds and unions of direct/deferred source pages.

## Validation and security

Reject malformed canonical Stage320 batches, noncontiguous ranges,
incorrect halo masks, filter masks missing geometry pages, duplicate or
unsorted batch keys, excessive triangle counts, nulls, undersized outputs,
and aliased output or input regions. No output is written on failure.

No original FoJ data, PS3 resource readers, private captures, shader changes,
GPU calls or emulation actions are included. This is a pure, deterministic
CPU research plan. The batch ordering follows Stage320 canonical dependency
ordering; it is not automatically suitable for transparent mesh draw order.

## Native regressions

The test independently replays each of the three GPU slots and checks that
every DIRECT binding really refers to the required resident page. It also
checks that PATCH_REQUIRED neither uploads nor binds anything.

Synthetic fixtures include reuse of page 0 across consecutive draws, cached
1/2/3-page batches, 4-source and 4+-source deferred patches, deterministic
replacement of nonrequired pages, all 128 input batches, consistency of
upload and cache counts, repeated bytewise-deterministic plans, and strict
all-output immutability for invalid inputs and aliases.

Four CI variants: GCC and Clang optimized, GCC UBSan, Clang ASan+UBSan.

## Next step

Stage322 should research generation of small, bounded synthetic RGBA corner
or gutter patches from independently decoded BC1 pages, and bind a new
single verified patched material to the existing three-slot research GPU.
Only after that can one try original FoJ geometry through a **private**
validated import. Hardware Switch results remain unverified.
