# Stage 185 — reverse COLL controls in NeXium

After the successful Stage 184 six-channel forward test, the same live
COLL homebrew NRO receives four more emulated buttons:

| Switch input | NeXium default key | Expected resulting mode |
| --- | --- | --- |
| L | Q | raw channel 5 (reverse from channel 0) |
| R | E | raw channel 0 again |
| ZL | R | undo the previous ZR zoom |
| DLeft | Left arrow | undo DRight cursor movement |

These keyboard bindings are grounded in NeXium source
`nexium-gui/src/controller_config.rs`. Each button is pressed and
released, and a real emulator window screenshot is captured afterward.

The independent checker `tools/foj_stage185_coll_reverse_check.py`
uses the already proven Stage 184 source-derived C reference matcher
to require the correct rasterized contents for each state. It also
compares each reversed guest frame with the earlier corresponding
forward-action guest frame, rejecting a merely static screen.

Frames and a machine-readable report are included in the Stage 185
GitHub Actions runtime-evidence artifact. Previous Stage 182, 183 and
184 tests remain active and must pass. No PS3 asset is shared; generated
COLL values have no asserted original FoJ terrain or collision meaning.

A passing NeXium guest run is evidence about this synthetic Nintendo
Switch homebrew, not a physical Switch, original PS3 gameplay or a
complete commercial-game port.
