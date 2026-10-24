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
