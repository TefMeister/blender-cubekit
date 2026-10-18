# Carved wear for cube weapons (Tefa, 2026-10-18): scratches, chipped edges and pits made by REMOVING
# the kit's smallest cubes (0.85 mm) from the surface, not by painting. Uses CubeKit 0.18.0's smaller
# cubes inside one model.
#   blender -b <in.blend> --python carve_wear.py -- <out.blend> <render folder> [seed]
# Merged models are first cut into single cubes (the kit's "Every cube on its own"). Hands, flashes,
# casings and shells are left alone. Seeded: the same seed gives the same carving.
import math
import os
import random
import sys
import zlib

import bpy
from mathutils import Vector

KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KIT)
import bl  # noqa: E402
import edit  # noqa: E402
import edit_small as small  # noqa: E402
from edit import DIRS, FINE  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, RENDERS = argv[0], argv[1]
SEED = int(argv[2]) if len(argv) > 2 else 2063
STAGE = argv[3] if len(argv) > 3 else "both"     # both / before / after

# ---- every number has a name ----
FILE_MM = 3.4                 # the cube size of a model not yet marked with its own
CARVE_MM = 0.85               # the smallest cube the kit allows: every cut is this size
SCRATCH_PER_CM2 = 0.45        # scratches per cm2 of metal surface
SOFT_SCRATCH_PER_CM2 = 0.25   # on wood and painted parts
SCRATCH_MM = (2.5, 13.0)      # scratch length range
ALONG_SHARE = 0.65            # share of scratches running along the gun
ALONG_SPREAD_DEG = 15         # how far those may lean off the gun's length
GOUGE_SHARE = 0.18            # share of scratches cut two cubes deep in their middle third
CHIP_PER_CM = 0.35            # chipped stretches per cm of outside edge
SOFT_CHIP_PER_CM = 0.55       # wood and paint chip more
CHIP_RUN = (1, 5)             # a chipped stretch, in small cubes along the edge
CHIP_DEEP_SHARE = 0.25        # share of chips that bite one cube deeper
PIT_PER_CM2 = 0.18            # pit groups per cm2
PIT_GROUP = (1, 4)            # small cubes in one pit group
DARK_SKIP = 20 / 255.0        # bore and port insides stay untouched
MIN_FACES = 60                # parts smaller than this (a trigger) are left alone
SKIP = ("hand", "flash", "casing", "shell")
CLOSE = 0.42                  # close-up camera: this fraction of the normal camera distance


def is_soft(rgb):
    """Wood or coloured paint (warm), as against grey or black metal."""
    r, g, b = rgb
    return r - b > 0.07 and r > 0.12


def solid_at(s, p):
    return small.occupied(s, p)


def carve(s, p, u):
    """Remove the small cube of size u (fine units) at fine position p. True if one went."""
    cell, idx = small.split_fpos(p)
    if cell in s.cells:
        small.make_small(s, cell, half=True)
    fc = s.fine.get(cell)
    if not fc:
        return False
    o = small.octant(idx)
    if u == 1:
        if idx not in fc.subs:
            return False
        fc.half.discard(o)
        small._take_unit(s, cell, idx, 1)
    else:
        quarters = small.octant_subs(o)
        if not any(i in fc.subs for i in quarters):
            return False
        small._take_unit(s, cell, quarters[0], 2)
    return True


def surface(s, p, d, u):
    """Solid at p with air straight outside it along d."""
    return solid_at(s, p) and not solid_at(s, tuple(p[i] + d[i] * u for i in range(3)))


def layer(cell, d, ax, u):
    return FINE * cell[ax] + (FINE - u if d[ax] > 0 else 0)


def snap(x, u):
    return int(math.floor(x / u)) * u


def carve_object(ob, rng):
    v = ob.get("cubekit_voxel_m", FILE_MM / 1000.0)
    u = max(1, round(CARVE_MM / (v * 1000.0 / FINE)))
    s = edit.Solid(ob, v)
    cells = s.cells
    lo = [min(c[i] for c in cells) for i in range(3)]
    hi = [max(c[i] for c in cells) for i in range(3)]
    long_ax = max(range(3), key=lambda i: hi[i] - lo[i])
    faces, soft = [], {}
    edges = []
    for cell in cells:
        rgb = s.cell_rgb.get(cell, edit.UNPAINTED)
        if max(rgb) < DARK_SKIP:
            continue
        soft[cell] = is_soft(rgb)
        out = [d for d in DIRS if (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2]) not in cells]
        for d in out:
            if max(s.colour_of(cell, d)) >= DARK_SKIP:
                faces.append((cell, d))
        for i, d1 in enumerate(out):
            for d2 in out[i + 1:]:
                if sum(abs(a * b) for a, b in zip(d1, d2)) == 0:
                    edges.append((cell, d1, d2))
    if not faces:
        return None
    face_cm2 = (v * 100.0) ** 2
    metal = [f for f in faces if not soft[f[0]]]
    softf = [f for f in faces if soft[f[0]]]
    stats = {"scratches": 0, "chips": 0, "pits": 0, "cubes": 0}

    def cut(p):
        if carve(s, p, u):
            stats["cubes"] += 1
            return True
        return False

    def scratch(cell, d):
        ax = [i for i in range(3) if d[i]][0]
        ua, va = [i for i in range(3) if i != ax]
        p0 = [0, 0, 0]
        p0[ax] = layer(cell, d, ax, u)
        p0[ua] = FINE * cell[ua] + u * rng.randrange(FINE // u)
        p0[va] = FINE * cell[va] + u * rng.randrange(FINE // u)
        if long_ax in (ua, va) and rng.random() < ALONG_SHARE:
            base = 0.0 if long_ax == ua else 90.0
            ang = math.radians(base + rng.uniform(-ALONG_SPREAD_DEG, ALONG_SPREAD_DEG))
        else:
            ang = rng.uniform(0, math.pi)
        n = max(2, int(rng.uniform(*SCRATCH_MM) / CARVE_MM))
        gouge = rng.random() < GOUGE_SHARE
        last, made = None, 0
        for k in range(n):
            q = list(p0)
            q[ua] = snap(p0[ua] + k * u * math.cos(ang), u)
            q[va] = snap(p0[va] + k * u * math.sin(ang), u)
            q = tuple(q)
            if q == last:
                continue
            last = q
            if not surface(s, q, d, u):
                break
            cut(q)
            made += 1
            if gouge and n / 3 <= k < 2 * n / 3:
                cut(tuple(q[i] - d[i] * u for i in range(3)))
        if made:
            stats["scratches"] += 1

    def chip(cell, d1, d2):
        a1 = [i for i in range(3) if d1[i]][0]
        a2 = [i for i in range(3) if d2[i]][0]
        e = 3 - a1 - a2
        p0 = [0, 0, 0]
        p0[a1] = layer(cell, d1, a1, u)
        p0[a2] = layer(cell, d2, a2, u)
        p0[e] = FINE * cell[e] + u * rng.randrange(FINE // u)
        run = rng.randint(*CHIP_RUN)
        deep = rng.random() < CHIP_DEEP_SHARE
        made = 0
        for k in range(run):
            q = list(p0)
            q[e] += k * u
            q = tuple(q)
            if not (surface(s, q, d1, u) and surface(s, q, d2, u)):
                break
            cut(q)
            made += 1
            if deep:
                dd = d1 if rng.random() < 0.5 else d2
                cut(tuple(q[i] - dd[i] * u for i in range(3)))
        if made:
            stats["chips"] += 1

    def pit(cell, d):
        ax = [i for i in range(3) if d[i]][0]
        ua, va = [i for i in range(3) if i != ax]
        q = [0, 0, 0]
        q[ax] = layer(cell, d, ax, u)
        q[ua] = FINE * cell[ua] + u * rng.randrange(FINE // u)
        q[va] = FINE * cell[va] + u * rng.randrange(FINE // u)
        made = 0
        for _ in range(rng.randint(*PIT_GROUP)):
            if surface(s, tuple(q), d, u):
                cut(tuple(q))
                made += 1
            q[rng.choice((ua, va))] += u * rng.choice((-1, 1))
        if made:
            stats["pits"] += 1

    jobs = []
    for pool, dens in ((metal, SCRATCH_PER_CM2), (softf, SOFT_SCRATCH_PER_CM2)):
        for _ in range(int(round(len(pool) * face_cm2 * dens))):
            jobs.append((scratch, rng.choice(pool)))
    for _ in range(int(round(len(faces) * face_cm2 * PIT_PER_CM2))):
        jobs.append((pit, rng.choice(faces)))
    edge_cm = v * 100.0
    for e in edges:
        dens = SOFT_CHIP_PER_CM if soft[e[0]] else CHIP_PER_CM
        if rng.random() < dens * edge_cm:
            jobs.append((chip, e))
    rng.shuffle(jobs)
    for fn, args in jobs:
        fn(*args)
    small.tidy(s)
    f0 = len(ob.data.polygons)
    s.write()
    stats.update(faces_before=f0, faces_after=len(ob.data.polygons), cube_mm=round(v * 1000, 2),
                 cut_mm=round(u * v * 1000 / FINE, 2))
    return stats


def setup_view():
    sc = bpy.context.scene
    try:
        sc.render.engine = 'BLENDER_WORKBENCH'
    except TypeError as e:
        print("ENGINE", e)
    sh = sc.display.shading
    sh.light = 'FLAT'
    sh.color_type = 'VERTEX'
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type == 'VIEW_3D':
                for sp in area.spaces:
                    if sp.type == 'VIEW_3D':
                        sp.shading.type = 'SOLID'
                        sp.shading.light = 'FLAT'
                        sp.shading.color_type = 'VERTEX'


def targets():
    out = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or not ob.data.polygons or ob.hide_render:
            continue
        if any(k in ob.name.lower() for k in SKIP):
            continue
        out.append(ob)
    return out


def render_all(tag):
    os.makedirs(RENDERS, exist_ok=True)
    sc = bpy.context.scene
    cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
    vis = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
    pts = [o.matrix_world @ Vector(c) for o in vis for c in o.bound_box]
    centre = sum(pts, Vector()) / max(1, len(pts))
    for cam in cams:
        sc.camera = cam
        sc.render.filepath = os.path.join(RENDERS, "%s_%s.png" % (tag, cam.name))
        bpy.ops.render.render(write_still=True)
    for cam in cams:
        if cam.name.lower() in ("three_quarter", "side_left", "side_right", "side", "viewcam"):
            keep = cam.location.copy()
            if cam.data.type == 'ORTHO':
                ks = cam.data.ortho_scale
                cam.data.ortho_scale = ks * CLOSE
            else:
                fwd = cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))
                cam.location = keep + fwd * ((centre - keep).dot(fwd) * (1 - CLOSE))
            sc.camera = cam
            sc.render.filepath = os.path.join(RENDERS, "%s_%s_close.png" % (tag, cam.name))
            bpy.ops.render.render(write_still=True)
            cam.location = keep
            if cam.data.type == 'ORTHO':
                cam.data.ortho_scale = ks


# 1. every cube on its own, with its colours on the mesh (what the add-on's button does)
for ob in bpy.data.objects:
    if ob.type == 'MESH' and ob.data.polygons and not edit.has_colours(ob):
        if not bl.pick_mode_check(ob, FILE_MM / 1000.0):
            bl.split_to_cubes(ob, FILE_MM / 1000.0)
        edit.convert(ob, FILE_MM / 1000.0)
setup_view()
if STAGE in ("both", "before"):
    render_all("before")
if STAGE in ("both", "after"):
    for ob in targets():
        if len(ob.data.polygons) < MIN_FACES:
            print("CARVE %-24s left alone (small part)" % ob.name)
            continue
        rng = random.Random(SEED + zlib.crc32(ob.name.encode()))
        st = carve_object(ob, rng)
        print("CARVE %-24s %s" % (ob.name, st))
    render_all("after")
    bpy.context.scene["cubekit_carved"] = "carved wear, seed %d, 2026-10-18" % SEED
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("SAVED", OUT)
