#!/usr/bin/env python3
"""Stage 212: owner-private consolidated image + 2D motion evidence gate.

No network, no source assets, images, original frames, SHA256 values or
operator filenames are placed in the report. It checks that the SAME
private Stage199 observations pass Stage210 geometry and Stage211 image
binding. A positive diagnostic is NEVER proof of real PS3 playback.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.foj_stage199_private_multiwindow import _read as read_windows
from tools.foj_stage210_multisequence_motion import evaluate as motion_audit
from tools.foj_stage211_private_multisequence_image_binding import (
    read_configuration,verify as image_audit
)
from tools.foj_stage196_private_pose_observations import rejected

SCHEMA="foj.stage212.private_joint_image_motion_audit.v1"
POSITIVE_MOTION="tentative_operator_declared_multisequence_coherence_only"
VALID_IMAGES="source_and_research_images_locally_bound_only"


def review(observations,bindings):
    # Stage210 ensures per-frame schema, non-collinearity, manual clock
    # consistency and distinct normalized 2D movement hypotheses.
    # Stage211 validates actual owner-local source PNG/PPM bytes against
    # their own manifests and refuses cross-window image replays.
    image=image_audit(observations,bindings)
    motion=motion_audit(observations)
    if image["windows_verified"]!=motion["windows_evaluated"]:
        raise rejected()
    # Stage211 checks original bytes again, but motion_audit uses the
    # same immutable in-memory observation snapshot. Re-check image
    # identity after CPU motion computation to narrow replacement races.
    renewed=image_audit(observations,bindings)
    if image!=renewed:
        raise rejected()
    image_ok=image["diagnosis"]==VALID_IMAGES
    motion_ok=motion["diagnosis"]==POSITIVE_MOTION
    declared=(image["operator_declared_distinct_actions"] and
              motion["operator_declared_distinct_actions"] and
              motion["all_source_and_research_captures_operator_declared"])
    if not image_ok:
        status="duplicate_or_invalid_image_window_evidence"
    elif motion["duplicate_normalized_motion_detected"]:
        status="duplicate_normalized_motion_windows"
    elif not declared:
        status="missing_operator_recording_or_action_declaration"
    elif not motion_ok:
        status="unresolved_sequence_geometry_or_timebase"
    else:
        status="tentative_joint_local_2d_consistency_only"

    return {
        "schema":SCHEMA,
        "windows_evaluated":image["windows_verified"],
        "source_png_frames_bound":image["source_png_frames_checked"],
        "research_native_wireframes_bound":image["research_ppm_frames_bound"],
        "image_identity_rechecked_after_motion_analysis":True,
        "cross_window_source_png_reuse_detected":
            not image["source_pngs_distinct_across_windows"],
        "normalized_motion_replay_detected":
            motion["duplicate_normalized_motion_detected"],
        "two_sided_image_binding_passed":image_ok,
        "per_window_articulated_motion_coherence_passed":motion_ok,
        "all_operator_capture_and_action_declarations_present":declared,
        "unresolved_motion_windows":motion["unresolved_sequence_windows"],
        "suspicious_interframe_transitions":
            motion["total_suspicious_motion_intervals"],
        "sampling_clock_warnings":
            motion["total_declared_clock_ratio_warnings"],
        "diagnosis":status,
        "two_sided_content_witnessing_authenticated_as_original_ps3":False,
        "true_window_independence_authenticated":False,
        "original_ps3_gameplay_authenticated":False,
        "original_ps3_skeletal_animation_fidelity_verified":False,
        "source_character_and_clip_correspondence_verified":False,
        "real_ps3_animation_timing_verified":False,
        "raw_images_coordinates_hashes_or_private_paths_exported":False,
        "warning":(
            "Passing separate local image-content and 2D-motion checks "
            "only demonstrates internal consistency of owner-supplied "
            "annotations and images. It cannot authenticate PS3 gameplay, "
            "source actor, clip, camera, bone math, capture independence "
            "or original animation fidelity."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",required=True,type=Path)
    parser.add_argument("--bindings",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        record=review(
            read_windows(args.observations),
            read_configuration(args.bindings)
        )
    except (OSError,ValueError,TypeError,IndexError,OverflowError,
            ZeroDivisionError):
        print("Private Stage212 combined motion/image evidence rejected.",
              file=sys.stderr)
        return 2
    print(json.dumps(record,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
