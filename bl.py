# Cubes -> Blender objects, flat unlit rendering, stop-motion keys.
#
# Lifted from the cube pistol's vp_blender.py (2026-09-22) and made prop-agnostic: the
# cube size and the pivot are arguments, and nothing here knows about guns or rust.
import bpy, math
from mathutils import Vector
from atlas import greedy_quads, Atlas, hash01


def value_noise(x, y, z, scale, seed):
    fx, fy, fz = x / scale, y / scale, z / scale
    ix, iy, iz = math.floor(fx), math.floor(fy), math.floor(fz)
    tx, ty, tz = fx - ix, fy - iy, fz - iz
    s = lambda t: t * t * (3 - 2 * t)
    tx, ty, tz = s(tx), s(ty), s(tz)
    acc = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (tx if dx else 1 - tx) * (ty if dy else 1 - ty) * (tz if dz else 1 - tz)
                acc += w * hash01(ix + dx, iy + dy, iz + dz, seed)
    return acc


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def scale_rgb(c, k):
    return tuple(min(255.0, v * k) for v in c)


class Space:
    """Turns voxel points into Blender metres about a chosen pivot cube."""

    def __init__(self, voxel_m, pivot):
        self.m, self.pivot = voxel_m, pivot

    def to_bl(self, px, py, pz):
        return Vector((-(py - self.pivot[1]) * self.m,
                       (px - self.pivot[0]) * self.m,
                       (pz - self.pivot[2]) * self.m))


def _unlit_material(name, img, alpha=None):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Closest'
    nt.links.new(tex.outputs[0], em.inputs[0])
    if alpha is None:
        nt.links.new(em.outputs[0], out.inputs[0])
    else:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mixn = nt.nodes.new('ShaderNodeMixShader')
        mixn.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mixn.inputs[1])
        nt.links.new(em.outputs[0], mixn.inputs[2])
        nt.links.new(mixn.outputs[0], out.inputs[0])
        for attr, val in (("surface_render_method", 'BLENDED'), ("blend_method", 'BLEND')):
            try: setattr(mat, attr, val)
            except (AttributeError, TypeError): pass
        try: mat.show_transparent_back = False
        except AttributeError: pass
    nt.nodes.active = tex
    return mat


def make_objects(specs, parent, png_path, space, shade=None, noise=None, alpha_of=None):
    """specs: [(name, {cell: sRGB}, origin_vox)]. One shared texture atlas for all of them.
    alpha_of: {object name: alpha} for the ones that must be see-through."""
    atlas = Atlas()
    per = []
    for name, cells, origin in specs:
        qs = [(corners, d, atlas.add(rows)) for corners, d, rows in greedy_quads(cells, shade, noise)]
        per.append((name, origin, qs))
    atlas.pack()
    img = bpy.data.images.new("cube_atlas", atlas.w, atlas.h, alpha=False)
    img.pixels.foreach_set(atlas.pixels())
    img.filepath_raw = png_path; img.file_format = 'PNG'; img.save()
    img.filepath = png_path
    alpha_of = alpha_of or {}
    mat = _unlit_material("cube_unlit", img)
    see_through = {a: _unlit_material("cube_glass_%.2f" % a, img, a) for a in set(alpha_of.values())}

    objs = {}
    for name, origin, qs in per:
        o = space.to_bl(*origin)
        verts, polys, uvs = [], [], []
        for corners, d, idx in qs:
            u0, v0, u1, v1 = atlas.uv_rect(idx)
            quv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            pts = [space.to_bl(*c) - o for c in corners]
            want = Vector((-d[1], d[0], d[2]))
            if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(want) < 0:
                pts.reverse(); quv.reverse()
            base = len(verts)
            verts += pts
            polys.append([base, base + 1, base + 2, base + 3])
            uvs += quv
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], polys); me.update()
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(see_through[alpha_of[name]] if name in alpha_of else mat)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = parent
        ob.location = o
        objs[name] = ob
    print("faces", sum(len(q) for _, _, q in per), "atlas", atlas.w, "x", atlas.h)
    return objs


ENGINES = {'WORKBENCH': ['BLENDER_WORKBENCH'],
           'EEVEE': ['BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE']}


def setup_scene(frame_end, res=(1000, 1400), bg=(0.05, 0.05, 0.09), fps=35, engine='WORKBENCH'):
    """engine: WORKBENCH for solid props, EEVEE when something must be seen through.
    Either way every material is pure emission, so nothing is lit - what you see is the
    texture the game gets."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for ident in ENGINES[engine]:
        try:
            sc.render.engine = ident
            break
        except TypeError as e:
            print("ENGINE", ident, e)
    sh = sc.display.shading
    sh.light = 'FLAT'
    ct = [i.identifier for i in sh.bl_rna.properties['color_type'].enum_items]
    sh.color_type = 'TEXTURE' if 'TEXTURE' in ct else ct[0]
    sh.show_object_outline = False
    try: sc.view_settings.view_transform = 'Standard'
    except TypeError: pass
    w = bpy.data.worlds.new("bg"); sc.world = w; w.color = bg
    w.use_nodes = True
    for n in w.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs[0].default_value = (bg[0], bg[1], bg[2], 1.0)
            n.inputs[1].default_value = 1.0
    if engine == 'EEVEE':
        for attr, val in (("taa_render_samples", 8), ("use_raytracing", False)):
            try: setattr(sc.eevee, attr, val)
            except (AttributeError, TypeError): pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 1, frame_end
    return sc


def key(obj, frame, loc=None, rot_deg=None, hide=None):
    if loc is not None:
        obj.location = loc; obj.keyframe_insert("location", frame=frame)
    if rot_deg is not None:
        obj.rotation_euler = [math.radians(a) for a in rot_deg]
        obj.keyframe_insert("rotation_euler", frame=frame)
    if hide is not None:
        obj.hide_viewport = obj.hide_render = hide
        obj.keyframe_insert("hide_viewport", frame=frame)
        obj.keyframe_insert("hide_render", frame=frame)


def all_constant():
    """Stop-motion: no blending between keys."""
    for act in bpy.data.actions:
        curves = list(getattr(act, "fcurves", []) or [])
        for layer in getattr(act, "layers", []):
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves += list(bag.fcurves)
        for fc in curves:
            for k in fc.keyframe_points:
                k.interpolation = 'CONSTANT'


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---- pick mode: every cube on its own, so one click + L selects exactly one cube (Tefa, 2026-10-03) ----
# The build merges neighbouring faces of one colour into big quads (fewer faces for the game). That is
# right for the game but wrong for editing: a click lands on a strip covering many cubes. This cuts
# every merged quad back into 1x1 cube faces and makes each cube's faces share corners only with each
# other, so in edit mode 'select linked' (L) under the mouse grabs exactly one cube. The look is the
# same: the texture coordinates are cut with the faces. ⚠️ Keep pick-mode meshes OUT of the .blend
# the game export reads (gz_world and the kit's gz_export read the mesh as it is in the file): save a
# pick-mode scene as <name>_pick.blend. pick_mode.py does that for any cube .blend.
def split_to_cubes(ob, voxel_m):
    """Replace ob's mesh with the per-cube version. Object, parent, keys, material and name stay.
    Returns (cubes, faces)."""
    import math
    me = ob.data
    if not me.polygons:
        return 0, 0
    uvl = me.uv_layers.active
    if uvl and len(uvl.data) != len(me.loops):      # seen 2026-10-03: a layer that reports no data until
        me.update()                                  # the mesh is evaluated; read it from the evaluated copy
        uvl = me.uv_layers.active
        if len(uvl.data) != len(me.loops):
            ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            uvl = ev.uv_layers.active
    uvdata = [d.uv.copy() for d in uvl.data] if uvl and len(uvl.data) == len(me.loops) else None
    # the cube grid is a constant fraction of a cube off the object's origin (PIVOT need not be whole);
    # every corner shares that fraction, so take it from the first vertex and work in whole cubes
    c0 = me.vertices[0].co
    off = [c0[i] / voxel_m - math.floor(c0[i] / voxel_m + 1e-6) for i in range(3)]
    grid = lambda v: [v[i] / voxel_m - off[i] for i in range(3)]
    verts, vidx, polys, uvs, cubes = [], {}, [], [], set()
    for poly in me.polygons:
        ls = list(poly.loop_indices)
        p = [me.vertices[me.loops[l].vertex_index].co.copy() for l in ls]
        t = [uvdata[l] for l in ls] if uvdata else [Vector((0, 0))] * len(ls)
        if len(ls) != 4:                                   # not a cube face: copy it untouched
            ids = []
            for pt, uv in zip(p, t):
                key = ("raw", tuple(round(c, 3) for c in grid(pt)))
                if key not in vidx:
                    vidx[key] = len(verts); verts.append(pt)
                ids.append(vidx[key]); uvs.append(uv)
            polys.append(ids)
            continue
        n = poly.normal
        e1, e3 = p[1] - p[0], p[3] - p[0]
        ns, nt = max(1, round(e1.length / voxel_m)), max(1, round(e3.length / voxel_m))
        for i in range(ns):
            for j in range(nt):
                centre = p[0] + e1 * ((i + 0.5) / ns) + e3 * ((j + 0.5) / nt) - n * (0.5 * voxel_m)
                cell = tuple(math.floor(c) for c in grid(centre))       # the cube this face belongs to
                cubes.add(cell)
                ids = []
                for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                    s, tt = a / ns, b / nt
                    pt = p[0] + e1 * s + e3 * tt
                    key = (cell, tuple(round(c) for c in grid(pt)))
                    if key not in vidx:
                        vidx[key] = len(verts); verts.append(pt)
                    ids.append(vidx[key])
                    uvs.append(t[0] + (t[1] - t[0]) * s + (t[3] - t[0]) * tt)
                polys.append(ids)
    me2 = bpy.data.meshes.new(me.name)
    me2.from_pydata(verts, [], polys); me2.update()
    layer = me2.uv_layers.new(name="UVMap")
    for li, uv in enumerate(uvs):
        layer.data[li].uv = uv
    for m in me.materials:
        me2.materials.append(m)
    ob.data = me2
    if me.users == 0:
        bpy.data.meshes.remove(me)
    for coll in (me2.polygons, me2.edges, me2.vertices):
        coll.foreach_set("select", [False] * len(coll))
    return len(cubes), len(me2.polygons)


def pick_mode_all(voxel_m):
    """split_to_cubes on every mesh object in the scene. Returns {name: (cubes, faces)}."""
    out = {}
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.data.polygons:
            if pick_mode_check(ob, voxel_m):           # already per-cube: leave it
                out[ob.name] = (None, len(ob.data.polygons))
            else:
                out[ob.name] = split_to_cubes(ob, voxel_m)
    return out


def pick_mode_check(ob, voxel_m=None):
    """True when every face is a single 1x1 cube face (no merged strips, no squashed faces) and no two
    cubes share a corner (every connected piece of the mesh has at most 8 corners)."""
    me = ob.data
    if voxel_m:
        for poly in me.polygons:
            vs = [me.vertices[i].co for i in poly.vertices]
            if len(vs) != 4:
                return False
            for a, b in zip(vs, vs[1:] + vs[:1]):
                if abs((a - b).length / voxel_m - 1.0) > 0.02:
                    return False
    parent = list(range(len(me.vertices)))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for poly in me.polygons:
        r = find(poly.vertices[0])
        for v in poly.vertices[1:]:
            parent[find(v)] = r
    sizes = {}
    for v in range(len(me.vertices)):
        r = find(v); sizes[r] = sizes.get(r, 0) + 1
    return max(sizes.values(), default=0) <= 8
