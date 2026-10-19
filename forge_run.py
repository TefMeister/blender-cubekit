# Builds one forge design into a fresh .blend and renders its preview pictures, with no Blender window:
#   blender -b --factory-startup --python forge_run.py -- <design.py> <out.blend> <render dir>
# The design file has a build() that returns a forge.Model. Then forge_sheet.py puts the pictures on one sheet.
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy                        # noqa: E402
import forge_bl                   # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    design, blend, renders = args[0], args[1], os.path.abspath(args[2])
    sys.path.insert(0, os.path.dirname(os.path.abspath(design)))
    t = time.time()
    spec = importlib.util.spec_from_file_location("design", design)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    model = mod.build()
    t_build = time.time() - t
    forge_bl.setup_scene()
    name = model.name
    tex = os.path.join(os.path.dirname(os.path.abspath(blend)), "textures", name + "_palette.png")
    objs, nfaces, ncol = forge_bl.build(model, tex)
    os.makedirs(os.path.dirname(os.path.abspath(blend)), exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend))
    os.makedirs(renders, exist_ok=True)
    forge_bl.render_views(objs, renders, name)
    c = model.counts()
    print("FORGE %s: cubes whole %d, half %d, quarter %d; faces %d; colours %d; build %.1f s; total %.1f s" %
          (name, c[1.0], c[0.5], c[0.25], nfaces, ncol, t_build, time.time() - t))


main()
