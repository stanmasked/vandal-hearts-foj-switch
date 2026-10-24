# Stage337 — generated-only native GPU upload/readback

**Purpose:** close the narrow gate between Stage336's *recorded* transfer and
proof of GPU execution. No original PS3 package, DDS, extracted texture,
private capture, member name, game code or proprietary pixel data is used.

## The test

A standalone devkitA64 NRO generates a unique 74 × 81 RGBA8 pattern with
varying alpha. It calls the unchanged Stage336 SDK-native adapter with a
64-byte row alignment, records and submits `dkCmdBufCopyBufferToImage`,
waits for the GPU queue, independently records `dkCmdBufCopyImageToBuffer`,
waits again, and compares all 5,994 RGBA pixels byte-for-byte. Any failed
allocation, GPU command list, guest queue state, or pixel mismatch rejects the
proof. The guest opens its success receipt **exclusively** and only after the
guest-side GPU readback and comparison. A stale or forged receipt is refused.

Stage337 deliberately uses two separate queue submissions (upload then
readback), plus synchronization. It does not claim zero-copy performance or
production throughput and must not be generalized to unsynchronized pipelines.

## Evidence gate

CI independently tests strict receipt parsing, builds and validates the NRO
using devkitA64 and runs the new NRO inside NeXium. The guest writes only a
fixed generated-data receipt. Public CI exports only the structured
allowlisted aggregate result and the downloaded emulator archive digest.
Raw guest logs are never uploaded; failure is not treated as success.

**Scope:** Stage337 verifies a *native GPU image transfer roundtrip* if and only
if the NeXium job passes. It does not draw the image to a framebuffer, capture
an onscreen texture, or verify the Nintendo Switch physical console. A fresh,
independent rendered-frame gate is needed before using original DDS. The
owner-local original source and its CPU-parity reports remain in private Drive.

## Stage337.1 — failure-only bounded execution telemetry

The initial run on `c5ef61a6` confirmed a valid NRO and evidence parser but
**failed** its real NeXium job: no native readback receipt appeared during 150
seconds; the driver reported a timeout. The first run cannot distinguish
emulator startup, device creation, upload submission, GPU idle wait or actual
pixel comparison. Do not claim the texture reached or failed a particular GPU
phase without fresh execution evidence.

Stage337.1 therefore adds a separate, best-effort, exclusive synthetic numeric
progress file (`FOJ337P1 stage=NN`) with a cap of 24 records and flushes between
phases. Numeric checkpoints are recorded before and after device/queue
creation, recording upload, waiting for GPU completion, readback, and comparing
RGBA pixels. On failure the driver prints **only** the validated final
2-digit phase, or `none` for absent or malformed evidence. Original/raw guest
logs remain unpublished, and the progress file is never a success condition or
public artifact. New unit fixtures assert that progress markers cannot be
accepted by the receipt checker.

The follow-up GitHub run is the only authority for the diagnosis. This change
does not increase pixel/texture scope or modify Stage336's buffer allocation.


## Stage337.2 diagnostic correction

A failure must preserve the last reached stage, rather than append a generic
failure code that hides it. The guest now emits stage 13 only after a successful
byte-for-byte readback. On any failure, the last record remains the last
completed milestone. A numeric progress record is diagnostic only and never
accepted as a GPU success receipt.


## Stage337.3 — real GPU readback failure classification

After the second queue wait, a queue-error state emits diagnostic stage 80.
A healthy queue reaches stage 12 *before* comparing pixels. Any mismatch
causes a strict refusal with one synthetic-only numeric diagnostic code:
81 means all active returned bytes still equal the 0xA5 initialization
pattern; 82 means only alpha differs; 83 means only RGB differs; 84 means
mixed RGBA differences. A fully matching buffer alone reaches stage 13 and
may generate the exclusive success receipt. Stages 80–84 are **never**
accepted as GPU proof, and no raw image, private game assets or guest logs
are exported. These diagnostics isolate the next possible GPU cache/fence or
copy-layout issue without changing the previously verified upload contract.


## Stage337.4 — explicit GPU-cache visibility fence

Previous exact-head NeXium run 40049012729 reported stage 84 after two GPU
queue waits, with a healthy GPU queue and mixed RGB/alpha mismatch. This is
not a successful GPU image readback. The returned content was not wholly
the unchanged 0xA5 CPU initialization sentinel.

The readback DkMemBlock is DkMemBlockFlags_CpuUncached but
DkMemBlockFlags_GpuCached. The documented SDK GPU-to-CPU coherency contract
calls for dkQueueSignalFence(queue, &fence, true) and
 dkQueueWaitFence(queue, &fence) to force dirty GPU cache lines to RAM before
CPU reads. Stage337.4 performs that explicit fence after the second wait-idle
and before exact RGBA comparison. Stage 85 isolates any queue error during
this new flush, with all diagnostic stages still rejected by the success
receipt parser. Results must be judged exclusively from the fresh NeXium
runtime check; neither compilation nor a stage code is success proof.
