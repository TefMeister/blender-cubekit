# Forge models -> Blender objects, one object per part, one small palette texture, unlit like every cubekit model
# (what you see is the colour the game gets). Plus a few preview renders.
import math
import os

import bpy
from mathutils import Vector

from cube_size import VOXEL_M


def to_bl(p, pivot):
    """Forge axes (x = muzzle, y = left, z = up) -> Blender (gun points along +Y), as bl.Space does."""
    return Vector((-(p[1] - pivot[1]) * VOXEL_M, (p[0] - pivot[0]) * VOXEL_M, (p[2] - pivot[2]) * VOXEL_M))


def _material(name, img):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Closest'
    nt.links.new(tex.outputs[0], em.inputs[0])
    nt.links.new(em.outputs[0], out.inputs[0])
    nt.nodes.active = tex
    return mat


def build(model, png_path, collection_name=None):
    """Make the model's objects in the current scene. Returns {part: object}."""
    faces = model.faces()
    pal = {}
    for _, _, _, rgb in faces:
        key = tuple(int(round(c)) for c in rgb)
        if key not in pal:
            pal[key] = len(pal)
    side = max(1, math.ceil(math.sqrt(len(pal))))
    img = bpy.data.images.new(model.name + "_palette", side, side, alpha=False)
    px = [0.0] * (side * side * 4)
    for rgb, i in pal.items():
        for n in range(3):
            px[i * 4 + n] = rgb[n] / 255.0                       # a byte image keeps sRGB as it is (as atlas.py)
        px[i * 4 + 3] = 1.0
    img.pixels.foreach_set(px)
    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    img.filepath_raw = png_path
    img.file_format = 'PNG'
    img.save()
    img.filepath = png_path
    mat = _material(model.name + "_cubes", img)

    col = bpy.data.collections.new(collection_name or model.name)
    bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.new(model.name + "_root", None)
    col.objects.link(root)
    parts = {}
    for part, corners, d, rgb in faces:
        parts.setdefault(part, []).append((corners, d, rgb))
    objs = {}
    for part, fs in parts.items():
        verts, polys, uvs = [], [], []
        for corners, d, rgb in fs:
            i = pal[tuple(int(round(c)) for c in rgb)]
            u, v = ((i % side) + 0.5) / side, ((i // side) + 0.5) / side
            pts = [to_bl(c, model.pivot) for c in corners]
            want = Vector((-d[1], d[0], d[2]))
            if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(want) < 0:
                pts.reverse()
            base = len(verts)
            verts += pts
            polys.append([base, base + 1, base + 2, base + 3])
            uvs += [(u, v)] * 4
        me = bpy.data.meshes.new(model.name + "_" + part)
        me.from_pydata([tuple(p) for p in verts], [], polys)
        me.update()
        uvl = me.uv_layers.new(name="UVMap")
        uvl.data.foreach_set("uv", [c for uv in uvs for c in uv])
        me.materials.append(mat)
        ob = bpy.data.objects.new(model.name + "_" + part, me)
        col.objects.link(ob)
        ob.parent = root
        objs[part] = ob
    # merge each part's shared corners so it is one solid piece to select and move
    for ob in objs.values():
        me = ob.data
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=VOXEL_M * 0.01)
        bm.to_mesh(me)
        bm.free()
    return objs, len(faces), len(pal)


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for ident in ('BLENDER_WORKBENCH',):
        try:
            sc.render.engine = ident
        except TypeError as e:
            print("ENGINE", e)
    sh = sc.display.shading
    sh.light = 'FLAT'
    ct = [i.identifier for i in sh.bl_rna.properties['color_type'].enum_items]
    sh.color_type = 'TEXTURE' if 'TEXTURE' in ct else ct[0]
    sh.show_object_outline = False
    try:
        sc.view_settings.view_transform = 'Standard'
    except TypeError:
        pass
    w = bpy.data.worlds.new("bg")
    sc.world = w
    w.color = (0.30, 0.31, 0.36)
    sc.render.film_transparent = False
    return sc


def render_views(objs, out_dir, name, res=900):
    """Left side, right side, the player's view from behind the right hand, and a front three-quarter."""
    sc = bpy.context.scene
    pts = [o.matrix_world @ Vector(c) for o in objs.values() for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    mid = (lo + hi) / 2
    size = max((hi - lo).x, (hi - lo).y, (hi - lo).z)
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    views = {
        'left': (Vector((-1, 0, 0.0)), 'ORTHO', (2, 1)),
        'right': (Vector((1, 0, 0.0)), 'ORTHO', (2, 1)),
        'player': (Vector((-0.25, -1, 0.35)), 'PERSP', (4, 3)),
        'front34': (Vector((-0.8, 0.9, 0.45)), 'PERSP', (4, 3)),
        'top': (Vector((0, 0, 1)), 'ORTHO', (2, 1)),
        'close': (Vector((-0.7, -0.55, 0.45)), 'CLOSE', (4, 3)),
    }
    out = []
    for vname, (d, kind, aspect) in views.items():
        sc.render.resolution_x = res * aspect[0] // max(aspect)
        sc.render.resolution_y = res * aspect[1] // max(aspect)
        d = d.normalized()
        if kind == 'CLOSE':                          # the middle of the gun (its pivot: grip and action) up close
            cam_data.type = 'PERSP'
            cam_data.lens = 50
            focus = Vector((0, 0, 0))
            cam.location = focus + d * size * 0.62
            look = (focus - cam.location).normalized()
            cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
            cam_data.clip_start = size * 0.005
            cam_data.clip_end = size * 20
            p = os.path.join(out_dir, "%s_%s.png" % (name, vname))
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            out.append(p)
            continue
        cam_data.type = kind
        if kind == 'ORTHO':
            ext = hi - lo
            hor, ver = ext.y, (ext.x if abs(d.z) > 0.99 else ext.z)
            cam_data.ortho_scale = max(hor, ver * aspect[0] / aspect[1]) * 1.1
            cam.location = mid + d * size * 3
        else:
            cam_data.lens = 50
            cam.location = mid + d * size * 1.25
        look = (mid - cam.location).normalized()
        if abs(d.z) > 0.99:                          # straight down: muzzle to the right of the picture
            cam.rotation_euler = (0.0, 0.0, math.radians(90))
        else:
            cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
        cam_data.clip_start = size * 0.01
        cam_data.clip_end = size * 20
        p = os.path.join(out_dir, "%s_%s.png" % (name, vname))
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        out.append(p)
    bpy.data.objects.remove(cam)
    return out
