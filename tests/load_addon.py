# Loads the add-on straight from the repo, registers it, checks every operator and panel exists,
# then unregisters it.   blender -b --factory-startup --python tests/load_addon.py
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "addon"))
sys.path.insert(0, ROOT)
import bpy  # noqa: E402
import blender_cubekit as ck  # noqa: E402

ck.register()
ops = sorted(n for n in dir(bpy.ops.cubekit))
print("LOAD operators:", len(ops), " ".join(ops))
print("LOAD panel:", hasattr(bpy.types, "CUBEKIT_PT_panel"))
ck.unregister()
print("LOAD unregister ok")
