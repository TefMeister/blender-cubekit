# The picking brush (left / right mouse), sides-or-whole-cubes (F) and the helpers they share.
# Moved out of __init__.py unchanged on 2026-10-08 (file size rule).
import math

import bpy

from . import _edit_objects

def _whole_cubes_of_selection(context, deselect_hits=None):
    """Whole cubes: grow the face selection to the cubes it touches (or, given the faces that were
    just un-picked, un-pick their whole cubes)."""
    import bmesh
    for ob in _edit_objects(context):
        bm = bmesh.from_edit_mesh(ob.data)
        if deselect_hits is None:
            seeds = [f for f in bm.faces if f.select]
            value = True
        else:
            seeds = [bm.faces[i] for i in deselect_hits.get(ob.name, ())]
            value = False
        bm.faces.ensure_lookup_table()
        seen = set()
        for f in seeds:
            if f.index in seen:
                continue
            stack = [f]
            while stack:
                g = stack.pop()
                if g.index in seen:
                    continue
                seen.add(g.index)
                g.select = value
                for v in g.verts:
                    for h in v.link_faces:
                        if h.index not in seen:
                            stack.append(h)
        if not value:
            bm.select_flush(False)
        bmesh.update_edit_mesh(ob.data, loop_triangles=False, destructive=False)


def _expand_groups(context):
    """Sides mode: a small square inside a 4-way split quarter that holds 16-way detail stands for
    its whole quarter, so picking one picks all four (and un-picking one un-picks all four)."""
    import bmesh
    for ob in _edit_objects(context):
        bm = bmesh.from_edit_mesh(ob.data)
        layer = bm.faces.layers.int.get("cubekit_group")
        if layer is None:
            continue
        on, off = set(), set()
        for f in bm.faces:
            g = f[layer]
            if g > 0:
                (on if f.select else off).add(g)
        mixed = on & off
        if not mixed:
            continue
        for f in bm.faces:
            if f[layer] in mixed:
                f.select = True
        bm.select_flush(True)
        bmesh.update_edit_mesh(ob.data, loop_triangles=False, destructive=False)


def _shrink_groups(context, before):
    """Un-picking: when one small square of a quarter was un-picked, un-pick the whole quarter."""
    import bmesh
    for ob in _edit_objects(context):
        bm = bmesh.from_edit_mesh(ob.data)
        layer = bm.faces.layers.int.get("cubekit_group")
        if layer is None:
            continue
        was = before.get(ob.name, set())
        dropped = {f[layer] for f in bm.faces if f[layer] > 0 and not f.select and f.index in was}
        if not dropped:
            continue
        for f in bm.faces:
            if f[layer] in dropped:
                f.select = False
        bm.select_flush(False)
        bmesh.update_edit_mesh(ob.data, loop_triangles=False, destructive=False)


def _picked_faces(context):
    import bmesh
    out = {}
    for ob in _edit_objects(context):
        bm = bmesh.from_edit_mesh(ob.data)
        out[ob.name] = {f.index for f in bm.faces if f.select}
    return out


def _draw_circle(self, context):
    import gpu
    from gpu_extras.batch import batch_for_shader
    if not getattr(self, "_drawing", False):
        return
    x, y, r = self._mouse[0], self._mouse[1], context.window_manager.cubekit_brush
    pts = [(x + r * math.cos(a), y + r * math.sin(a)) for a in
           [i * 2 * math.pi / 48 for i in range(49)]]
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pts})
    shader.bind()
    shader.uniform_float("color", (1.0, 0.6, 0.1, 1.0) if self.mode == 'ADD' else (1.0, 0.2, 0.2, 1.0))
    gpu.state.line_width_set(1.5)
    batch.draw(shader)
    gpu.state.line_width_set(1.0)


class CUBEKIT_OT_brush(bpy.types.Operator):
    """Left mouse: brush-pick cubes (or sides). Click picks the one under the mouse; hold and sweep
to pick more; the wheel while holding changes the brush size. Right mouse: the same, un-picking"""
    bl_idname = "cubekit.brush"
    bl_label = "Pick cubes with the brush"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(items=[('ADD', "pick", ""), ('SUB', "un-pick", "")], default='ADD')

    def _apply(self, context):
        wm = context.window_manager
        r = wm.cubekit_brush
        before = {}
        if wm.cubekit_whole and self.mode == 'SUB':
            import bmesh
            for o in _edit_objects(context):
                bm = bmesh.from_edit_mesh(o.data)
                before[o.name] = {f.index for f in bm.faces if f.select}
        sides_before = _picked_faces(context) if not wm.cubekit_whole and self.mode == 'SUB' else None
        bpy.ops.view3d.select_circle(x=self._mouse[0], y=self._mouse[1], radius=r,
                                     wait_for_input=False, mode=self.mode)
        if not wm.cubekit_whole:
            if self.mode == 'ADD':
                _expand_groups(context)
            else:
                _shrink_groups(context, sides_before)
        if wm.cubekit_whole:
            if self.mode == 'ADD':
                _whole_cubes_of_selection(context)
            else:
                import bmesh
                hits = {}
                for o in _edit_objects(context):
                    bm = bmesh.from_edit_mesh(o.data)
                    now = {f.index for f in bm.faces if f.select}
                    hits[o.name] = before.get(o.name, set()) - now
                _whole_cubes_of_selection(context, deselect_hits=hits)

    def invoke(self, context, event):
        if context.mode != 'EDIT_MESH':
            return {'PASS_THROUGH'}
        bpy.ops.mesh.select_mode(type='FACE')
        self._mouse = (event.mouse_region_x, event.mouse_region_y)
        self._start = self._mouse
        self._moved = False
        self._drawing = True
        self._button = 'LEFTMOUSE' if self.mode == 'ADD' else 'RIGHTMOUSE'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(_draw_circle, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        self._drawing = False
        context.area.tag_redraw()

    def modal(self, context, event):
        wm = context.window_manager
        if event.type == 'MOUSEMOVE':
            self._mouse = (event.mouse_region_x, event.mouse_region_y)
            if not self._moved and (abs(self._mouse[0] - self._start[0]) > 3 or abs(self._mouse[1] - self._start[1]) > 3):
                self._moved = True
            if self._moved:
                self._apply(context)
            context.area.tag_redraw()
        elif event.type in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE'):
            step = 4 if wm.cubekit_brush < 40 else 10
            wm.cubekit_brush = max(2, min(300, wm.cubekit_brush + (step if event.type == 'WHEELUPMOUSE' else -step)))
            if self._moved:
                self._apply(context)
            context.area.tag_redraw()
        elif event.type == self._button and event.value == 'RELEASE':
            if not self._moved:
                # a plain click: the one cube (or side) under the mouse
                if wm.cubekit_whole:
                    if self.mode == 'ADD':
                        bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT', deselect=False)
                    else:
                        bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT', deselect=True)
                else:
                    before = _picked_faces(context)
                    bpy.ops.view3d.select(location=self._mouse, extend=(self.mode == 'ADD'),
                                          deselect=(self.mode == 'SUB'))
                    if self.mode == 'ADD':
                        _expand_groups(context)
                    else:
                        _shrink_groups(context, before)
            self._finish(context)
            return {'FINISHED'}
        elif event.type == 'ESC':
            self._finish(context)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


class CUBEKIT_OT_toggle_whole(bpy.types.Operator):
    """F: sides only / whole cubes. Decides what a pick grabs and what a colour paints"""
    bl_idname = "cubekit.toggle_whole"
    bl_label = "Sides / whole cubes"

    def execute(self, context):
        wm = context.window_manager
        wm.cubekit_whole = not wm.cubekit_whole
        if wm.cubekit_whole and context.mode == 'EDIT_MESH':
            _whole_cubes_of_selection(context)
        self.report({'INFO'}, "picking WHOLE CUBES" if wm.cubekit_whole else "picking SIDES only")
        return {'FINISHED'}
