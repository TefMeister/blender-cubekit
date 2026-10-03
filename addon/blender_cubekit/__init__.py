# CubeKit - the Blender side of blender-cubekit (github.com/TefMeister/blender-cubekit).
# Buttons and keys for pixel-style cube models. Everything here is also a script in the repo;
# the add-on only puts a button on it.
#
# What it gives you (3D view, sidebar tab "CubeKit"):
#   Colours on             the flat, unlit, textured view - exactly what the game shows
#   Every cube on its own  cuts merged strips back into single cubes so one cube can be picked
#   Save pick copy         saves <file>_pick.blend beside the open file (the original stays lean)
# Keys, object mode:
#   L  (mouse over a cube)   picks exactly that one cube and drops you into edit mode.
# Keys, edit mode (after Tab), asked for 2026-10-03:
#   left mouse               picks the cube under the mouse (one click = that cube only;
#                            Shift adds). In paint-select, hold it and sweep over cubes to add them.
#   right mouse              paint-select on / off
#   Space                    walk around: W A S D move, mouse looks, Q down, E up, Shift fast.
#                            Space again (or Esc) stops.
#   F5                       what the left mouse did before (Blender's plain click-select)
#   F6                       what the right mouse did before (the edit-mesh menu)
#   Tab                      back out of edit mode.
import os
import sys

import bpy

bl_info = {   # read by Blender versions before 4.2; the manifest file is what 4.2+ reads
    "name": "CubeKit",
    "author": "TefMeister",
    "version": (0, 2, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > CubeKit",
    "category": "Mesh",
    "description": "Pixel-style cube models: pick any cube, colours on, pick-mode copies",
}

_HERE = os.path.dirname(os.path.abspath(__file__))
# bl.py and atlas.py are bundled in the zip; when the add-on runs straight from the repo they sit
# two folders up. Either way they are plain modules, found through sys.path.
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", ".."))):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _kit():
    import importlib
    import bl
    import cube_size
    importlib.reload(bl)
    importlib.reload(cube_size)
    return bl, cube_size.VOXEL_M


def _view3d_spaces(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for sp in area.spaces:
                if sp.type == 'VIEW_3D':
                    yield sp


class CUBEKIT_OT_colours_on(bpy.types.Operator):
    """Flat, unlit, textured view: what the game shows, nothing more"""
    bl_idname = "cubekit.colours_on"
    bl_label = "Colours on"

    def execute(self, context):
        for sp in _view3d_spaces(context):
            sp.shading.type = 'SOLID'
            sp.shading.color_type = 'TEXTURE'
            sp.shading.light = 'FLAT'
        return {'FINISHED'}


class CUBEKIT_OT_pick_mode(bpy.types.Operator):
    """Cut every merged strip back into single cubes, so one cube can be picked on its own.
Works on the selected objects, or on every mesh when nothing is selected"""
    bl_idname = "cubekit.pick_mode"
    bl_label = "Every cube on its own"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl, voxel_m = _kit()
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        obs = [o for o in context.selected_objects if o.type == 'MESH']
        if not obs:
            obs = [o for o in bpy.data.objects if o.type == 'MESH']
        done, already = 0, 0
        for ob in obs:
            if not ob.data.polygons:
                continue
            if bl.pick_mode_check(ob, voxel_m):
                already += 1
            else:
                bl.split_to_cubes(ob, voxel_m)
                done += 1
        self.report({'INFO'}, "%d object(s) cut into single cubes, %d already were" % (done, already))
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


class CUBEKIT_OT_paint_pick(bpy.types.Operator):
    """Left mouse in edit mode: pick the cube under the mouse. One click = that cube only (Shift
adds). With paint-select on, hold the button and sweep over cubes to add them"""
    bl_idname = "cubekit.paint_pick"
    bl_label = "Pick cubes with the mouse"
    bl_options = {'REGISTER', 'UNDO'}

    def _pick(self):
        try:
            bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT', deselect=False)
        except RuntimeError:
            pass

    def invoke(self, context, event):
        if context.mode != 'EDIT_MESH':
            return {'PASS_THROUGH'}
        paint = context.window_manager.cubekit_paint
        if not paint and not event.shift:
            bpy.ops.mesh.select_all(action='DESELECT')
        self._pick()
        if not paint:
            return {'FINISHED'}
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self._pick()
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            return {'FINISHED'}
        elif event.type == 'ESC':
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


class CUBEKIT_OT_toggle_paint(bpy.types.Operator):
    """Right mouse in edit mode: paint-select on / off"""
    bl_idname = "cubekit.toggle_paint"
    bl_label = "Paint-select on / off"

    def execute(self, context):
        wm = context.window_manager
        wm.cubekit_paint = not wm.cubekit_paint
        self.report({'INFO'}, "paint-select " + ("ON: hold the left mouse and sweep" if wm.cubekit_paint
                                                 else "OFF: one click = one cube"))
        return {'FINISHED'}


WALK_SPEED = 0.35        # metres per second: a hand-held model is under a metre long


class CUBEKIT_OT_walk(bpy.types.Operator):
    """Space in edit mode: walk around the model. W A S D move, the mouse looks, Q down, E up,
Shift fast. Space again (or Esc) stops"""
    bl_idname = "cubekit.walk"
    bl_label = "Walk around"

    def invoke(self, context, event):
        walk = context.preferences.inputs.walk_navigation
        walk.use_gravity = False
        walk.walk_speed = WALK_SPEED
        return bpy.ops.view3d.walk('INVOKE_DEFAULT')


class CUBEKIT_PT_panel(bpy.types.Panel):
    bl_label = "CubeKit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CubeKit"

    def draw(self, context):
        col = self.layout.column(align=True)
        try:
            _, voxel_m = _kit()
            col.label(text="cube size: %.1f mm" % (voxel_m * 1000))
        except Exception:
            col.label(text="cube size: (kit not found)", icon='ERROR')
        col.operator("cubekit.colours_on", icon='SHADING_TEXTURE')
        col.operator("cubekit.pick_mode", icon='MESH_CUBE')
        col.operator("cubekit.save_pick_copy", icon='FILE_TICK')
        col.separator()
        wm = context.window_manager
        col.prop(wm, "cubekit_paint", text="paint-select (right mouse)", toggle=True,
                 icon='BRUSH_DATA' if wm.cubekit_paint else 'RESTRICT_SELECT_OFF')
        col.separator()
        col.label(text="object mode: hover a cube, L = pick it")
        col.label(text="edit mode: left mouse = pick, Tab = out")
        col.label(text="Space = walk (WASD, mouse, Q/E)")
        col.label(text="F5 / F6 = the old left / right mouse")


CLASSES = (CUBEKIT_OT_colours_on, CUBEKIT_OT_pick_mode, CUBEKIT_OT_save_pick_copy,
           CUBEKIT_OT_pick_cube, CUBEKIT_OT_paint_pick, CUBEKIT_OT_toggle_paint, CUBEKIT_OT_walk,
           CUBEKIT_PT_panel)
_keys = []
_walk_space = []


def _bind(kc, keymap, idname, key, shift=False, **props):
    km = kc.keymaps.new(name=keymap, space_type='EMPTY')
    kmi = km.keymap_items.new(idname, type=key, value='PRESS', shift=shift)
    for k, v in props.items():
        setattr(kmi.properties, k, v)
    _keys.append((km, kmi))


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.cubekit_paint = bpy.props.BoolProperty(
        name="paint-select", default=False,
        description="Hold the left mouse and sweep over cubes to add them (right mouse toggles)")
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        _bind(kc, "Object Mode", "cubekit.pick_cube", 'L')
        _bind(kc, "Mesh", "cubekit.paint_pick", 'LEFTMOUSE')
        _bind(kc, "Mesh", "cubekit.paint_pick", 'LEFTMOUSE', shift=True)   # Shift adds a cube
        _bind(kc, "Mesh", "cubekit.toggle_paint", 'RIGHTMOUSE')
        _bind(kc, "Mesh", "cubekit.walk", 'SPACE')
        _bind(kc, "Mesh", "view3d.select", 'F5')                            # the old left mouse
        _bind(kc, "Mesh", "wm.call_menu", 'F6', name="VIEW3D_MT_edit_mesh_context_menu")   # the old right mouse
    # Inside the walk, Space ends it (Blender's own keys for that are Esc and Enter). An add-on cannot
    # add to a modal keymap, so this changes the one Space item in the user's walk keymap (teleport by
    # default, which nobody needs on a model) and puts it back when the add-on is disabled.
    try:
        wk = bpy.context.window_manager.keyconfigs.user.keymaps.get("View3D Walk Modal")
        for kmi in wk.keymap_items:
            if kmi.type == 'SPACE' and kmi.propvalue != 'CONFIRM':
                _walk_space.append((kmi, kmi.propvalue))
                kmi.propvalue = 'CONFIRM'
    except Exception as e:
        print("CubeKit: could not make Space end the walk:", e)


def unregister():
    for km, kmi in _keys:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _keys.clear()
    for kmi, old in _walk_space:
        try:
            kmi.propvalue = old
        except Exception:
            pass
    _walk_space.clear()
    del bpy.types.WindowManager.cubekit_paint
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
