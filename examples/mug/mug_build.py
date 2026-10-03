# A coffee mug: the smallest complete CubeKit model. Settings -> shape in parts -> colours ->
# one textured mesh per part -> pictures -> a .blend to open.
#   blender -b --factory-startup --python examples/mug/mug_build.py
# Writes renders/*.png and mug.blend beside this file.
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.abspath(os.path.join(HERE, "..", ".."))):
    if p not in sys.path:
        sys.path.insert(0, p)

import bpy
from mathutils import Vector

from mug_settings import (VOXEL_M, PIVOT, RADIUS, HEIGHT, WALL, FLOOR, BAND, HANDLE_R, HANDLE_THICK,
                          HANDLE_CENTRE_X, COL, SHADE, NOISE, RENDER_DIR, OUT_DIR)
from parts import Parts
from bl import Space, make_objects, setup_scene, render

SPACE = Space(VOXEL_M, PIVOT)


def shape():
    """The mug as named parts. Each part becomes one object, so it can move on its own later."""
    g = Parts()
    r2 = RADIUS * RADIUS + 0.3
    inner = (RADIUS - WALL) ** 2 + 0.3
    for x in range(-RADIUS, RADIUS + 1):
        for y in range(-RADIUS, RADIUS + 1):
            d2 = x * x + y * y
            if d2 > r2:
                continue
            for z in range(0, HEIGHT):
                if d2 <= inner and z >= FLOOR:
                    continue                      # the hollow
                g.put("body", x, y, z, "cream")
    # the handle: a ring standing in the x-z plane, with the part inside the mug cut away
    cz = HEIGHT // 2
    for x in range(HANDLE_CENTRE_X - HANDLE_R, HANDLE_CENTRE_X + HANDLE_R + 1):
        for z in range(cz - HANDLE_R, cz + HANDLE_R + 1):
            d2 = (x - HANDLE_CENTRE_X) ** 2 + (z - cz) ** 2
            if (HANDLE_R - HANDLE_THICK) ** 2 <= d2 <= HANDLE_R * HANDLE_R + 0.3:
                for y in (-1, 0):
                    if not g.owned((x, y, z)):
                        g.put("handle", x, y, z, "handle")
    return g


def paint(cells):
    """Colour names -> sRGB, plus the band and the inside."""
    out = {}
    for (x, y, z), name in cells.items():
        if name == "cream" and x * x + y * y <= (RADIUS - WALL + 1) ** 2 and z >= FLOOR:
            name = "inside"                   # the inner wall, seen from above
        elif name == "cream" and BAND[0] <= z <= BAND[1]:
            name = "band"
        out[(x, y, z)] = COL[name]
    return out


def camera(name, loc, target, lens=50):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    co = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(co)
    co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co


def run():
    os.makedirs(RENDER_DIR, exist_ok=True)
    setup_scene(1, res=(900, 900), bg=(0.30, 0.30, 0.34))
    root = bpy.data.objects.new("Mug_Root", None)
    bpy.context.scene.collection.objects.link(root)
    g = shape()
    specs = [("Mug_" + part, paint(cells), PIVOT) for part, cells in g.p.items()]
    make_objects(specs, root, os.path.join(OUT_DIR, "mug_atlas.png"), SPACE, SHADE, NOISE)
    print("cubes:", {k: len(v) for k, v in g.p.items()})
    mid = SPACE.to_bl(0, 0, HEIGHT // 2)
    cam = camera("three_quarter", mid + Vector((-0.17, 0.22, 0.12)), mid)   # the handle side
    bpy.context.scene.camera = cam
    render(os.path.join(RENDER_DIR, "three_quarter.png"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "mug.blend"))


run()
