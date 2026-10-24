# The colour of cubes added and uncovered by adding and carving (Tefa, 2026-10-24): "Same as the side" keeps the
# colour pattern going (a new cube takes the colour of the side it goes on, the cube a carve uncovers takes the carved
# cube's colour), "Chosen colour" paints both the chosen colour, and the old carve (no colour asked) leaves the
# uncovered cube as it was. Whole cubes and small cubes.
#   blender -b --factory-startup --python tests/run_colour.py
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import bpy  # noqa: E402
import edit  # noqa: E402
import edit_small as small  # noqa: E402

V = 0.0034
RED, BLUE, GREY, GREEN, YEL = (0.8, 0.1, 0.1), (0.1, 0.2, 0.9), (0.5, 0.5, 0.5), (0.1, 0.8, 0.2), (0.9, 0.8, 0.1)
UP = (0, 0, 1)
fails = []


def near(c, want):
    return c is not None and all(abs(a - b) < 1e-3 for a, b in zip(c, want))


def check(name, ok, detail=""):
    print("COLOUR %-44s %s %s" % (name, "ok" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


def fresh(name="cubes"):
    """A column of three cubes: red on top of blue on top of grey."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(0, 0, 0)], [], [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    cells = [(0, 0, 0), (0, 0, 1), (0, 0, 2)]
    ob["cubekit_cells"] = [i for c in cells for i in c]
    ob["cubekit_cell_rgb"] = list(GREY) + list(BLUE) + list(RED)
    ob["cubekit_voxel_m"] = V
    ob["cubekit_off"] = [0.0, 0.0, 0.0]
    edit.Solid(ob, V).write()
    return ob


def top_key(ob, cell):
    s = edit.Solid(ob, V)
    for p in ob.data.polygons:
        k = s.key_of(p)
        if k[:2] == (cell, UP):
            return [k]
    return []


def colour(ob, cell):
    return edit.Solid(ob, V).colour_of(cell, UP)


# carving the red top cube: what colour is the blue cube it uncovers?
ob = fresh("keep")
edit.shrink(ob, V, top_key(ob, (0, 0, 2)))
check("carve, no colour asked: uncovered stays blue", near(colour(ob, (0, 0, 1)), BLUE), colour(ob, (0, 0, 1)))

ob = fresh("match")
edit.shrink(ob, V, top_key(ob, (0, 0, 2)), 1, None, match=True)
s = edit.Solid(ob, V)
check("carve, same as the side: red cube gone", (0, 0, 2) not in s.cells)
check("carve, same as the side: uncovered is red", near(colour(ob, (0, 0, 1)), RED), colour(ob, (0, 0, 1)))

ob = fresh("chosen")
edit.shrink(ob, V, top_key(ob, (0, 0, 2)), 1, GREEN, match=True)
check("carve, chosen colour: uncovered is green", near(colour(ob, (0, 0, 1)), GREEN), colour(ob, (0, 0, 1)))

ob = fresh("deep")
edit.shrink(ob, V, top_key(ob, (0, 0, 2)), 2, None, match=True)
check("carve 2 deep, same as the side: grey cube now red", near(colour(ob, (0, 0, 0)), RED), colour(ob, (0, 0, 0)))

# adding on the red top
ob = fresh("add-side")
edit.grow(ob, V, top_key(ob, (0, 0, 2)), 1, None)
check("add, same as the side: new cube is red", near(colour(ob, (0, 0, 3)), RED), colour(ob, (0, 0, 3)))
ob = fresh("add-chosen")
edit.grow(ob, V, top_key(ob, (0, 0, 2)), 1, GREEN)
check("add, chosen colour: new cube is green", near(colour(ob, (0, 0, 3)), GREEN), colour(ob, (0, 0, 3)))

# small cubes: the red top cube made into eight half cubes, the top sides of the upper four painted yellow, then
# those carved: the lower four stay red, turn yellow (the carved side's colour) or turn green (chosen)
for mode, col, match, want in (("small-keep", None, False, RED), ("small-match", None, True, YEL),
                               ("small-chosen", GREEN, True, GREEN)):
    ob = fresh(mode)
    s = edit.Solid(ob, V)
    keys = []
    for p in ob.data.polygons:
        k = s.key_of(p)
        if k[:1] == ((0, 0, 2),):
            p.select = True
    keys = edit.Solid(ob, V).selected_keys()
    edit.resize_picked(ob, V, keys, -1)
    s = edit.Solid(ob, V)
    tops = []
    for p in ob.data.polygons:
        k = s.key_of(p)
        if small.is_sub(k) and k[0] == (0, 0, 2) and k[1] == UP:
            tops.append(k)
    tops = list(dict.fromkeys(tops))
    edit.paint(ob, V, tops, YEL, False)
    edit.shrink(ob, V, tops, 1, col, match=match)
    s = edit.Solid(ob, V)
    fc = s.fine.get((0, 0, 2))
    left = sorted(fc.subs) if fc else []
    rgbs = {fc.subs[i] for i in left} if fc else set()
    ok = bool(left) and all(near(c, want) for c in rgbs)
    check("%s: lower half cubes are the right colour" % mode, ok, "%d left, %s" % (len(left), rgbs))

print("COLOUR RESULT:", "ALL OK" if not fails else "FAILED: " + ", ".join(fails))
