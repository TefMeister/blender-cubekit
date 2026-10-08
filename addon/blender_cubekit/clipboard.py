# Picking a whole block (L), and copy / cut / paste of picked cubes (Ctrl + C / X / V).
# Moved out of __init__.py unchanged on 2026-10-08 (file size rule).
import bpy

from . import _kit, _edit_objects

_clip = {}            # the last copy: what Ctrl + V pastes
_glue = {}            # the side the last L was pressed on: {"ob", "cell", "dir"}


def _hover_side(context, event):
    """(object, bmesh, cell, dir) of the cube side under the mouse, among the parts in edit mode,
    or None."""
    import bmesh
    from bpy_extras import view3d_utils
    from mathutils.bvhtree import BVHTree
    region, rv3d = context.region, context.region_data
    if rv3d is None:
        return None
    co = (event.mouse_region_x, event.mouse_region_y)
    origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, co)
    ray = view3d_utils.region_2d_to_vector_3d(region, rv3d, co)
    best = None
    for ob in _edit_objects(context):
        bm = bmesh.from_edit_mesh(ob.data)
        bm.faces.ensure_lookup_table()
        inv = ob.matrix_world.inverted()
        hit, _n, idx, _dist = BVHTree.FromBMesh(bm).ray_cast(inv @ origin, (inv.to_3x3() @ ray).normalized())
        if hit is None:
            continue
        dist = (ob.matrix_world @ hit - origin).length
        if best is None or dist < best[0]:
            best = (dist, ob, bm, idx)
    if best is None or not best[1].get("cubekit_voxel_m"):
        return None
    _d, ob, bm, idx = best
    f = bm.faces[idx]
    return ob, bm, _cell_of(ob, f), _dir_of_face(f)


def _dir_of_face(f):
    n = f.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    d = [0, 0, 0]
    d[ax] = 1 if n[ax] > 0 else -1
    return tuple(d)


def _cell_of(ob, f):
    import math
    v = ob["cubekit_voxel_m"]
    off = list(ob.get("cubekit_off", (0.0, 0.0, 0.0)))
    d = _dir_of_face(f)
    c = f.calc_center_median()
    return tuple(math.floor((c[i] - 0.5 * v * d[i]) / v - off[i]) for i in range(3))


def _unpick_all(context):
    import bmesh
    for o in _edit_objects(context):
        b = bmesh.from_edit_mesh(o.data)
        for f in b.faces:
            f.select = False
        b.select_flush(False)
        bmesh.update_edit_mesh(o.data, loop_triangles=False, destructive=False)


class CUBEKIT_OT_pick_block(bpy.types.Operator):
    """L: pick the whole block under the mouse: the cube there and every cube joined to it, side to
side, inside the same part. A loose plate or bit picks on its own; a cube joined to the main body
picks the whole body (Tefa, 2026-10-06). The side pressed on becomes the glue side for Ctrl + C"""
    bl_idname = "cubekit.pick_block"
    bl_label = "Pick the whole block under the mouse"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        import bmesh
        hov = _hover_side(context, event)
        if hov is None:
            self.report({'WARNING'}, "no cube under the mouse")
            return {'CANCELLED'}
        ob, bm, start, d = hov
        _glue.clear()
        _glue.update(ob=ob.name, cell=start, dir=d)
        faces_of = {}
        for f in bm.faces:
            faces_of.setdefault(_cell_of(ob, f), []).append(f)
        flat = list(ob.get("cubekit_cells", ()))
        cells = {tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)} if flat else set(faces_of)
        cells.add(start)
        block, stack = {start}, [start]
        while stack:
            c = stack.pop()
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (c[0] + dx, c[1] + dy, c[2] + dz)
                if nb in cells and nb not in block:
                    block.add(nb)
                    stack.append(nb)
        for c in block:
            for f in faces_of.get(c, ()):
                f.select = True
        bm.select_flush(True)
        bmesh.update_edit_mesh(ob.data, loop_triangles=False, destructive=False)
        self.report({'INFO'}, "picked a block of %d cubes" % len(block))
        return {'FINISHED'}


class CUBEKIT_OT_copy(bpy.types.Operator):
    """Ctrl + C: copy the picked cubes. The glue side is the side under the mouse if it belongs to a
picked cube, otherwise the side the last L was pressed on"""
    bl_idname = "cubekit.copy"
    bl_label = "Copy the picked cubes"
    CUT = False

    def invoke(self, context, event):
        import bmesh
        _, edit, _V = _kit()
        hov = _hover_side(context, event)
        picked = {}
        for ob in _edit_objects(context):
            bm = bmesh.from_edit_mesh(ob.data)
            cells = {_cell_of(ob, f) for f in bm.faces if f.select}
            if cells:
                picked[ob.name] = cells
        if not picked:
            self.report({'WARNING'}, "nothing picked: pick a block first (L)")
            return {'CANCELLED'}
        if hov and hov[2] in picked.get(hov[0].name, ()):
            name, cell, d = hov[0].name, hov[2], hov[3]
        elif _glue and _glue["cell"] in picked.get(_glue["ob"], ()):
            name, cell, d = _glue["ob"], _glue["cell"], _glue["dir"]
        else:
            self.report({'WARNING'}, "point at a side of the picked cubes: that side is what gets glued")
            return {'CANCELLED'}
        ob = bpy.data.objects[name]
        bpy.ops.object.mode_set(mode='OBJECT')
        try:
            clip = edit.copy_cubes(ob, ob["cubekit_voxel_m"], picked[name], cell, d)
            if self.CUT:
                edit.drop(ob, ob["cubekit_voxel_m"], picked[name])
        finally:
            bpy.ops.object.mode_set(mode='EDIT')
        _clip.clear()
        _clip.update(clip)
        self.report({'INFO'}, "%s %d cubes; Ctrl + V on a side glues them there"
                    % ("cut" if self.CUT else "copied", len(clip["cells"])))
        return {'FINISHED'}


class CUBEKIT_OT_cut(CUBEKIT_OT_copy):
    """Ctrl + X: like Ctrl + C, and the picked cubes are taken away. Ctrl + V puts them back
wherever you point"""
    bl_idname = "cubekit.cut"
    bl_label = "Cut the picked cubes"
    bl_options = {'REGISTER', 'UNDO'}
    CUT = True


class CUBEKIT_OT_paste(bpy.types.Operator):
    """Ctrl + V: paste the copy onto the side under the mouse. It lands just outside that side,
turned so its glue side lies flat against it. The pasted cubes come up picked"""
    bl_idname = "cubekit.paste"
    bl_label = "Paste the copied cubes"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        if not _clip:
            self.report({'WARNING'}, "nothing copied yet: pick a block (L), then Ctrl + C")
            return {'CANCELLED'}
        _, edit, _V = _kit()
        hov = _hover_side(context, event)
        if hov is None:
            self.report({'WARNING'}, "point at the side to paste onto")
            return {'CANCELLED'}
        ob, _bm, cell, d = hov
        _unpick_all(context)                      # only the pasted cubes come up picked
        bpy.ops.object.mode_set(mode='OBJECT')
        try:
            n = edit.paste_cubes(ob, ob["cubekit_voxel_m"], _clip, cell, d)
        except ValueError as e:
            bpy.ops.object.mode_set(mode='EDIT')
            self.report({'WARNING'}, str(e))
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, "pasted %d cubes" % n)
        return {'FINISHED'}
