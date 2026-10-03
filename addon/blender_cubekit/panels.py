# The key help in the CubeKit tab, one folding section per job, and the CubeKit Build tab where a
# number of cubes to add or remove is typed in (asked for by Tefa, 2026-10-03).
import bpy

# (section title, icon, [(key, what it does)]) - the help the CubeKit tab shows. Keep in step with
# the key bindings in __init__.py, navigate.py and palette.py, and with docs/HOTKEYS.md.
HELP = [
    ("Moving around (always on)", 'VIEW_PAN', [
        ("W A S D", "move"),
        ("Z / X", "down / up"),
        ("Shift", "faster, while held"),
        ("Middle mouse", "hold to look around"),
        ("Wheel", "zoom"),
        ("R", "whole model in view (edit mode)"),
        ("CubeKit Move tab", "change the speeds"),
    ]),
    ("Picking (edit mode)", 'RESTRICT_SELECT_OFF', [
        ("Tab", "in / out of editing, nothing picked"),
        ("Left mouse", "pick; hold and sweep for more"),
        ("Right mouse", "hold to un-pick"),
        ("Ctrl + wheel", "brush bigger / smaller"),
        ("Alt + A", "un-pick everything"),
        ("F", "whole cubes / sides only"),
    ]),
    ("Building", 'MESH_CUBE', [
        ("E", "add a cube on each picked side"),
        ("Q", "remove the cube behind each picked side"),
        ("C", "split a side: 4, then 16, then 4 ..."),
        ("Shift + C", "join a split side back into one"),
        ("CubeKit Build tab", "add or remove a typed number"),
    ]),
    ("Painting", 'BRUSH_DATA', [
        ("Click a colour", "paint what is picked"),
        ("1 to 0 over a cube", "paint it that key's colour"),
        ("Click colour, then 1-0", "give the colour that key"),
        ("Ctrl + click colour", "remove that colour"),
    ]),
    ("Blender's own keys, moved", 'KEYINGSET', [
        ("F5", "plain click-select (was left mouse)"),
        ("F6", "edit-mesh menu (was right mouse)"),
        ("F7", "pick all / none (was A)"),
        ("F8", "scale (was S)"),
        ("F9", "shading wheel (was Z)"),
        ("F10", "spin-the-model view (was middle mouse)"),
        ("Delete", "delete (was X)"),
        ("Ctrl + Z", "undo"),
    ]),
]


def _help_panel(index, title, icon, rows):
    def draw_header(self, context):
        self.layout.label(text="", icon=icon)

    def draw(self, context):
        col = self.layout.column(align=True)
        for key, what in rows:
            row = col.row(align=True)
            split = row.split(factor=0.42, align=True)
            split.label(text=key)
            split.label(text=what)

    return type("CUBEKIT_PT_help_%d" % index, (bpy.types.Panel,), {
        "bl_label": title,
        "bl_space_type": 'VIEW_3D',
        "bl_region_type": 'UI',
        "bl_category": "CubeKit",
        "bl_parent_id": "CUBEKIT_PT_panel",
        "bl_options": {'DEFAULT_CLOSED'},
        "bl_order": 10 + index,
        "draw_header": draw_header,
        "draw": draw,
    })


HELP_PANELS = [_help_panel(i, t, ic, r) for i, (t, ic, r) in enumerate(HELP)]


# ---- the CubeKit Build tab ----

class CUBEKIT_OT_build(bpy.types.Operator):
    """Add (or remove) the typed number of cubes on every picked side"""
    bl_idname = "cubekit.build"
    bl_label = "Build"
    bl_options = {'REGISTER', 'UNDO'}

    remove: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        from . import _for_each_edited
        scene = context.scene
        wm = context.window_manager
        n = scene.cubekit_count
        if context.mode != 'EDIT_MESH':
            self.report({'WARNING'}, "press Tab and pick a side first")
            return {'CANCELLED'}
        if self.remove:
            if wm.cubekit_whole:
                fn = lambda edit, ob, V, keys: edit.remove_cubes(ob, V, keys)
            else:
                fn = lambda edit, ob, V, keys: edit.shrink(ob, V, keys, n)
        else:
            if wm.cubekit_whole:
                self.report({'WARNING'}, "pick a SIDE (F switches to sides), so I know which way to build")
                return {'CANCELLED'}
            rgb = None if scene.cubekit_build_colour == 'SIDE' else tuple(scene.cubekit_add_rgb)
            fn = lambda edit, ob, V, keys: edit.grow(ob, V, keys, n, rgb)
        done = _for_each_edited(context, fn)
        if not done:
            self.report({'WARNING'}, "nothing picked, or not a cube-edit object (use Every cube on its own)")
            return {'CANCELLED'}
        self.report({'INFO'}, "%s %d cube(s) on each picked side" % ("removed" if self.remove else "added", n))
        return {'FINISHED'}


class CUBEKIT_OT_build_colour_from_palette(bpy.types.Operator):
    """Use the palette's colour in hand (the big square in the CubeKit tab) for new cubes"""
    bl_idname = "cubekit.build_colour_from_palette"
    bl_label = "Take the palette's colour"

    def execute(self, context):
        scene = context.scene
        scene.cubekit_add_rgb = scene.cubekit_mix
        scene.cubekit_build_colour = 'CHOSEN'
        return {'FINISHED'}


class CUBEKIT_PT_build(bpy.types.Panel):
    bl_label = "Build by number"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CubeKit Build"

    def draw(self, context):
        scene = context.scene
        lay = self.layout
        lay.label(text="1. Tab, pick a side (F on sides)")
        lay.label(text="2. type how many, choose a colour")
        lay.label(text="3. press Add or Remove")
        box = lay.box()
        box.prop(scene, "cubekit_count", text="how many cubes")
        row = box.row(align=True)
        row.scale_y = 1.5
        row.operator("cubekit.build", text="Add on top", icon='ADD').remove = False
        row.operator("cubekit.build", text="Remove inwards", icon='REMOVE').remove = True
        box = lay.box()
        box.label(text="colour of added cubes", icon='COLOR')
        box.prop(scene, "cubekit_build_colour", expand=True)
        if scene.cubekit_build_colour == 'CHOSEN':
            row = box.row(align=True)
            row.scale_y = 1.5
            row.prop(scene, "cubekit_add_rgb", text="")
            box.operator("cubekit.build_colour_from_palette", icon='EYEDROPPER')


CLASSES = tuple(HELP_PANELS) + (CUBEKIT_OT_build, CUBEKIT_OT_build_colour_from_palette, CUBEKIT_PT_build)
COUNT_MAX = 200


def register():
    bpy.types.Scene.cubekit_count = bpy.props.IntProperty(
        name="how many cubes", default=1, min=1, max=COUNT_MAX,
        description="How many cubes Add on top or Remove inwards builds on each picked side")
    bpy.types.Scene.cubekit_build_colour = bpy.props.EnumProperty(
        name="colour of added cubes",
        items=[('SIDE', "Same as the side", "New cubes take the picked side's colour"),
               ('CHOSEN', "Chosen colour", "New cubes take the colour chosen below")],
        default='SIDE')
    bpy.types.Scene.cubekit_add_rgb = bpy.props.FloatVectorProperty(
        name="colour of added cubes", subtype='COLOR_GAMMA', size=3, min=0.0, max=1.0, default=(0.5, 0.5, 0.5))
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
    for name in ("cubekit_count", "cubekit_build_colour", "cubekit_add_rgb"):
        delattr(bpy.types.Scene, name)
