# Builds dist/blender_cubekit-<version>.zip: the add-on plus the kit modules it needs (bl.py,
# atlas.py, cube_size.py), copied in at zip time so there is ONE copy of each in the repo.
#   python addon/make_addon_zip.py
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PKG = os.path.join(HERE, "blender_cubekit")
manifest = open(os.path.join(PKG, "blender_manifest.toml"), encoding="utf-8").read()
version = re.search(r'^version = "([^"]+)"', manifest, re.M).group(1)
out = os.path.join(ROOT, "dist", "blender_cubekit-%s.zip" % version)
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in ("blender_manifest.toml", "__init__.py", "navigate.py", "palette.py"):
        z.write(os.path.join(PKG, name), name)
    for name in ("bl.py", "edit.py", "atlas.py", "cube_size.py"):
        z.write(os.path.join(ROOT, name), name)
print("wrote", os.path.relpath(out, ROOT), os.path.getsize(out), "bytes")
