# CubeKit - the Blender side of blender-cubekit (github.com/TefMeister/blender-cubekit).
# Buttons and keys for pixel-style cube models. Everything here is also a script in the repo;
# the add-on only puts a button on it.
#
# What it gives you (3D view, sidebar tab "CubeKit"):
#   Colours on             the flat, unlit, textured view - exactly what the game shows
#   Every cube on its own  cuts merged strips back into single cubes so one cube can be picked
#   Save pick copy         saves <file>_pick.blend beside the open file (the original stays lean)
# Key:
#   L  (object mode, mouse over a cube)  picks exactly that one cube and drops you into edit mode.
#      In edit mode L already does this in Blender, so the rule is: hover a cube, press L.
#   Tab                                  back out of edit mode.
import os
import sys

import bpy

bl_info = {   # read by Blender versions before 4.2; the manifest file is what 4.2+ reads
    "name": "CubeKit",
    "author": "TefMeister",
    "version": (0, 1, 0),
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
        col.label(text="hover a cube, press L = pick it")
        col.label(text="Tab = back out")


CLASSES = (CUBEKIT_OT_colours_on, CUBEKIT_OT_pick_mode, CUBEKIT_OT_save_pick_copy,
           CUBEKIT_OT_pick_cube, CUBEKIT_PT_panel)
_keys = []


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Object Mode", space_type='EMPTY')
        kmi = km.keymap_items.new("cubekit.pick_cube", type='L', value='PRESS')
        _keys.append((km, kmi))


def unregister():
    for km, kmi in _keys:
        km.keymap_items.remove(kmi)
    _keys.clear()
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
