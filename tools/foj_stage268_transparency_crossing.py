#!/usr/bin/env python3
"""Stage268 fail-closed screen-space translucent triangle order analyzer.

Generated-only host math. No GPU proof, private textures or source game assets.
Screen XY are orthographic/clip coordinates; Z follows the research pipeline's
GREATER depth convention (larger is nearer).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

AREA_EPS = 1e-9
DEPTH_EPS = 1e-6
MAX_TRIANGLES = 64

Point = tuple[float, float]
Vertex = tuple[float, float, float]


class UnsafeTransparencyOrder(ValueError):
    """A single global transparent triangle order cannot be certified."""


@dataclass(frozen=True)
class Triangle:
    name: str
    vertices: tuple[Vertex, Vertex, Vertex]


def cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def signed_area_twice(points: Sequence[Point]) -> float:
    return sum(cross(a, b) for a, b in zip(points, (*points[1:], points[0])))


def validate(triangle: Triangle) -> None:
    if not isinstance(triangle, Triangle):
        raise ValueError("Expected Triangle")
    if not isinstance(triangle.name, str) or not triangle.name.strip():
        raise ValueError("Empty triangle identifier")
    if not isinstance(triangle.vertices, tuple) or len(triangle.vertices) != 3:
        raise ValueError("Expected exactly three vertices")
    for vertex in triangle.vertices:
        if not isinstance(vertex, tuple) or len(vertex) != 3:
            raise ValueError("Vertex must be a 3-tuple")
        if any(type(v) not in (int, float) or not isfinite(v) for v in vertex):
            raise ValueError("Every coordinate must be finite")
        x, y, z = vertex
        if not (-1 <= x <= 1 and -1 <= y <= 1 and 0 <= z <= 1):
            raise ValueError("Vertex outside canonical clip XY / Z range")
    poly = [(x, y) for x, y, _ in triangle.vertices]
    if abs(signed_area_twice(poly)) <= AREA_EPS:
        raise ValueError("Projected triangle is degenerate")


def _inside(edge_a: Point, edge_b: Point, p: Point, sign: float) -> float:
    return sign * cross(
        (edge_b[0] - edge_a[0], edge_b[1] - edge_a[1]),
        (p[0] - edge_a[0], p[1] - edge_a[1]),
    )


def _clip_polygon(subject: list[Point], boundary: list[Point]) -> list[Point]:
    """Sutherland-Hodgman intersection; works with both polygon windings."""
    sign = 1.0 if signed_area_twice(boundary) > 0 else -1.0
    result = subject
    for edge_index, edge_a in enumerate(boundary):
        edge_b = boundary[(edge_index + 1) % len(boundary)]
        old = result
        result = []
        if not old:
            break
        previous = old[-1]
        d_prev = _inside(edge_a, edge_b, previous, sign)
        for current in old:
            d_curr = _inside(edge_a, edge_b, current, sign)
            prev_ok = d_prev >= -AREA_EPS
            curr_ok = d_curr >= -AREA_EPS
            if curr_ok != prev_ok:
                denom = d_prev - d_curr
                # Opposite signed sides imply a nonzero denominator.
                if abs(denom) <= 1e-15:
                    raise UnsafeTransparencyOrder("Numerically unstable clip edge")
                t = max(0.0, min(1.0, d_prev / denom))
                result.append((
                    previous[0] + t * (current[0] - previous[0]),
                    previous[1] + t * (current[1] - previous[1]),
                ))
            if curr_ok:
                result.append(current)
            previous, d_prev = current, d_curr
    return result


def _sample_depth(tri: Triangle, p: Point) -> float:
    a, b, c = tri.vertices
    ab = (b[0] - a[0], b[1] - a[1])
    ac = (c[0] - a[0], c[1] - a[1])
    ap = (p[0] - a[0], p[1] - a[1])
    denominator = cross(ab, ac)
    w_b = cross(ap, ac) / denominator
    w_c = cross(ab, ap) / denominator
    return a[2] + w_b * (b[2] - a[2]) + w_c * (c[2] - a[2])


def pair_relation(a: Triangle, b: Triangle) -> str:
    """Return far-before-near relation or disjoint; reject depth crossings.

    Touching at only one vertex or a zero-area edge produces 'disjoint',
    because those contacts have no shared interior requiring compositing.
    Equal / near-equal depths and crossings in positive-area intersections
    are conservatively unsafe.
    """
    validate(a)
    validate(b)
    if a.name == b.name:
        raise ValueError("Identical triangle names")
    p_a = [(v[0], v[1]) for v in a.vertices]
    p_b = [(v[0], v[1]) for v in b.vertices]
    intersection = _clip_polygon(p_a, p_b)
    if len(intersection) < 3 or abs(signed_area_twice(intersection)) <= AREA_EPS:
        return "disjoint"
    differences = [_sample_depth(a, p) - _sample_depth(b, p)
                   for p in intersection]
    if min(differences) > DEPTH_EPS:
        return "b_before_a"
    if max(differences) < -DEPTH_EPS:
        return "a_before_b"
    raise UnsafeTransparencyOrder(
        f"Depth crossing or coplanar overlap: {a.name} / {b.name}"
    )


def plan_back_to_front(triangles: Sequence[Triangle]) -> tuple[str, ...]:
    """Return deterministic triangle-name order only if all pair orders agree.

    Disjoint pairs impose no constraint. Cyclic overlap dependencies cannot be
    represented by a single draw order and are also rejected. This is *not*
    polygon splitting, OIT, per-pixel depth peeling, or a GPU renderer.
    """
    if not 1 <= len(triangles) <= MAX_TRIANGLES:
        raise ValueError("Unsupported triangle count")
    names: set[str] = set()
    for tri in triangles:
        validate(tri)
        if tri.name in names:
            raise ValueError("Duplicate triangle name")
        names.add(tri.name)
    edges = {name: set() for name in names}
    indegree = {name: 0 for name in names}
    for index, a in enumerate(triangles):
        for b in triangles[index + 1:]:
            relation = pair_relation(a, b)
            if relation == "disjoint":
                continue
            farther, nearer = ((a.name, b.name)
                               if relation == "a_before_b"
                               else (b.name, a.name))
            if nearer not in edges[farther]:
                edges[farther].add(nearer)
                indegree[nearer] += 1
    result = []
    available = sorted(name for name in names if indegree[name] == 0)
    while available:
        first = available.pop(0)
        result.append(first)
        for adjacent in sorted(edges[first]):
            indegree[adjacent] -= 1
            if indegree[adjacent] == 0:
                available.append(adjacent)
        available.sort()
    if len(result) != len(triangles):
        raise UnsafeTransparencyOrder("Cyclic triangle depth precedence")
    return tuple(result)


def example_crossing_pair() -> tuple[Triangle, Triangle]:
    xy = ((-.70, -.45), (.70, -.45), (0., .70))
    return (
        Triangle("slanted", tuple((x, y, z) for (x,y),z in
                                 zip(xy, (.25, .75, .50)))),
        Triangle("flat", tuple((x, y, .50) for x,y in xy)),
    )


if __name__ == "__main__":
    import json
    a, b = example_crossing_pair()
    try:
        print(json.dumps({"order": list(plan_back_to_front([a, b])),
                          "safe": True}))
    except UnsafeTransparencyOrder as exc:
        print(json.dumps({"safe": False, "reason": str(exc),
                          "scope": "host_geometry_guard_only"}))
