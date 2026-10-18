"""Independent geometric reference for PRIVATE stage195 pose envelope.

Unlike production C's row-major inverse-bind matrix multiplication, this
reference composes quaternion transforms and evaluates vertex positions
directly via quaternion conjugation. These are RESEARCH conventions, not
verified original FoJ PS3 engine coordinates. Never log raw source points.
"""
from __future__ import annotations

import math


def multiply(a, b):
    x,y,z,w=a
    u,v,t,s=b
    return (
        w*u+x*s+y*t-z*v,
        w*v-x*t+y*s+z*u,
        w*t+x*v-y*u+z*s,
        w*s-x*u-y*v-z*t,
    )


def rotated(q,vector):
    norm=math.sqrt(sum(x*x for x in q))
    if not math.isfinite(norm) or norm<.001:
        raise ValueError("Nonfinite local pose rotation")
    unit=tuple(x/norm for x in q)
    inverse=(-unit[0],-unit[1],-unit[2],unit[3])
    return multiply(multiply(unit,(*vector,0.)),inverse)[:3]


def sum3(a,b):
    return tuple(x+y for x,y in zip(a,b,strict=True))


def worlds(bones):
    world=[]
    for index,(parent,q,translation) in enumerate(bones):
        if parent< -1 or parent>=index:
            raise ValueError("Nonancestral private rig parent index")
        if parent==-1:
            world.append((q,translation))
        else:
            ancestor_q,ancestor_t=world[parent]
            world.append((
                multiply(ancestor_q,q),
                sum3(ancestor_t,rotated(ancestor_q,translation)),
            ))
    return world


def predict_vertices(bind,animation,vertices):
    if not bind or len(bind)!=len(animation):
        raise ValueError("Mismatched private skeleton dimensions")
    if any(x[0]!=y[0] for x,y in zip(bind,animation,strict=True)):
        raise ValueError("Mismatched private bone parent array")
    source_world=worlds(bind)
    animated_world=worlds(animation)
    palettes=[]
    for (bq,bt),(aq,at) in zip(
        source_world,animated_world,strict=True
    ):
        inverse=(-bq[0],-bq[1],-bq[2],bq[3])
        q=multiply(aq,inverse)
        t=sum3(at,tuple(-x for x in rotated(q,bt)))
        palettes.append((q,t))
    moved=[]
    for position,influences in vertices:
        if not influences:
            moved.append(position)
            continue
        xyz=[0.,0.,0.]
        for bone,weight in influences:
            if bone<0 or bone>=len(palettes) or weight<0:
                raise ValueError("Invalid private skin influence")
            q,t=palettes[bone]
            transformed=sum3(rotated(q,position),t)
            for axis in range(3):
                xyz[axis]+=weight*transformed[axis]
        if not all(math.isfinite(v) for v in xyz):
            raise ValueError("Nonfinite private deformation")
        moved.append(tuple(xyz))
    return moved
