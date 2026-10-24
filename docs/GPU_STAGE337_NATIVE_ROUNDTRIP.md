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
