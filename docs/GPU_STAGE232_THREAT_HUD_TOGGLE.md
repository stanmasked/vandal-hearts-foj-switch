# Stage232 — hide or reveal synthetic movement danger preview

The generated 8×6 homebrew now has an optional, purely visual
**threat-preview display**. This does not reproduce any original PS3
game mechanic and uses no private PS3 data.

## Control

While running the isometric research NRO, click the **right stick**
(`HidNpadButton_StickR`, NeXium's default keyboard `g`) to hide or
reveal all per-cell teal safe and orange incoming-damage hints.
The default is **visible** so existing behavior and previous NeXium
screenshots are unchanged. The console NRO supports the same control
and prints its current ON/OFF state next to the help instructions.

The feature is *only a presentation setting*:

- A selected hero can still inspect routes and move/attack/guard.
- Switching danger hints off cannot change actual enemy turns, path
  legality, HP forecasts or the winning condition.
- The deterministic controller battle replay does not record this
  display-only switch, just as it excludes optional COLL diagnostic
  channel toggles.
- COLL channel samples, movement replay bar, ZR guard mark and other
  diagnostic overlays are completely unaffected.

## Compatibility and verification

The original `foj_iso_render_battle` signature is preserved as a
wrapper that always displays risk hints. New
`foj_iso_render_battle_options(..., show_threat_preview)` allows the
research UI to choose visibility without affecting C tests or old
callers. An additional generated-only isometric regression asserts
that the safe marker is present by default, disappears when OFF,
reappears when toggled ON, and that both draw variants leave the
entire `FojBattle` state byte-for-byte unchanged.

Stage231 PR #115 passed independent host, NeXium and COLL checks
and merged into `main` as `b0806177d6c059f955db547c81451640445fbd08`.
Stage232 now targets `main` and requires a fresh full host,
devkitA64, isometric-render and NeXium CI matrix before merging.

Everything remains a synthetic homebrew research prototype, not the
original Vandal Hearts: Flames of Judgment battle implementation.
