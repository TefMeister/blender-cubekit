# Runs every cube-editing tool on a small made-up model and prints a fingerprint of each result, so
# a change that should not change behaviour (a split of a file into smaller files) can be proven to
# change nothing: run before and after, compare the output.
#   blender -b --factory-startup --python tests/run_ops.py
import hashlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import bpy  # noqa: E402
import edit  # noqa: E402

V = 0.0034
RED, BLUE, GREY = (0.8, 0.1, 0.1), (0.1, 0.2, 0.9), (0.5, 0.5, 0.5)


def fresh(name="cubes"):
    """An L-shaped block of 3 x 2 x 2 cubes plus one cube on top, all on the 3.4 mm grid."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(0, 0, 0)], [], [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    cells = [(x, y, z) for x in range(3) for y in range(2) for z in range(2)] + [(0, 0, 2)]
    ob["cubekit_cells"] = [i for c in cells for i in c]
    ob["cubekit_cell_rgb"] = [x for c in cells for x in (RED if c[0] == 0 else GREY)]
    ob["cubekit_voxel_m"] = V
    ob["cubekit_off"] = [0.0, 0.0, 0.0]
    edit.Solid(ob, V).write()
    return ob


def digest(ob):
    me = ob.data
    h = hashlib.sha256()
    for v in me.vertices:
        h.update(("%.6f %.6f %.6f;" % tuple(v.co)).encode())
    for p in me.polygons:
        h.update((" ".join(str(i) for i in p.vertices) + "|" + str(p.select) + ";").encode())
    for name in ("cubekit_base", "cubekit_view"):
        a = me.color_attributes.get(name)
        if a:
            for d in a.data:
                h.update(("%.5f %.5f %.5f;" % tuple(d.color[:3])).encode())
    for name in ("cubekit_level", "cubekit_group"):
        a = me.attributes.get(name)
        if a:
            h.update(",".join(str(d.value) for d in a.data).encode())
    for k in ("cubekit_cells", "cubekit_cell_rgb", "cubekit_voxel_m", "cubekit_off", "cubekit_off_stack"):
        if k in ob:
            val = ob[k]
            val = list(val) if hasattr(val, "__len__") else [val]
            h.update((k + ":" + ",".join("%.6f" % float(x) for x in val)).encode())
    return "%5d faces %s" % (len(me.polygons), h.hexdigest()[:16])


def pick(ob, keys):
    """Pick the faces of these (cell, dir) keys, as the brush would."""
    s = edit.Solid(ob, ob["cubekit_voxel_m"])
    want = set(keys)
    for p in ob.data.polygons:
        p.select = s.key_of(p)[:2] in want
    return [k for k in s.selected_keys()]


def report(label, ob):
    print("OPS", label.ljust(16), digest(ob))


def main():
    ob = fresh()
    report("write", ob)
    keys = pick(ob, [((0, 0, 2), (0, 0, 1))])
    edit.grow(ob, V, keys, count=2)
    report("grow", ob)
    keys = pick(ob, [((2, 1, 1), (1, 0, 0))])
    edit.shrink(ob, V, keys)
    report("shrink", ob)
    keys = pick(ob, [((0, 0, 0), (0, -1, 0)), ((1, 0, 0), (0, -1, 0))])
    edit.paint(ob, V, keys, BLUE, False)
    report("paint sides", ob)
    edit.paint(ob, V, [((1, 1, 1),)], RED, True)
    report("paint cube", ob)
    keys = pick(ob, [((0, 0, 0), (-1, 0, 0))])
    edit.split(ob, V, keys, False)
    report("split 4", ob)
    edit.split(ob, V, keys, False)
    report("split 16", ob)
    s = edit.Solid(ob, V)
    fine = [k for k in (s.key_of(p) for p in ob.data.polygons) if len(k) == 3 and k[:2] == ((0, 0, 0), (-1, 0, 0))]
    edit.paint(ob, V, fine[:3], BLUE, False)
    report("paint 16", ob)
    edit.subdivide(ob, V)
    report("subdivide", ob)
    edit.merge(ob, V / 2)
    report("merge", ob)
    keys = pick(ob, [((0, 0, 0), (-1, 0, 0))])
    edit.join(ob, V, keys, False)
    report("join", ob)
    edit.move_cubes(ob, V, [((0, 0, 2),)], (0, 1, 0))
    report("move", ob)
    clip = edit.copy_cubes(ob, V, {(1, 0, 0), (1, 1, 0)}, (1, 0, 0), (0, -1, 0))
    edit.paste_cubes(ob, V, clip, (2, 0, 1), (0, 0, 1))
    report("paste", ob)
    picked, rest, joint, off, v = edit.split_part_plan(ob, V, [((0, 0, 0),)])
    print("OPS part plan       ", sorted(picked), joint)
    edit.drop(ob, V, {(2, 1, 0)})
    report("drop", ob)
    edit.keep_only(ob, V, set(list(edit.Solid(ob, V).cells)[:6]), shift=(1, 0, 0))
    report("keep only", ob)
    ob2 = fresh("tiers")
    print("OPS ensure finer    ", edit.ensure_size(ob2, V / 4, V))
    report("finer x2", ob2)
    print("OPS ensure bigger   ", edit.ensure_size(ob2, V, V))
    report("back to start", ob2)


main()
