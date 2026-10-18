"""Stage 193: validate *captured* NeXium frames of the generated-only
animated actor. Synthetic unit fixtures do not constitute guest evidence.
No original PS3 data is accepted or needed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image

SCHEMA = "foj.stage193.generated_animation_guest.v1"
COLORS = {
    "source": (255, 0, 0),
    "clip_a": (0, 255, 255),
    "clip_b": (255, 165, 0),
    "paused": (0, 255, 0),
    "playing": (255, 0, 255),
    "fade": (255, 255, 0),
    "wire": (218, 228, 189),
}
STATES = (
    "initial", "playing", "paused", "paused-later",
    "fade-0", "fade-25", "fade-50", "fade-75", "fade-done",
)
EXPECTED = {
    "initial": ("clip_a", "paused", 0),
    "playing": ("clip_a", "playing", 0),
    "paused": ("clip_a", "paused", 0),
    "paused-later": ("clip_a", "paused", 0),
    "fade-0": ("clip_a", "paused", 1),
    "fade-25": ("clip_a", "paused", 2),
    "fade-50": ("clip_a", "paused", 3),
    "fade-75": ("clip_a", "paused", 4),
    "fade-done": ("clip_b", "paused", 0),
}


def near(pixel, target, tolerance=24):
    return all(abs(int(pixel[i]) - target[i]) <= tolerance for i in range(3))


def summarize(path: Path):
    with Image.open(path) as source:
        img = source.convert("RGB")
    if img.width < 640 or img.height < 400:
        raise ValueError("Guest screenshot too small")
    # Keep only real content markers (large saturated 52x52 blocks), not
    # accidental text, antialiasing, emulator chrome, or tiny noise.
    counts = {name: 0 for name in COLORS}
    wire = set()
    for y in range(img.height):
        for x in range(img.width):
            px = img.getpixel((x, y))
            if y < img.height * .23:
                for name, color in COLORS.items():
                    if name != "wire" and near(px, color):
                        counts[name] += 1
            elif img.width * .18 < x < img.width * .82 and y < img.height * .9:
                if near(px, COLORS["wire"], 16):
                    wire.add((x, y))
    if counts["source"] < 300 or len(wire) < 70:
        raise ValueError("Synthetic source marker or deformed wireframe absent")
    return img.size, counts, wire


def verify(directory: Path):
    frames = {name: summarize(directory / f"anim-{name}.png") for name in STATES}
    sizes = {frames[name][0] for name in STATES}
    if len(sizes) != 1:
        raise ValueError("Screenshot dimensions changed across guest states")
    for name, (clip, mode, progress) in EXPECTED.items():
        counts = frames[name][1]
        other_clip = "clip_a" if clip == "clip_b" else "clip_b"
        other_mode = "paused" if mode == "playing" else "playing"
        if (counts[clip] < 600 or counts[other_clip] > 200 or
                counts[mode] < 600 or counts[other_mode] > 200):
            raise ValueError(f"Wrong active clip or pause marker: {name}")
        # Four 40x30 yellow step blocks in addition to one 52x52
        # incoming-clip marker. Check increments, not exact pixel colors.
        yellow = counts["fade"]
        if progress == 0 and yellow > 250:
            raise ValueError(f"Unexpected crossfade marker in {name}")
        if progress:
            low = 2100 + 950 * (progress - 1)
            high = 3700 + 1450 * (progress - 1)
            if not low < yellow < high:
                raise ValueError(f"Wrong crossfade progress in {name}: {yellow}")

    wires = {name: frames[name][2] for name in STATES}
    def difference(a, b):
        return len(wires[a] ^ wires[b])

    if difference("initial", "playing") < 70:
        raise ValueError("Play did not produce visible skinned motion")
    if difference("paused", "paused-later") > 30:
        raise ValueError("Paused clip changed without guest input")
    if difference("initial", "fade-0") > 30:
        raise ValueError("Crossfade had a visible jump at zero weight")
    for a, b in (
        ("fade-0", "fade-25"),
        ("fade-25", "fade-50"),
        ("fade-50", "fade-75"),
        ("fade-75", "fade-done"),
        ("initial", "fade-done"),
    ):
        if difference(a, b) < 50:
            raise ValueError(f"Skinning frozen across {a} / {b}")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "scope": "one_generated_only_native_NRO",
        "states": list(STATES),
        "guest_frame_dimensions": list(next(iter(sizes))),
        "wire_pixels_at_start": len(wires["initial"]),
        "changed_wire_pixels_playing": difference("initial", "playing"),
        "paused_stillness_delta": difference("paused", "paused-later"),
        "zero_weight_fade_delta": difference("initial", "fade-0"),
        "fade_transition_delta": [
            difference(a, b) for a, b in (
                ("fade-0", "fade-25"), ("fade-25", "fade-50"),
                ("fade-50", "fade-75"), ("fade-75", "fade-done")
            )
        ],
        "original_ps3_resources_used": False,
        "original_ps3_blend_rules_verified": False,
        "physical_switch_executed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.evidence)
        with args.report.open("x", encoding="utf-8") as out:
            json.dump(result, out, indent=2, sort_keys=True)
            out.write("\n")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print("NeXium guest: synthetic animation play, pause and fade verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
