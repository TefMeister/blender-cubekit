# The mug: every number and colour in one place. This is the shape every project's settings file
# takes: the cube size comes from the kit (never typed here), sizes are in cubes, colours are
# sRGB 0-255, and each number has a name so the build script never holds a bare number.
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
from cube_size import VOXEL_M      # ONE cube size for every model in a project: cube_size.py

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
RENDER_DIR = os.path.join(OUT_DIR, "renders")

# Cube axes: x and y across, z up. z = 0 is the table.
PIVOT = (0, 0, 0)                  # the cube that sits at Blender's origin

# ---- sizes, in cubes ----
RADIUS = 14                        # about 95 mm across at 3.4 mm cubes
HEIGHT = 26                        # about 88 mm tall
WALL = 2
FLOOR = 2
BAND = (17, 20)                    # the red band: bottom row, top row
HANDLE_R = 7                       # the ring the handle is cut from
HANDLE_THICK = 2
HANDLE_CENTRE_X = RADIUS + 4       # where the ring's middle sits, out from the mug's centre

# ---- colours, sRGB 0-255 ----
COL = {
    "cream": (235, 225, 205),
    "band": (190, 50, 45),
    "inside": (120, 108, 96),
    "handle": (225, 215, 195),
}

# ---- the look ----
# How much each face direction is brightened or darkened: top lightest, bottom darkest. This is
# what makes a flat, unlit model read as solid. (dx, dy, dz) -> factor.
SHADE = {(0, 0, 1): 1.12, (0, 0, -1): 0.55, (0, 1, 0): 0.88, (0, -1, 0): 0.88,
         (1, 0, 0): 0.74, (-1, 0, 0): 0.74}
NOISE = 0.05                       # per-cube brightness wobble, so flat areas are not dead flat
