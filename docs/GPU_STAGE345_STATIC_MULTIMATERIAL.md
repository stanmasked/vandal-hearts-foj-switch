# Stage345 — static multi-section, multi-material GPU path

## Scope

FOJRM001 now permits a static mesh with zero bones only when every vertex has zero influences. Rigged meshes retain their existing hierarchy and weight validation; static meshes are not eligible for animation clips. The existing private-actor bridge can consume an unskinned BMODEL conversion without inventing a dummy skeleton.

The local exporter accepts both static and rigged BMODEL sources. Its output remains private original geometry and must not be committed or uploaded to public GitHub.

## Generated-only GPU acceptance

The Stage345 workflow builds the existing private-actor NRO, creates a synthetic two-section static FOJRM001 plus FOJMAT01 mapping to two generated DDS textures, and runs the actual NRO under NeXium. Both material colors must appear in two independent guest screenshots. The NeXium archive digest is checked against the release's published SHA-256 before extraction.

No original PS3 package, BMODEL, material table or original texture is used in public CI. A private-only unskinned source sample with multiple sections and distinct material textures is reserved for a separate owner-only run; its generated FOJRM/FOJMAT/DDS conversion remains private.

## Limits

This stage verifies static geometry, section batching, material selection and GPU texture sampling. It does not prove animated skinning, world-space transforms, the original camera, gameplay integration, physical Nintendo Switch execution or full-game fidelity. The original package and extracted assets remain owner-only in Drive.
