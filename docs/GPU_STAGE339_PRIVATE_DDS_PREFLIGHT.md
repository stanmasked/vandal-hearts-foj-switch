# Stage339 — safe bridge for owner-held DDS (base mip → GPU plan)

## Scope

Stage337.8 proved a generated texture round-trip on a genuine NeXium
deko3d GPU, and Stage338 proved shader sampling of a Stage336 native-uploaded
256×256 **generated-only** RGBA texture in two actual framebuffer images.
Neither stage renders a copyrighted original game texture.

The Stage339 public module adds a **format-independent, owner-local handoff**
from already recognized classic DDS bytes (Stage332) through CPU level-zero
RGBA8 decode to Stage336's bounded GPU upload allocation/stride plan. It does
not read any files, include game resources, access Google Drive, submit GPU
commands or publish captured frames.

Function `foj_stage339_prepare_private_dds`:
1. Refuses null, zero-sized, overflowed or overlapping input/output/metadata
   address ranges using checked half-open intervals.
2. Strictly inspects DDS header, format, pixel count and the ENTIRE expected
   mip-chain length with Stage332. Supports BGRA32, BGR24, BC1 and BC2,
   never guesses missing flags or truncated source data.
3. Computes Stage336's aligned GPU image and staging budgets from the
   **actual native** `dkImageLayoutGetSize/Alignment` supplied by caller.
   Does not invent or infer device memory requirements.
4. Only after all preflight checks pass, decodes BASE MIP ZERO to caller-owned
   RGBA8 and returns the frozen image info and exact GPU copy plan.
5. Never mutates the returned plan nor any output pixel byte on refusal.
   Caller owns all buffers. No automatic fallback to generated/synthetic data.

Independent synthetic tests build four invented, minimal classic DDS files
with no original artwork or proprietary bytes; validate RGBA conversions,
row pitch in BYTES versus logical PIXELS, staging/image allocation sizes,
malformed and truncated sources, insufficient buffers, wrong GPU layout and
memory overlap. GCC, Clang, Clang ASan+UBSan and devkitA64 cross compiler run
in `.github/workflows/stage339-owner-dds-preflight.yml`.

## Strict privacy and proof separation

- The real owner-provided PS3 PKG and every original DDS are stored only
  in user-owned PRIVATE Google Drive. Public CI never receives source
  images, private hashes, raw filenames, decrypted game data or traces.
- This CPU contract produces **NO evidence** of original texture GPU display.
  Actual owner-private GPU proof will require a separate SD/local runtime
  input path using the Stage336 native upload plus Stage338 real framebuffer
  audit, without uploading any raw game pixels or screenshots publicly.
- The former CPU corpus audit sampled base mip levels of all 1,479 owner DDS
  and found bit-identical independent decoders. Other mip levels are *not*
  independently decoded pixelwise. Do not assert mip-level parity.
- No physical Nintendo Switch testing or full game render is asserted.
- Existing parent Draft PR216/218/219/220/221 must remain unmodified.

Public code is synthetic-tested. Private source proof is a **future
independent gate**, never inferred from a passing host CI workflow.
