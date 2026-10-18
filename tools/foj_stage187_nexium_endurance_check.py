#!/usr/bin/env python3
"""Stage 187: validate a 48-button, single-NeXium-guest COLL endurance run.

An emulator child must remain alive while it receives *distinct* Y press/
release events. Nine real-window captures, including the initial capture,
must alternate between host-C-matched isometric and heatmap scenes at
known input counts. Host process RSS samples are only a rough guard
against catastrophic growth, not evidence of Switch guest memory behavior.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from tools.foj_stage183_coll_y_frame_check import (
    HEAT_CURSOR, ISO_CURSOR, SYNTHETIC_MARKER,
    _changed_pixels, _count_near, _open, _palette_agreement,
)

SCHEMA = "foj-stage187-nexium-coll-y-endurance-v1"
CHECKPOINTS = (0, 1, 8, 9, 24, 25, 40, 41, 48)
TOGGLE_COUNT = 48
MAX_HOST_RSS_GROWTH_KIB = 512 * 1024


def _read_host_rss(path: Path) -> list[dict[str, int]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) != len(CHECKPOINTS):
            raise ValueError("Missing NeXium process liveness/RSS checkpoints")
        entries = []
        for expected, line in zip(CHECKPOINTS, lines, strict=True):
            fields = line.split("\t")
            if len(fields) != 3:
                raise ValueError("Malformed NeXium RSS checkpoint")
            count, rss, seconds = (int(value) for value in fields)
            if (count != expected or rss <= 0 or rss >= 8 * 1024 * 1024 or
                    seconds <= 0):
                raise ValueError("Invalid NeXium process RSS data")
            entries.append({"toggles": count, "host_rss_kib": rss,
                            "epoch_seconds": seconds})
        if any(b["epoch_seconds"] < a["epoch_seconds"]
               for a, b in zip(entries, entries[1:])):
            raise ValueError("Non-monotonic NeXium liveness timestamps")
        if entries[-1]["epoch_seconds"] - entries[0]["epoch_seconds"] < 8:
            raise ValueError("No credible elapsed duration for 48 guest inputs")
        if (max(entry["host_rss_kib"] for entry in entries)
                - entries[0]["host_rss_kib"] > MAX_HOST_RSS_GROWTH_KIB):
            raise ValueError("Excessive NeXium HOST RSS growth")
        return entries
    except (UnicodeError, OSError) as exc:
        raise ValueError("No verifiable NeXium host RSS evidence") from exc


def verify_endurance(directory: Path) -> dict:
    ref_heat = _open(directory / "ref-coll-heat.png")
    ref_iso = _open(directory / "ref-coll-iso.png")
    if ref_heat.size != (1280, 720) or ref_iso.size != (1280, 720):
        raise ValueError("Generated-only C reference sizes invalid")
    reference_palettes = (Counter(ref_heat.getdata()), Counter(ref_iso.getdata()))
    samples = []
    first_by_mode = {}
    dimensions = None
    for index in CHECKPOINTS:
        image = _open(directory / f"coll-endurance-{index:02d}.png")
        if dimensions is None:
            dimensions = image.size
        if dimensions != image.size:
            raise ValueError("NeXium guest window dimensions changed")
        colors = Counter(image.getdata())
        mode = "isometric" if index % 2 else "heatmap"
        own_palette = reference_palettes[1 if index % 2 else 0]
        other_palette = reference_palettes[0 if index % 2 else 1]
        own = _palette_agreement(colors, own_palette)
        other = _palette_agreement(colors, other_palette)
        source_cursor = ISO_CURSOR if index % 2 else HEAT_CURSOR
        cursor_count = _count_near(colors, source_cursor)
        fallback_count = _count_near(colors, SYNTHETIC_MARKER)
        if (own < 0.40 or own < other + 0.12 or
                cursor_count < 20 or fallback_count < 150):
            raise ValueError(
                f"NeXium COLL mode/color mismatch after {index} toggles"
            )
        if mode not in first_by_mode:
            first_by_mode[mode] = image
        steady_change = _changed_pixels(first_by_mode[mode], image)
        if steady_change > max(5000, image.width * image.height // 50):
            raise ValueError(
                f"NeXium COLL framebuffer drift after {index} toggles"
            )
        samples.append({
            "toggles": index,
            "expected_mode": mode,
            "reference_palette_agreement": round(own, 5),
            "other_mode_palette_agreement": round(other, 5),
            "cursor_pixel_count": cursor_count,
            "synthetic_fallback_pixel_count": fallback_count,
            "changed_pixels_from_first_same_mode": steady_change,
        })

    if (_changed_pixels(first_by_mode["heatmap"],
                        first_by_mode["isometric"]) < 10000):
        raise ValueError("No actual guest visual toggle occurred")

    rss = _read_host_rss(directory / "nexium-host-rss.tsv")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "provenance": "actual-generated-only-nro-guest-window-captures",
        "switch_button": "Y",
        "default_emulator_keyboard_key": "z",
        "button_press_release_events": TOGGLE_COUNT,
        "checkpoint_count": len(CHECKPOINTS),
        "guest_screenshot_dimensions": list(dimensions),
        "checkpoints": samples,
        "host_rss_kib_samples": rss,
        "host_rss_growth_kib": rss[-1]["host_rss_kib"] - rss[0]["host_rss_kib"],
        "host_memory_measurement_not_guest_memory": True,
        "physical_switch_execution_verified": False,
        "physical_switch_gpu_scanout_verified": False,
        "original_foj_gameplay_verified": False,
        "original_ps3_assets_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_endurance(args.evidence)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print("NeXium COLL guest: 48 Y inputs, nine alternating frames and RSS samples verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
