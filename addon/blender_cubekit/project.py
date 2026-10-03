# The project's cube size, shared by every model in it (asked for by Tefa, 2026-10-03).
#
# A project keeps one small file, cube_project.py, in a folder above its model folders (for the
# Ashes models: the Screenshots folder, next to the cubekit folder). It holds the cube size the
# project started with (CUBE_MM_START, millimetres): the biggest any of its models can be.
# How fine each model is, is that model file's own choice (the add-on's cube size buttons, stored
# in the .blend), so making one weapon finer leaves the others at the start size (Tefa, 2026-10-03).
# A TIER line from version 0.8.0 is ignored.
import os
import re

FILE = "cube_project.py"
SEARCH_UP = 6                     # how many folders above the open .blend to look for the file
MIN_MM = 0.05                     # no finer than this

TEMPLATE = '''# This project's starting cube size, read by the CubeKit add-on (github.com/TefMeister/blender-cubekit).
# CUBE_MM_START: the size the project started with, in millimetres. No model goes bigger than this.
# Each model file can be made finer (half, quarter) with the add-on's cube size buttons.
CUBE_MM_START = {start}
'''


def find(blend_path):
    """The project file above the open .blend, or None."""
    if not blend_path:
        return None
    d = os.path.dirname(os.path.abspath(blend_path))
    for _ in range(SEARCH_UP):
        p = os.path.join(d, FILE)
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def home_for(blend_path):
    """Where to make a project file: the folder holding a 'cubekit' folder, else the .blend's own."""
    d = os.path.dirname(os.path.abspath(blend_path))
    start = d
    for _ in range(SEARCH_UP):
        if os.path.isdir(os.path.join(d, "cubekit")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return start


def read(path, default_start_mm):
    """(start mm, tier) from the project file; the kit's own size and tier 0 when there is none."""
    if not path:
        return default_start_mm, 0
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^CUBE_MM_START\s*=\s*([0-9.]+)", text, re.M)
    t = re.search(r"^TIER\s*=\s*(\d+)", text, re.M)
    return (float(m.group(1)) if m else default_start_mm), (int(t.group(1)) if t else 0)


def write(path, start_mm, tier):
    if os.path.isfile(path):
        text = open(path, encoding="utf-8").read()
        text = re.sub(r"^TIER\s*=\s*\d+", "TIER = %d" % tier, text, flags=re.M)
    else:
        text = TEMPLATE.format(start=start_mm, tier=tier)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def size_mm(start_mm, tier):
    return start_mm / (2 ** tier)
