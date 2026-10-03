# CubeKit - the Blender side of blender-cubekit (github.com/TefMeister/blender-cubekit).
# Buttons and keys for pixel-style cube models. Everything here is also a script in the repo;
# the add-on only puts a button on it.
#
# Sidebar tab "CubeKit" (3D view, press N):
#   Colours on             the flat, unlit view - exactly what the game shows
#   Every cube on its own  cuts merged strips back into single cubes so single cubes can be picked,
#                          and gives the object its full cube list so cubes can be added and removed
#   Save pick copy         saves <file>_pick.blend beside the open file (the original stays lean)
#   the palette            colours; the brush button beside one paints the picked sides or cubes
#
# Keys, object mode:
#   L  (mouse over a cube)   picks exactly that one cube and drops you into edit mode.
# Keys, edit mode (after Tab), as asked for on 2026-10-03:
#   left mouse               brush: click picks the cube (or side) under the mouse, hold and sweep
#                            to pick more; the WHEEL while holding makes the brush bigger or smaller
#   right mouse              held: the brush un-picks instead
#   F                        sides only / whole cubes (what a pick grabs, and what a colour paints)
#   E                        add a cube outside every picked side; E E E builds a row
#   Q                        remove the cube behind every picked side (Q Q Q digs a row); with whole
#                            cubes picked, removes those cubes
#   R                        the whole model in view
#   Ctrl + wheel             brush circle bigger / smaller (the circle follows the mouse)
#   F5 / F6                  Blender's plain click-select / the edit-mesh menu (the old mouse jobs)
# Movement, always on, every mode (navigate.py): W A S D move, Z down, X up, Shift faster, middle
# mouse held turns your head. What those keys did before: F7 pick all, F8 scale, F9 shading wheel,
# F10 Blender's orbit, Delete key deletes.
#   Tab                      back out of edit mode
import math
import os
import sys

import bpy

bl_info = {   # read by Blender versions before 4.2; the manifest file is what 4.2+ reads
    "name": "CubeKit",
    "author": "TefMeister",
    "version": (0, 4, 1),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > CubeKit",
    "category": "Mesh",
    "description": "Pixel-style cube models: pick, add, remove and colour single cubes",
}

_HERE = os.path.dirname(os.path.abspath(__file__))
# bl.py, edit.py, atlas.py and cube_size.py are bundled in the zip; when the add-on runs straight
# from the repo they sit two folders up. Either way they are plain modules, found through sys.path.
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", ".."))):
    if _p not in sys.path:
        sys.path.insert(0, _p)


from . import navigate  # noqa: E402  W A S D movement, the hover circle, Ctrl + wheel


def _kit():
    import importlib
    import bl
    import edit
    import cube_size
    importlib.reload(bl)
    importlib.reload(edit)
    importlib.reload(cube_size)
    return bl, edit, cube_size.VOXEL_M


def _view3d_spaces(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for sp in area.spaces:
                if sp.type == 'VIEW_3D':
                    yield sp


def _edit_objects(context):
    return [o for o in context.objects_in_mode if o.type == 'MESH'] if context.mode == 'EDIT_MESH' else []


# ---------------------------------------------------------------- buttons

class CUBEKIT_OT_colours_on(bpy.types.Operator):
    """Flat, unlit view: what the game shows, nothing more"""
    bl_idname = "cubekit.colours_on"
    bl_label = "Colours on"

    def execute(self, context):
        _, edit, _ = _kit()
        painted = any(edit.has_colours(o) for o in bpy.data.objects if o.type == 'MESH')
        for sp in _view3d_spaces(context):
            sp.shading.type = 'SOLID'
            sp.shading.color_type = 'VERTEX' if painted else 'TEXTURE'
            sp.shading.light = 'FLAT'
        return {'FINISHED'}


class CUBEKIT_OT_pick_mode(bpy.types.Operator):
    """Cut every merged strip back into single cubes and give each object its full cube list, so
single cubes can be picked, added, removed and coloured. Works on the selected objects, or on
every mesh when nothing is selected"""
    bl_idname = "cubekit.pick_mode"
    bl_label = "Every cube on its own"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl, edit, V = _kit()
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        obs = [o for o in getattr(context, 'selected_objects', None) or [] if o.type == 'MESH']
        if not obs:
            obs = [o for o in bpy.data.objects if o.type == 'MESH']
        done = 0
        for ob in obs:
            if not ob.data.polygons or edit.has_colours(ob):
                continue
            if not bl.pick_mode_check(ob, V):
                bl.split_to_cubes(ob, V)
            edit.convert(ob, V)
            done += 1
        try:
            bpy.ops.cubekit.colours_on()
        except Exception:
            pass
        self.report({'INFO'}, "%d object(s) ready for cube editing" % done)
        return {'FINISHED'}


class CUBEKIT_OT_save_pick_copy(bpy.types.Operator):
    """Save this scene as <file>_pick.blend beside the open file. The original is what the game
export reads, so it stays merged and lean"""
    bl_idname = "cubekit.save_pick_copy"
    bl_label = "Save pick copy"

    def execute(self, context):
        src = bpy.data.filepath
        if not src:
            self.report({'ERROR'}, "save the file once first, so there is a name to add _pick to")
            return {'CANCELLED'}
        out = src if src.endswith("_pick.blend") else src[:-6] + "_pick.blend"
        bpy.ops.wm.save_as_mainfile(filepath=out)
        self.report({'INFO'}, "saved " + os.path.basename(out))
        return {'FINISHED'}


# ---------------------------------------------------------------- picking

class CUBEKIT_OT_pick_cube(bpy.types.Operator):
    """Pick exactly the cube under the mouse (from object mode: enters edit mode on that object)"""
    bl_idname = "cubekit.pick_cube"
    bl_label = "Pick the cube under the mouse"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        if context.mode == 'OBJECT':
            loc = (event.mouse_region_x, event.mouse_region_y)
            bpy.ops.view3d.select(location=loc, deselect_all=True)
            ob = context.object
            if not ob or ob.type != 'MESH' or not ob.select_get():
                self.report({'WARNING'}, "no cube under the mouse")
                return {'CANCELLED'}
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='FACE')
            bpy.ops.mesh.select_all(action='DESELECT')
        return bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT', deselect=False)


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
        bpy.ops.view3d.select_circle(x=self._mouse[0], y=self._mouse[1], radius=r,
                                     wait_for_input=False, mode=self.mode)
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
                    bpy.ops.view3d.select(location=self._mouse, extend=(self.mode == 'ADD'),
                                          deselect=(self.mode == 'SUB'))
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


class CUBEKIT_OT_tab(bpy.types.Operator):
    """Tab: into cube editing with nothing picked, faces mode, cubes visible; Tab again: out"""
    bl_idname = "cubekit.tab"
    bl_label = "Edit cubes"

    def execute(self, context):
        if context.mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}
        ob = context.active_object
        if not ob or ob.type != 'MESH':
            return bpy.ops.object.editmode_toggle()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_all(action='DESELECT')
        try:
            bpy.ops.cubekit.hover('INVOKE_DEFAULT')
        except Exception:
            pass
        return {'FINISHED'}


class CUBEKIT_OT_view_all(bpy.types.Operator):
    """R: the whole model in view"""
    bl_idname = "cubekit.view_all"
    bl_label = "Whole model in view"

    def execute(self, context):
        # frame the visible cube objects only (not cameras, lights or empties far away)
        obs = [o for o in context.visible_objects if o.type == 'MESH']
        if not obs:
            return bpy.ops.view3d.view_all(center=False)
        from mathutils import Vector
        pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
        lo = Vector([min(p[i] for p in pts) for i in range(3)])
        hi = Vector([max(p[i] for p in pts) for i in range(3)])
        rv = context.space_data.region_3d
        rv.view_location = (lo + hi) / 2
        rv.view_distance = max((hi - lo).length * 1.15, 0.05)
        return {'FINISHED'}


# ---------------------------------------------------------------- editing cubes

def _for_each_edited(context, fn):
    """Run fn(ob, V, keys) on every object in edit mode that has picked faces, in object mode, then
    go back to edit mode. Returns how many objects were touched."""
    _, edit, V = _kit()
    obs = _edit_objects(context)
    if not obs:
        return 0
    bpy.ops.object.mode_set(mode='OBJECT')
    touched = 0
    for ob in obs:
        if not edit.has_colours(ob):
            continue
        keys = edit.Solid(ob, V).selected_keys()
        if keys:
            fn(edit, ob, V, keys)
            touched += 1
    bpy.ops.object.mode_set(mode='EDIT')
    return touched


class CUBEKIT_OT_grow(bpy.types.Operator):
    """E: add a cube outside every picked side, in that side's colour. E E E builds a row"""
    bl_idname = "cubekit.grow"
    bl_label = "Add a cube"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.window_manager.cubekit_whole:
            self.report({'WARNING'}, "pick a SIDE first (F switches to sides), so I know which way")
            return {'CANCELLED'}
        n = _for_each_edited(context, lambda edit, ob, V, keys: edit.grow(ob, V, keys))
        if not n:
            self.report({'WARNING'}, "nothing picked, or not a cube-edit object (use Every cube on its own)")
            return {'CANCELLED'}
        return {'FINISHED'}


class CUBEKIT_OT_shrink(bpy.types.Operator):
    """Q: remove the cube behind every picked side (Q Q Q digs a row). With whole cubes picked,
removes those cubes"""
    bl_idname = "cubekit.shrink"
    bl_label = "Remove a cube"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        whole = context.window_manager.cubekit_whole
        n = _for_each_edited(context, lambda edit, ob, V, keys:
                             edit.remove_cubes(ob, V, keys) if whole else edit.shrink(ob, V, keys))
        if not n:
            self.report({'WARNING'}, "nothing picked, or not a cube-edit object (use Every cube on its own)")
            return {'CANCELLED'}
        return {'FINISHED'}


# ---------------------------------------------------------------- the palette

class CubeKitColour(bpy.types.PropertyGroup):
    color: bpy.props.FloatVectorProperty(name="colour", subtype='COLOR_GAMMA', size=3, min=0.0, max=1.0,
                                         default=(0.8, 0.8, 0.8))


class CUBEKIT_OT_apply_colour(bpy.types.Operator):
    """Paint the picked sides (or whole cubes) with this colour"""
    bl_idname = "cubekit.apply_colour"
    bl_label = "Paint"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        pal = context.scene.cubekit_palette
        if not (0 <= self.index < len(pal)):
            return {'CANCELLED'}
        rgb = tuple(pal[self.index].color)
        whole = context.window_manager.cubekit_whole
        n = _for_each_edited(context, lambda edit, ob, V, keys: edit.paint(ob, V, keys, rgb, whole))
        if not n:
            self.report({'WARNING'}, "nothing picked, or not a cube-edit object (use Every cube on its own)")
            return {'CANCELLED'}
        return {'FINISHED'}


class CUBEKIT_OT_palette_add(bpy.types.Operator):
    """Add a colour to the palette: the picked side's colour if something is picked, else grey"""
    bl_idname = "cubekit.palette_add"
    bl_label = "Add colour"

    def execute(self, context):
        rgb = None
        _, edit, V = _kit()
        if context.mode == 'EDIT_MESH':
            obs = _edit_objects(context)
            bpy.ops.object.mode_set(mode='OBJECT')
            for ob in obs:
                if edit.has_colours(ob):
                    s = edit.Solid(ob, V)
                    keys = s.selected_keys()
                    if keys:
                        rgb = s.colour_of(*keys[0])
                        break
            bpy.ops.object.mode_set(mode='EDIT')
        item = context.scene.cubekit_palette.add()
        if rgb:
            item.color = rgb
        return {'FINISHED'}


class CUBEKIT_OT_palette_remove(bpy.types.Operator):
    """Take this colour off the palette"""
    bl_idname = "cubekit.palette_remove"
    bl_label = "Remove colour"

    index: bpy.props.IntProperty()

    def execute(self, context):
        pal = context.scene.cubekit_palette
        if 0 <= self.index < len(pal):
            pal.remove(self.index)
        return {'FINISHED'}


DEFAULT_PALETTE = [(0.16, 0.16, 0.17), (0.45, 0.46, 0.48), (0.62, 0.41, 0.22), (0.35, 0.16, 0.14),
                   (0.75, 0.59, 0.27), (0.63, 0.14, 0.12), (0.92, 0.88, 0.80), (0.20, 0.35, 0.65)]


# ---------------------------------------------------------------- the panel

class CUBEKIT_PT_panel(bpy.types.Panel):
    bl_label = "CubeKit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CubeKit"

    def draw(self, context):
        wm = context.window_manager
        lay = self.layout
        col = lay.column(align=True)
        try:
            _, _, V = _kit()
            col.label(text="cube size: %.1f mm" % (V * 1000))
        except Exception:
            col.label(text="cube size: (kit not found)", icon='ERROR')
        col.operator("cubekit.colours_on", icon='SHADING_TEXTURE')
        col.operator("cubekit.pick_mode", icon='MESH_CUBE')
        col.operator("cubekit.save_pick_copy", icon='FILE_TICK')

        box = lay.box()
        box.label(text="picking", icon='RESTRICT_SELECT_OFF')
        row = box.row(align=True)
        row.prop(wm, "cubekit_whole", text="whole cubes (F)" if wm.cubekit_whole else "sides only (F)", toggle=True)
        box.prop(wm, "cubekit_brush", text="brush size (wheel)")

        box = lay.box()
        row = box.row(align=True)
        row.label(text="colours", icon='COLOR')
        row.operator("cubekit.palette_add", text="", icon='ADD')
        pal = context.scene.cubekit_palette
        box.label(text="pick cubes, then click a brush button")
        if not pal:
            box.label(text="press + to add one")
        for i, item in enumerate(pal):
            row = box.row(align=True)
            row.prop(item, "color", text="")
            row.operator("cubekit.apply_colour", text="", icon='BRUSH_DATA').index = i
            row.operator("cubekit.palette_remove", text="", icon='X').index = i

        col = lay.column(align=True)
        col.label(text="object mode: hover a cube, L = pick")
        col.label(text="edit mode: left = pick, right = un-pick")
        col.label(text="E add / Q remove / F sides / R view")
        col.label(text="Ctrl + wheel = brush size")
        col.label(text="WASD move, Z down, X up, middle mouse look")
        col.label(text="F5 / F6 = the old left / right mouse")


# ---------------------------------------------------------------- register

CLASSES = (CubeKitColour, CUBEKIT_OT_colours_on, CUBEKIT_OT_pick_mode, CUBEKIT_OT_save_pick_copy,
           CUBEKIT_OT_pick_cube, CUBEKIT_OT_brush, CUBEKIT_OT_toggle_whole, CUBEKIT_OT_tab, CUBEKIT_OT_view_all,
           CUBEKIT_OT_grow, CUBEKIT_OT_shrink, CUBEKIT_OT_apply_colour, CUBEKIT_OT_palette_add,
           CUBEKIT_OT_palette_remove, CUBEKIT_PT_panel)
_keys = []
_walk_moved = []          # (keymap item, old key) for the walk mode's Tab, put back on unregister
GRAVITY_KEY = 'F12'       # where walk mode's "falling" switch goes: a key nobody presses while walking


def _bind(kc, keymap, idname, key, shift=False, **props):
    km = kc.keymaps.new(name=keymap, space_type='EMPTY')
    kmi = km.keymap_items.new(idname, type=key, value='PRESS', shift=shift)
    for k, v in props.items():
        setattr(kmi.properties, k, v)
    _keys.append((km, kmi))


def _seed_palette(scene):
    if scene and not scene.cubekit_palette:
        for rgb in DEFAULT_PALETTE:
            scene.cubekit_palette.add().color = rgb


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.cubekit_whole = bpy.props.BoolProperty(
        name="whole cubes", default=True, description="A pick grabs whole cubes (on) or single sides (off). F toggles")
    bpy.types.WindowManager.cubekit_brush = bpy.props.IntProperty(
        name="brush size", default=18, min=2, max=300, description="Brush radius in pixels; the wheel changes it while picking")
    bpy.types.Scene.cubekit_palette = bpy.props.CollectionProperty(type=CubeKitColour)
    navigate.register()
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        navigate.bind(kc, _keys)
        _bind(kc, "Object Mode", "cubekit.pick_cube", 'L')
        _bind(kc, "Object Mode", "cubekit.tab", 'TAB')
        _bind(kc, "Mesh", "cubekit.tab", 'TAB')
        _bind(kc, "Mesh", "cubekit.brush", 'LEFTMOUSE', mode='ADD')
        _bind(kc, "Mesh", "cubekit.brush", 'RIGHTMOUSE', mode='SUB')
        _bind(kc, "Mesh", "cubekit.toggle_whole", 'F')
        _bind(kc, "Mesh", "cubekit.grow", 'E')
        _bind(kc, "Mesh", "cubekit.shrink", 'Q')
        _bind(kc, "Mesh", "cubekit.view_all", 'R')
        _bind(kc, "Mesh", "view3d.select", 'F5')                                   # the old left mouse
        _bind(kc, "Mesh", "wm.call_menu", 'F6', name="VIEW3D_MT_edit_mesh_context_menu")   # the old right mouse
    try:
        _seed_palette(bpy.context.scene)
    except Exception:
        pass
    # Walk mode (Blender's own, Shift+`): Tab switches falling on. An add-on cannot add to that
    # keymap, so the user's own Tab item is moved to GRAVITY_KEY, and falling starts off.
    try:
        bpy.context.preferences.inputs.walk_navigation.use_gravity = False
        wk = bpy.context.window_manager.keyconfigs.user.keymaps.get("View3D Walk Modal")
        for kmi in wk.keymap_items:
            if kmi.propvalue == 'GRAVITY_TOGGLE' and kmi.type == 'TAB':
                _walk_moved.append((kmi, kmi.type))
                kmi.type = GRAVITY_KEY
    except Exception as e:
        print("CubeKit: could not move walk mode's Tab:", e)


def unregister():
    for km, kmi in _keys:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _keys.clear()
    for kmi, old in _walk_moved:
        try:
            kmi.type = old
        except Exception:
            pass
    _walk_moved.clear()
    navigate.unregister()
    del bpy.types.WindowManager.cubekit_whole
    del bpy.types.WindowManager.cubekit_brush
    del bpy.types.Scene.cubekit_palette
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
