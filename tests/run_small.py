# Exercises smaller cubes inside one model, prints checks, and renders a picture to look at.
#   blender -b --factory-startup --python tests/run_small.py -- out.png
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import bpy  # noqa: E402
import edit  # noqa: E402
import edit_small as small  # noqa: E402

V = 0.0034
RED, BLUE, GREY, YEL = (0.8, 0.1, 0.1), (0.1, 0.2, 0.9), (0.5, 0.5, 0.5), (0.9, 0.8, 0.1)
fails = []


def check(name, ok, detail=""):
    print("SMALL %-34s %s %s" % (name, "ok" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


def fresh(name="cubes"):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(0, 0, 0)], [], [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    cells = [(x, y, z) for x in range(3) for y in range(2) for z in range(2)]
    ob["cubekit_cells"] = [i for c in cells for i in c]
    ob["cubekit_cell_rgb"] = [x for c in cells for x in (RED if c[0] == 0 else GREY)]
    ob["cubekit_voxel_m"] = V
    ob["cubekit_off"] = [0.0, 0.0, 0.0]
    edit.Solid(ob, V).write()
    return ob


def pick(ob, want):
    """Pick every face whose key starts like one of want ((cell, dir) or (cell,))."""
    s = edit.Solid(ob, V)
    for p in ob.data.polygons:
        k = s.key_of(p)
        p.select = any(k[:len(w)] == w for w in want)
    return s.selected_keys()


def state(ob):
    s = edit.Solid(ob, V)
    return s


ob = fresh()
n0 = len(ob.data.polygons)

# 1. one corner cube -> eight 1.7 mm cubes
keys = pick(ob, [((2, 1, 1),)])
n = edit.resize_picked(ob, V, keys, -1)
s = state(ob)
check("half: one cube changed", n == 1, n)
check("half: cell left the main grid", (2, 1, 1) not in s.cells)
check("half: 8 half cubes", (2, 1, 1) in s.fine and len(s.fine[(2, 1, 1)].half) == 8 and len(s.fine[(2, 1, 1)].subs) == 64)
# the corner cube showed 3 sides; as 8 half cubes each exposed side is 4 half-cube sides
check("half: 3 sides became 12", len(ob.data.polygons) == n0 - 3 + 12, "%d vs %d" % (len(ob.data.polygons), n0 + 9))

# 2. dig one half cube away (Q with whole cubes): a 1.7 mm hole
keys = pick(ob, [((2, 1, 1), (0, 0, 1), "sub")])
top = [k for k in keys if k[3][0] == small.octant_subs(7)[0]]      # the +x +y +z octant
check("pick: 4 half-cube tops picked", len(keys) == 4, len(keys))
edit.remove_cubes(ob, V, top)
s = state(ob)
check("dig: 7 half cubes left", len(s.fine[(2, 1, 1)].half) == 7 and len(s.fine[(2, 1, 1)].subs) == 56)

# 3. one of the remaining half cubes -> eight 0.85 mm cubes, then paint one quarter blue
keys = pick(ob, [((2, 1, 1), (0, 0, 1), "sub")])
one = [k for k in keys if k[3][0] == small.octant_subs(3)[0]]
edit.resize_picked(ob, V, one, -2)
s = state(ob)
check("quarter: 6 half + 8 quarter", len(s.fine[(2, 1, 1)].half) == 6 and len(s.fine[(2, 1, 1)].subs) == 56)
keys = pick(ob, [((2, 1, 1), (0, 0, 1), "sub")])
q = [k for k in keys if k[3][1] == 1]
check("pick: 4 quarter tops picked", len(q) == 4, len(q))
edit.paint(ob, V, q[:1], BLUE, True)
s = state(ob)
check("paint: a quarter cube is blue", s.fine[(2, 1, 1)].subs[q[0][3][0]] == BLUE)

# 4. E on a quarter cube's top: the quarter cubes face the dug-out octant above, so one grows into it
keys = pick(ob, [((2, 1, 1), (0, 0, 1), "sub")])
q = [k for k in keys if k[3][1] == 1][:1]
edit.grow(ob, V, q)
s = state(ob)
check("grow: a quarter cube into the hole", len(s.fine[(2, 1, 1)].subs) == 57)
edit.grow(ob, V, q, count=3)                     # and on, out of the top of the cell
s = state(ob)
check("grow: on into the cell above", (2, 1, 2) in s.fine and len(s.fine[(2, 1, 2)].subs) == 1)

# 5. a main cube's side facing the small cubes shows only the uncovered squares
s = state(ob)
faces_nb = [p for p in ob.data.polygons if s.key_of(p)[:2] == ((1, 1, 1), (1, 0, 0))]
check("neighbour side: fully covered, hidden", len(faces_nb) == 0, len(faces_nb))
keys = pick(ob, [((2, 1, 1), (0, 0, 1), "sub")])
low = [k for k in keys if k[3] == (small.octant_subs(4)[0], 2)]      # the -x -y +z half cube
check("pick: the low half cube on top", len(low) == 1, len(low))
edit.remove_cubes(ob, V, low)
s = state(ob)
faces_nb = [p for p in ob.data.polygons if s.key_of(p)[:2] == ((1, 1, 1), (1, 0, 0))]
check("neighbour side: 4 squares uncovered", len(faces_nb) == 4, len(faces_nb))
check("neighbour side: read back plain", ((1, 1, 1), (1, 0, 0)) not in s.split)

# 6. save / reload round trip: the fine data survives a re-read of the mesh + props
before = (sorted(s.fine[(2, 1, 1)].subs.items()), sorted(s.fine[(2, 1, 1)].half))
s2 = edit.Solid(ob, V)
after = (sorted(s2.fine[(2, 1, 1)].subs.items()), sorted(s2.fine[(2, 1, 1)].half))
check("reload: fine cubes identical", before == after)

# 7. the old tools still work beside small cubes
keys = pick(ob, [((0, 0, 0), (-1, 0, 0))])
edit.grow(ob, V, keys)
edit.split(ob, V, pick(ob, [((0, 1, 0), (0, 1, 0))]), False)
s = state(ob)
check("old tools: grew and split beside", (-1, 0, 0) in s.cells and ((0, 1, 0), (0, 1, 0)) in s.split)

# 8. back to the file's size: the cell comes back as one cube (5 of 8 octants there -> stays)
keys = pick(ob, [((2, 1, 1), (0, 0, 1), "sub")])
edit.resize_picked(ob, V, keys, 0)
s = state(ob)
check("join: one whole cube again", (2, 1, 1) in s.cells and (2, 1, 1) not in s.fine)
check("join: top side keeps blue as detail", ((2, 1, 1), (0, 0, 1)) in s.split)
check("join: grown quarter above is kept", (2, 1, 2) in s.fine)

# 9. make small then dig most away and join: the cube goes (less than half left)
keys = pick(ob, [((0, 0, 1),)])
edit.resize_picked(ob, V, keys, -1)
keys = pick(ob, [((0, 0, 1), (0, 0, 1), "sub")]) + pick(ob, [((0, 0, 1), (-1, 0, 0), "sub")])
edit.remove_cubes(ob, V, keys)
s = state(ob)
left = len(s.fine.get((0, 0, 1), small.FineCell()).half)
edit.resize_picked(ob, V, pick(ob, [((0, 0, 1), (0, -1, 0), "sub")]), 0)
s = state(ob)
check("join: mostly dug cube disappears", left < 4 and (0, 0, 1) not in s.cells and (0, 0, 1) not in s.fine, left)

# 9b. the whole-file size change carries small cubes along, and back
ob3 = fresh("tiers")
edit.resize_picked(ob3, V, pick(ob3, [((2, 1, 1),)]), -2)
keys = pick(ob3, [((2, 1, 1), (0, 0, 1), "sub")])
edit.paint(ob3, V, keys[:1], BLUE, True)
edit.remove_cubes(ob3, V, keys[1:3])
edit.subdivide(ob3, V)
s = edit.Solid(ob3, V / 2)
n_fine_subs = sum(len(fc.subs) for fc in s.fine.values())
check("finer: quarters became half cubes", len(s.cells) == 11 * 8 and n_fine_subs == (64 - 2) * 8, "%d %d" % (len(s.cells), n_fine_subs))
check("finer: blue carried", any(BLUE in fc.subs.values() for fc in s.fine.values()))
edit.merge(ob3, V / 2)
s = edit.Solid(ob3, V)
check("bigger: joined back to 12 cubes", len(s.cells) == 12 and not s.fine, "%d %d" % (len(s.cells), len(s.fine)))

# 10. a picture
out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
if out:
    ob2 = fresh("shown")
    edit.resize_picked(ob2, V, pick(ob2, [((2, 1, 1),)]), -1)
    keys = pick(ob2, [((2, 1, 1), (0, 0, 1), "sub")])
    edit.remove_cubes(ob2, V, [k for k in keys if k[3][0] == small.octant_subs(7)[0]])
    keys = pick(ob2, [((2, 1, 1), (0, 0, 1), "sub")])
    edit.resize_picked(ob2, V, [k for k in keys if k[3][0] == small.octant_subs(3)[0]], -2)
    keys = pick(ob2, [((2, 1, 1), (0, 0, 1), "sub")])
    q = [k for k in keys if k[3][1] == 1]
    edit.paint(ob2, V, q[:2], BLUE, True)
    edit.paint(ob2, V, pick(ob2, [((2, 1, 1), (1, 0, 0), "sub")])[:3], YEL, False)
    edit.grow(ob2, V, q[2:3])
    bpy.data.objects.remove(ob)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'FLAT'
    scene.display.shading.color_type = 'VERTEX'
    scene.render.resolution_x, scene.render.resolution_y = 900, 700
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 0.016
    cam.data.clip_start, cam.data.clip_end = 0.0005, 1.0
    cam.location = (0.03, -0.03, 0.03)
    import mathutils
    cam.rotation_euler = (mathutils.Vector((0.0051, 0.0034, 0.0034)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("SMALL rendered", out)

print("SMALL RESULT", "ALL OK" if not fails else "FAILED: " + ", ".join(fails))
