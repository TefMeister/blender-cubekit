# Make a "pick" copy of any cube model's .blend: every cube selectable on its own (Tefa, 2026-10-03).
#   blender -b "<model>.blend" --python pick_mode.py
# writes <model>_pick.blend beside it. Open THAT to edit cube by cube (Tab, hover a cube, L).
# The original stays merged, which is what the game export reads.
import os, sys, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cube_size import VOXEL_M
import bl
src = bpy.data.filepath
counts = bl.pick_mode_all(VOXEL_M)
bad = [n for n in counts if not bl.pick_mode_check(bpy.data.objects[n], VOXEL_M)]
out = src[:-6] + "_pick.blend"
bpy.ops.wm.save_as_mainfile(filepath=out)
print("PICK", os.path.basename(out), "cubes", sum(c for c, _ in counts.values()), "faces", sum(f for _, f in counts.values()),
      "every cube on its own:", not bad, bad)
