#!/usr/bin/env python3
"""Stage 206: render strictly PRIVATE two-sided landmark review PNG images.

The annotations are manual, and both local source PNG identities and
research C-rendered PPM wire proximity must ALREADY check out.
This makes visual review possible, not source-PS3 authenticity or
correct anatomical correspondence. Never upload generated overlays.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import zlib

from tools.foj_stage196_private_pose_observations import (
    align_observations,private_read,rejected
)
from tools.foj_stage203_private_actor_evidence import (
    HEADER,W,H,IMAGE_BYTES,safe_destination
)
from tools.foj_stage204_private_frame_landmarks import (
    inspect_landmarks,nearest_wire_distance,read_bindings,
    read_wire_frame,validate_bindings
)
from tools.foj_stage205_private_source_png import (
    SIGNATURE,png_bytes,png_info,inspect_sources,file_name
)

SCHEMA="foj.stage206.private_two_sided_review.v1"
COLOR=(255,0,215)
DARK=(10,9,18)
DIGITS={
 "0":("111","101","101","101","111"),
 "1":("010","110","010","010","111"),
 "2":("111","001","111","100","111"),
 "3":("111","001","111","001","111"),
 "4":("101","101","111","001","001"),
 "5":("111","100","111","001","111"),
 "6":("111","100","111","101","111"),
 "7":("111","001","010","010","010"),
 "8":("111","101","111","101","111"),
 "9":("111","101","111","001","111"),
}


def png_image(raw:bytes):
    """Decode validated 8-bit noninterlaced PNG RGB/RGBA into RGB.

    Implements PNG scanline filter types 0..4, without Pillow, and
    composites RGBA onto white. CRC, bounded stream and chunk layout
    are checked by stage205 png_info first.
    """
    meta=png_info(raw)
    width,height=meta["width"],meta["height"]
    at=len(SIGNATURE)
    pieces=[]
    channels=None
    while at<len(raw):
        n=struct.unpack_from(">I",raw,at)[0]
        kind=raw[at+4:at+8]
        if kind==b"IHDR":
            channels=3 if raw[at+8+9]==2 else 4
        elif kind==b"IDAT":
            pieces.append(raw[at+8:at+8+n])
        at+=n+12
    if channels not in (3,4):
        raise rejected()
    decompressed=zlib.decompress(b"".join(pieces))
    stride=width*channels
    previous=bytearray(stride)
    rgb=bytearray(width*height*3)
    for y in range(height):
        begin=y*(stride+1)
        filtr=decompressed[begin]
        row=bytearray(decompressed[begin+1:begin+1+stride])
        for i in range(stride):
            left=row[i-channels] if i>=channels else 0
            up=previous[i]
            upper_left=previous[i-channels] if i>=channels else 0
            if filtr==1:
                predictor=left
            elif filtr==2:
                predictor=up
            elif filtr==3:
                predictor=(left+up)//2
            elif filtr==4:
                p=left+up-upper_left
                a,b,c=abs(p-left),abs(p-up),abs(p-upper_left)
                predictor=(left if a<=b and a<=c else
                           up if b<=c else upper_left)
            elif filtr==0:
                predictor=0
            else:
                raise rejected()
            row[i]=(row[i]+predictor)&255
        previous=row
        dst=y*width*3
        if channels==3:
            rgb[dst:dst+stride]=row
        else:
            for x in range(width):
                a=row[x*4+3]
                for channel in range(3):
                    component=row[x*4+channel]
                    rgb[dst+x*3+channel]=(component*a+255*(255-a)+127)//255
    return width,height,rgb


def ppm_image(raw:bytes):
    if len(raw)!=IMAGE_BYTES or not raw.startswith(HEADER):
        raise rejected()
    return W,H,bytearray(raw[len(HEADER):])


def put(rgb:bytearray,w:int,h:int,x:int,y:int,color):
    if 0<=x<w and 0<=y<h:
        offset=(y*w+x)*3
        rgb[offset:offset+3]=bytes(color)


def mark(rgb:bytearray,w:int,h:int,xy,number:int):
    if type(number) is not int or not 1<=number<=32:
        raise rejected()
    x=round(xy[0]*(w-1))
    y=round(xy[1]*(h-1))
    if not (0<=x<w and 0<=y<h):
        raise rejected()
    # Outlined cross and small numbered tag, colored identically across
    # original and research frames. Never invent points in production.
    for length,color in ((9,DARK),(7,COLOR)):
        for d in range(-length,length+1):
            put(rgb,w,h,x+d,y,color)
            put(rgb,w,h,x,y+d,color)
    label=str(number)
    box_x=min(max(0,x+11),max(0,w-(len(label)*5+4)))
    box_y=min(max(0,y-8),max(0,h-9))
    for py in range(9):
        for px in range(len(label)*5+4):
            put(rgb,w,h,box_x+px,box_y+py,DARK)
    for offset,digit in enumerate(label):
        for iy,row in enumerate(DIGITS[digit]):
            for ix,value in enumerate(row):
                if value=="1":
                    put(rgb,w,h,box_x+2+offset*5+ix,box_y+2+iy,COLOR)


def png_chunk(kind,payload):
    return (struct.pack(">I",len(payload))+kind+payload+
            struct.pack(">I",zlib.crc32(kind+payload)&0xffffffff))


def rgb_png(w,h,rgb):
    if len(rgb)!=w*h*3:
        raise rejected()
    raw=b"".join(
        b"\x00"+rgb[(y*w)*3:((y+1)*w)*3]
        for y in range(h)
    )
    return (
        SIGNATURE+
        png_chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+
        png_chunk(b"IDAT",zlib.compress(raw,6))+
        png_chunk(b"IEND",b"")
    )


def exclusive_write(path:Path,data:bytes):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(data)


def create_review(observations,source_manifest,source_dir,
                  bindings,private_research_dir,output_root):
    safe_destination(output_root)
    # Require both independent upstream checks before writing anything.
    source=inspect_sources(observations,source_manifest,source_dir)
    research=inspect_landmarks(
        observations,bindings,private_research_dir
    )
    if source["source_png_frames_locally_bound"]!=research[
        "stage203_named_frames_bound"
    ]:
        raise rejected()
    validated=align_observations(observations)
    labels=validate_bindings(bindings,len(observations["frames"]))
    rows=observations["frames"]
    # Source side must be exactly the private PNGs validated by hashes.
    # Research side must come from exact locally-rendered C output.
    names=sorted(point["id"] for point in rows[0]["landmarks"])
    results=[]
    old_umask=os.umask(0o077)
    created=False
    try:
        output_root.mkdir(mode=0o700)
        created=True
        for i,(row,label) in enumerate(zip(rows,labels,strict=True)):
            src_data=png_bytes(source_dir/file_name(i))
            if hashlib.sha256(src_data).hexdigest()!=source_manifest["frames"][i]["sha256"]:
                raise rejected()
            original=png_image(src_data)
            research_pixels=read_wire_frame(
                private_research_dir/(label+".ppm")
            )
            experimental=ppm_image(HEADER+research_pixels)
            for point in row["landmarks"]:
                nearest_wire_distance(research_pixels,point["experimental_xy"])
            marked={item["id"]:item for item in row["landmarks"]}
            for j,name in enumerate(names,1):
                point=marked[name]
                mark(original[2],original[0],original[1],
                     point["ps3_xy"],j)
                mark(experimental[2],experimental[0],experimental[1],
                     point["experimental_xy"],j)
            exclusive_write(
                output_root/f"source_{i:03d}_REVIEW_PRIVATE.png",
                rgb_png(*original)
            )
            exclusive_write(
                output_root/f"research_{i:03d}_REVIEW_PRIVATE.png",
                rgb_png(*experimental)
            )
            results.append({
                "index":i,"landmark_count":len(names),
                "source_resolution":[original[0],original[1]],
                "research_resolution":[W,H],
            })
        # Revalidate image and research-frame inputs after rendering to
        # reject replacements during the local offline process.
        inspect_sources(observations,source_manifest,source_dir)
        inspect_landmarks(observations,bindings,private_research_dir)
        # Source landmark ID/numerical label key is private; don't print it.
        exclusive_write(
            output_root/"PRIVATE_landmark_number_key.json",
            (json.dumps({"names_by_number":names},
                       ensure_ascii=False,indent=2)+"\n").encode("utf-8")
        )
        record={
            "schema":SCHEMA,
            "review_pair_count":len(rows),
            "overlays_generated":2*len(rows),
            "manually_reviewed_by_human":False,
            "source_png_bytes_matched_private_manifest":True,
            "research_points_matched_native_wireframes":True,
            "source_ps3_gameplay_authenticated":False,
            "correct_anatomical_landmarks_confirmed":False,
            "camera_or_original_animation_fidelity_verified":False,
            "private_original_image_pixels_or_hashes_in_receipt":False,
            "do_not_upload_overlays_or_number_key":True,
        }
        exclusive_write(
            output_root/"PRIVATE_review_status.json",
            (json.dumps(record,indent=2,sort_keys=True)+"\n").encode()
        )
        return record
    except BaseException:
        if created:
            import shutil
            shutil.rmtree(output_root)
        raise
    finally:
        os.umask(old_umask)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",required=True,type=Path)
    parser.add_argument("--source-manifest",required=True,type=Path)
    parser.add_argument("--source-dir",required=True,type=Path)
    parser.add_argument("--research-bindings",required=True,type=Path)
    parser.add_argument("--research-dir",required=True,type=Path)
    parser.add_argument("--output-root",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        result=create_review(
            private_read(args.observations),
            private_read(args.source_manifest),
            args.source_dir,
            read_bindings(args.research_bindings),
            args.research_dir,
            args.output_root
        )
        print(json.dumps(result,sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,IndexError,OverflowError,
            zlib.error,MemoryError):
        print("Private Stage206 annotated review rejected.",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
