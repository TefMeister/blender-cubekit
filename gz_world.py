# Put cube models into GZDoom as WORLD actors - things the game draws in the level, which
# is how anything held in the off hand has to work.
#   blender -b --factory-startup --python <cubekit>/gz_world.py -- <profile.py>
#
# Different from the weapons kit's gz_export.py on purpose: that one exports ONE animated
# weapon model per run and takes its frames from a Blender animation. Here one run writes
# SEVERAL models into one .pk3, and a "frame" is simply which objects are showing - which
# is what a cube model needs, because every pose is its own mesh.
#
# Cube models already carry their own baked atlas and UVs (cubekit/bl.py), so there is no
# unwrapping or baking here at all: the .png beside the .blend is the skin.
import bpy, sys, os, math, struct, zlib, zipfile
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index("--") + 1:]
PROFILE = os.path.abspath(args[0])
# the profile is exec'd, so it has no __file__ of its own; hand it its own folder
PROFILE_DIR = os.path.dirname(PROFILE)

# the weapons kit's MD3 writer, used unchanged so both routes make the same kind of file
KIT = os.path.join(os.path.expanduser("~"), "github-backups", "ashes-2063-weapons", "kit")
KIT = os.path.abspath(os.environ.get("ASHES_KIT", KIT))
exec(open(os.path.join(KIT, "gz_md3.py")).read())

exec(open(PROFILE).read())


def png_chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


# 1x1 transparent PNG. MODELDEF can only hang a model on a sprite name, so the name has
# to exist as a graphic even though nothing of it is ever drawn.
PIXEL = (bytes([0x89]) + b"PNG\r\n" + bytes([0x1A]) + b"\n"
         + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
         + png_chunk(b"IDAT", zlib.compress(bytes(5))) + png_chunk(b"IEND", b""))


def turn_matrix(rot, pre_roll=0.0):
    """Degrees about Blender X, Y, Z - applied Z first, then Y, then X. `pre_roll` is a
    turn about Blender X applied BEFORE all of them, which for a hand is a roll about its
    own forearm: the one move that swaps which side of the hand you are looking at."""
    rx, ry, rz = [math.radians(a) for a in rot]
    return (Matrix.Rotation(rx, 3, 'X') @ Matrix.Rotation(ry, 3, 'Y')
            @ Matrix.Rotation(rz, 3, 'Z') @ Matrix.Rotation(math.radians(pre_roll), 3, 'X'))


def to_md3(p, origin):
    # GZDoom draws MD3 +Y on the viewer's RIGHT (hh79/gzdoomvr gvr4.13.2.2, models.cpp)
    # [verified-live 2026-09-17], the same mapping the weapons kit uses.
    return ((p.y - origin[1]) * UNITS_PER_M,
            (p.x - origin[0]) * UNITS_PER_M,
            (p.z - origin[2]) * UNITS_PER_M)


def build_model(spec):
    """One .md3 + its MODELDEF block. spec['frames'] is a list of visible-object lists."""
    bpy.ops.wm.open_mainfile(filepath=spec["blend"])
    sc = bpy.context.scene
    sc.frame_set(1)
    wanted = [o for o in sorted(sc.objects, key=lambda o: o.name)
              if o.type == 'MESH' and o.name in spec["objects"]]
    missing = set(spec["objects"]) - {o.name for o in wanted}
    assert not missing, "%s: no such objects in %s: %s" % (spec["name"], spec["blend"], sorted(missing))

    origin = spec.get("origin", (0.0, 0.0, 0.0))
    turn = turn_matrix(spec.get("rot", (0, 0, 0)), spec.get("pre_roll", 0.0))
    frames, uvs = [], []
    for fi, shown_names in enumerate(spec["frames"]):
        shown = set(shown_names)
        verts = []
        for o in wanted:
            me = o.data
            M = o.matrix_world
            R = M.to_3x3()
            on = o.name in shown
            centre = M @ Vector((0, 0, 0))
            uvl = me.uv_layers.active.data
            for poly in me.polygons:
                n = (R @ poly.normal).normalized()
                loops = list(poly.loop_indices)
                for k in range(1, len(loops) - 1):
                    # HUD and world models are not back-face culled here, so one copy of
                    # each triangle is enough; the x -> Y mapping mirrors, so wind it back.
                    for li in (loops[0], loops[k + 1], loops[k]):
                        p = M @ me.vertices[me.loops[li].vertex_index].co if on else centre
                        q = turn @ (p - Vector(origin))
                        nn = turn @ n
                        verts.append((to_md3(q, (0, 0, 0)), (nn.y, nn.x, nn.z)))
                        if fi == 0:
                            uvs.append(tuple(uvl[li].uv))
        frames.append(verts)
    assert len(frames[0]) == len(uvs)

    md3 = os.path.join(OUT_DIR, spec["name"] + ".md3")
    tris = [(i, i + 1, i + 2) for i in range(0, len(uvs), 3)]
    nsurf, nv, nt = write_md3(md3, spec["name"], frames, (tris, uvs),
                              "%s/%s" % (MODEL_PATH, spec["skin"]))
    print("  %-22s %2d frames, %d surfaces, %d verts, %d tris"
          % (spec["name"], len(frames), nsurf, nv, nt))

    scale = spec.get("scale", MODEL_SCALE)
    lines = ["Model %s" % spec["actor"], "{",
             '   Path "%s"' % MODEL_PATH,
             '   Model 0 "%s.md3"' % spec["name"],
             '   Skin 0 "%s"' % spec["skin"]]
    lines += ['   SurfaceSkin 0 %d "%s"' % (i, spec["skin"]) for i in range(nsurf)]
    lines += ["   Scale %s %s %s" % (scale, scale, scale),
              "   AngleOffset %s" % spec.get("yaw", YAW_OFFSET),
              "   NOINTERPOLATION"]
    lines += ["   " + f for f in spec.get("flags", [])]
    lines += ["   FrameIndex %s %s 0 %d" % (spec["sprite"], chr(ord('A') + i), i)
              for i in range(len(frames))]
    lines += ["}", ""]
    return md3, "\n".join(lines), [(spec["sprite"], chr(ord('A') + i)) for i in range(len(frames))]


os.makedirs(OUT_DIR, exist_ok=True)
print("cube world export ->", PK3)
md3s, blocks, sprite_names, skins = [], [], [], set()
for spec in MODELS:
    path, block, names = build_model(spec)
    md3s.append(path); blocks.append(block); sprite_names += names
    skins.add((spec["skin"], spec["skin_src"]))

MODELDEF = "// Generated by cubekit/gz_world.py from %s. Do not edit by hand.\n" % os.path.basename(PROFILE)
MODELDEF += "\n".join(blocks)

with zipfile.ZipFile(os.path.join(OUT_DIR, PK3), "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("zscript.txt", ZSCRIPT)
    z.writestr("modeldef." + LUMP, MODELDEF)
    z.writestr("mapinfo." + LUMP, MAPINFO)
    if globals().get("GLDEFS"):
        z.writestr("gldefs." + LUMP, GLDEFS)
    for path in md3s:
        z.write(path, "%s/%s" % (MODEL_PATH, os.path.basename(path)))
    for skin, src in sorted(skins):
        z.write(src, "%s/%s" % (MODEL_PATH, skin))
    for spr, letter in sprite_names:
        z.writestr("sprites/%s%s0.png" % (spr, letter), PIXEL)
print("pk3", os.path.join(OUT_DIR, PK3), "-", len(md3s), "models,", len(sprite_names), "sprite frames")
