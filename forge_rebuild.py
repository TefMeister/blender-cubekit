# Builds a forge gun's own objects again inside an existing .blend, leaving everything else in the file alone
# (hands, gloves, cameras, anything added later). Used when a design changes but its cubes do not, for example
# when its pieces get names of their own so each can be picked in Blender (Tefa, 2026-10-23).
#   blender -b <gun.blend> --python forge_rebuild.py -- <design.py> [<check picture.png>]
# The gun's objects are the ones in the collection named after the model; that collection, its objects, their
# meshes, the gun's material and palette picture are replaced. Blender keeps the file as it was as .blend1.
# The check picture shows the gun from its right side with every piece in its own colour.
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy                        # noqa: E402
from mathutils import Vector      # noqa: E402
import forge_bl                   # noqa: E402


def load(design):
    sys.path.insert(0, os.path.dirname(os.path.abspath(design)))
    spec = importlib.util.spec_from_file_location("design", design)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build()


def remove_gun(name):
    """Take out the gun's collection, objects, meshes, material and palette. Returns how many objects went."""
    col = bpy.data.collections.get(name)
    if col is None:
        raise SystemExit("no collection named %s in this file" % name)
    obs = list(col.objects)
    strays = [o.name for o in obs if not o.name.startswith(name + "_")]
    if strays:
        raise SystemExit("the gun's collection holds objects that are not the gun's: %s" % strays)
    for o in obs:
        me = o.data if o.type == 'MESH' else None
        bpy.data.objects.remove(o)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    bpy.data.collections.remove(col)
    mat = bpy.data.materials.get(name + "_cubes")
    if mat is not None and mat.users == 0:
        bpy.data.materials.remove(mat)
    img = bpy.data.images.get(name + "_palette")
    if img is not None and img.users == 0:
        bpy.data.images.remove(img)
    return len(obs)


def check_picture(objs, path):
    sc = bpy.context.scene
    sh = sc.display.shading
    old = (sc.render.engine, sh.light, sh.color_type)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh.light = 'STUDIO'
    sh.color_type = 'RANDOM'                     # every object (piece) in its own colour
    hidden = [o for o in sc.objects if o.type == 'MESH' and o.name not in {ob.name for ob in objs.values()}]
    for o in hidden:
        o.hide_render = True
    pts = [o.matrix_world @ Vector(c) for o in objs.values() for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    cam = bpy.data.objects.new("parts_check_cam", bpy.data.cameras.new("parts_check_cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = 'ORTHO'
    ext = hi - lo
    cam.data.ortho_scale = max(ext.y, ext.z * 2) * 1.1
    cam.location = (lo + hi) / 2 + Vector((ext.length * 3, 0, 0))        # from the gun's right side, as forge_bl
    cam.rotation_euler = Vector((-1, 0, 0)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = ext.length * 10
    sc.render.resolution_x, sc.render.resolution_y = 1200, 600
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    for o in hidden:
        o.hide_render = False
    sc.render.engine, sh.light, sh.color_type = old


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    model = load(args[0])
    gone = remove_gun(model.name)
    tex = os.path.join(os.path.dirname(bpy.data.filepath), "textures", model.name + "_palette.png")
    objs, nfaces, ncol = forge_bl.build(model, tex)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_mainfile()
    print("REBUILT %s: %d objects out, %d pieces in (%s); faces %d" %
          (model.name, gone, len(objs), ", ".join(sorted(objs)), nfaces))
    if len(args) > 1:
        check_picture(objs, os.path.abspath(args[1]))


main()
