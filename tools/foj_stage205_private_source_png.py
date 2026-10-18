#!/usr/bin/env python3
"""Stage205: bind private manually annotated PS3 frames to exact local PNG bytes.

This tool NEVER authenticates original-game footage or automatically
identifies anatomical joints. It NEVER uploads an image or image digest.
Run only on the owner's computer, not with real assets in public CI.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import zlib
from tools.foj_stage196_private_pose_observations import (
    align_observations, only_keys, private_read, rejected,
)

SCHEMA="foj.stage205.private_source_png_binding.v1"
REPORT="foj.stage205.private_source_png_audit.v1"
SIGNATURE=b"\x89PNG\r\n\x1a\n"
MAX_FILE=12*1024*1024
MAX_CHUNKS=128
MAX_PIXELS=8_000_000


def file_name(i):
    return f"frame_{i:03d}.png"


def png_bytes(path):
    fd=-1
    try:
        fd=os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or not 64<=st.st_size<=MAX_FILE:
            raise rejected()
        with os.fdopen(fd,"rb") as stream:
            fd=-1
            raw=stream.read(MAX_FILE+1)
        if len(raw)!=st.st_size:
            raise rejected()
        return raw
    except (OSError,ValueError):
        raise rejected() from None
    finally:
        if fd>=0:
            os.close(fd)


def png_info(raw):
    if type(raw) is not bytes or len(raw)<64 or not raw.startswith(SIGNATURE):
        raise rejected()
    offset=len(SIGNATURE)
    idat=bytearray()
    ihdr=False
    have_data=False
    after_data=False
    ended=False
    width=height=channels=0
    chunks=0
    while offset<len(raw):
        if chunks>=MAX_CHUNKS or offset+12>len(raw):
            raise rejected()
        length=struct.unpack_from(">I",raw,offset)[0]
        name=raw[offset+4:offset+8]
        if length>MAX_FILE or offset+12+length>len(raw):
            raise rejected()
        value=raw[offset+8:offset+8+length]
        crc=struct.unpack_from(">I",raw,offset+8+length)[0]
        if zlib.crc32(name+value)&0xffffffff!=crc:
            raise rejected()
        offset+=12+length
        chunks+=1
        if any(not(65<=x<=90 or 97<=x<=122) for x in name):
            raise rejected()
        if not ihdr and name!=b"IHDR":
            raise rejected()
        if name==b"IHDR":
            if ihdr or chunks!=1 or length!=13:
                raise rejected()
            width,height,depth,color,comp,filt,interlace=struct.unpack(
                ">IIBBBBB",value
            )
            if (not 32<=width<=4096 or not 32<=height<=4096 or
                width*height>MAX_PIXELS or depth!=8 or
                color not in (2,6) or comp!=0 or filt!=0 or interlace!=0):
                raise rejected()
            channels=3 if color==2 else 4
            ihdr=True
        elif name==b"IDAT":
            if ended or after_data or length==0:
                raise rejected()
            have_data=True
            idat.extend(value)
            if len(idat)>MAX_FILE:
                raise rejected()
        elif name==b"IEND":
            if length!=0 or not have_data or ended or offset!=len(raw):
                raise rejected()
            ended=True
            break
        else:
            if name[0]&32==0:
                raise rejected()
            if have_data:
                after_data=True
    if not (ihdr and have_data and ended):
        raise rejected()
    expected=height*(1+width*channels)
    stream=zlib.decompressobj()
    try:
        data=stream.decompress(bytes(idat),expected+1)
    except zlib.error:
        raise rejected() from None
    if (len(data)!=expected or not stream.eof or
        stream.unused_data or stream.unconsumed_tail):
        raise rejected()
    stride=1+width*channels
    if any(data[i*stride]>4 for i in range(height)):
        raise rejected()
    return {"width":width,"height":height,
            "sha256":hashlib.sha256(raw).hexdigest()}


def image_info(folder,path):
    if not folder.is_dir() or folder.is_symlink():
        raise rejected()
    return png_info(png_bytes(folder/path))


def prepare(observations,folder):
    align_observations(observations)
    frames=[]
    seen=set()
    for i,row in enumerate(observations["frames"]):
        info=image_info(folder,file_name(i))
        if info["sha256"] in seen:
            raise rejected()
        seen.add(info["sha256"])
        frames.append({
            "file":file_name(i),
            "ps3_time_seconds":row["ps3_time_seconds"],
            **info,
        })
    return {"schema":SCHEMA,
            "source_kind":"operator_claimed_original_ps3_not_authenticated",
            "frames":frames}


def inspect_sources(observations,manifest,folder):
    aligned=align_observations(observations)
    only_keys(manifest,{"schema","source_kind","frames"})
    if (manifest["schema"]!=SCHEMA or
        manifest["source_kind"]!=
        "operator_claimed_original_ps3_not_authenticated" or
        type(manifest["frames"]) is not list or
        len(manifest["frames"])!=len(observations["frames"])):
        raise rejected()
    seen=set()
    for i,(entry,row) in enumerate(zip(
        manifest["frames"],observations["frames"],strict=True
    )):
        only_keys(entry,{"file","ps3_time_seconds","width","height","sha256"})
        if (entry["file"]!=file_name(i) or
            type(entry["ps3_time_seconds"]) not in (int,float) or
            abs(entry["ps3_time_seconds"]-row["ps3_time_seconds"])>1e-6):
            raise rejected()
        actual=image_info(folder,file_name(i))
        if (type(entry["width"]) is not int or
            type(entry["height"]) is not int or
            type(entry["sha256"]) is not str or
            any(entry[key]!=actual[key] for key in
                ("width","height","sha256")) or
            entry["sha256"] in seen):
            raise rejected()
        seen.add(entry["sha256"])
    return {
        "schema":REPORT,
        "source_png_frames_locally_bound":len(seen),
        "landmarks_per_frame":aligned["landmarks_per_frame"],
        "png_bytes_dimensions_timestamps_match_private_manifest":True,
        "operator_claimed_source_recorded":
            observations["ps3_observation"]["capture_recorded"],
        "original_ps3_gameplay_authenticated":False,
        "capture_timestamps_independently_verified":False,
        "anatomical_correspondences_verified":False,
        "original_ps3_animation_accuracy_verified":False,
        "original_png_content_or_digests_in_report":False,
        "warning":(
            "Local PNG identity is verified against an owner-created manifest. "
            "This does not prove capture provenance, actual PS3 hardware, "
            "time synchronization or correctly labelled joints."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare",action="store_true")
    mode.add_argument("--verify",action="store_true")
    parser.add_argument("--observations",required=True,type=Path)
    parser.add_argument("--capture-dir",required=True,type=Path)
    parser.add_argument("--manifest",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        doc=private_read(args.observations)
        if args.prepare:
            manifest=prepare(doc,args.capture_dir)
            fd=os.open(args.manifest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"w",encoding="utf-8") as output:
                json.dump(manifest,output,indent=2,sort_keys=True)
                output.write("\n")
            report={"schema":SCHEMA,
                    "frames_manifested":len(manifest["frames"]),
                    "original_ps3_gameplay_authenticated":False}
        else:
            report=inspect_sources(
                doc,private_read(args.manifest),args.capture_dir
            )
        print(json.dumps(report,sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,IndexError,OverflowError):
        print("Private Stage205 source PNG check rejected.",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
