# Moving cubes, and moving parts (asked for by Tefa, 2026-10-03, for posing fingers):
#
#   Move picked cubes   Alt + arrow keys / Alt + Page Up, Page Down in edit mode (or the arrows in the
#                       CubeKit Build tab): the picked cubes move one whole cube, with their colours,
#                       in the direction that is left / right / away / towards / up / down on screen.
#   Make a moving part  the picked cubes are lifted out of their object into a part of their own,
#                       which turns at the point where it touched the rest (a finger at its knuckle)
#                       and follows the object it came from. Pose it frame by frame like the shell:
#                       Tab out, click it, R to turn it, I to keep the pose for that frame. A part can
#                       be split again (the fingertip out of the finger) for more joints.
import bpy
from mathutils import Matrix, Vector

# screen directions -> a direction in the view (x right, y up, -z away)
SCREEN = {
    'LEFT': Vector((-1, 0, 0)), 'RIGHT': Vector((1, 0, 0)),
    'AWAY': Vector((0, 0, -1)), 'TOWARDS': Vector((0, 0, 1)),
}
KEYS = [('LEFT_ARROW', 'LEFT'), ('RIGHT_ARROW', 'RIGHT'), ('UP_ARROW', 'AWAY'), ('DOWN_ARROW', 'TOWARDS'),
        ('PAGE_UP', 'UP'), ('PAGE_DOWN', 'DOWN')]


def _grid_step(context, ob, which):
    """The whole-cube step in the object's own grid that is closest to the screen direction."""
    if which in ('UP', 'DOWN'):
        world = Vector((0, 0, 1 if which == 'UP' else -1))
    else:
        rv = context.space_data.region_3d if context.space_data and context.space_data.type == 'VIEW_3D' else None
        if rv is None:
            for a in context.screen.areas:
                if a.type == 'VIEW_3D':
                    rv = a.spaces.active.region_3d
        world = rv.view_rotation @ SCREEN[which]
        if which in ('AWAY', 'TOWARDS'):
            world.z = 0                      # away / towards stay level, like walking
            if world.length < 1e-6:
                world = rv.view_rotation @ Vector((0, 1 if which == 'AWAY' else -1, 0))
                world.z = 0
    local = ob.matrix_world.to_3x3().inverted() @ world
    ax = max(range(3), key=lambda i: abs(local[i]))
    step = [0, 0, 0]
    step[ax] = 1 if local[ax] > 0 else -1
    return tuple(step)


class CUBEKIT_OT_nudge(bpy.types.Operator):
    """Move the picked cubes one whole cube, with their colours (Alt + arrows, Alt + Page Up / Down)"""
    bl_idname = "cubekit.nudge"
    bl_label = "Move picked cubes"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(items=[(k, k.title(), "") for k in
                                             ('LEFT', 'RIGHT', 'AWAY', 'TOWARDS', 'UP', 'DOWN')])

    def execute(self, context):
        from . import _for_each_edited
        if context.mode != 'EDIT_MESH':
            self.report({'WARNING'}, "press Tab and pick cubes first")
            return {'CANCELLED'}
        steps = {ob.name: _grid_step(context, ob, self.direction) for ob in context.objects_in_mode}
        n = _for_each_edited(context, lambda edit, ob, V, keys: edit.move_cubes(ob, V, keys, steps[ob.name]))
        if not n:
            self.report({'WARNING'}, "nothing picked, or not a cube-edit object")
            return {'CANCELLED'}
        return {'FINISHED'}


class CUBEKIT_OT_make_part(bpy.types.Operator):
    """Lift the picked cubes out into a moving part of their own, turning where they touched the
    rest (a finger at its knuckle). Then pose it per frame: Tab out, click it, R, I"""
    bl_idname = "cubekit.make_part"
    bl_label = "Make a moving part"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from . import _kit, _edit_objects
        if context.mode != 'EDIT_MESH':
            self.report({'WARNING'}, "press Tab and pick the cubes for the part first")
            return {'CANCELLED'}
        _, edit, V = _kit()
        obs = _edit_objects(context)
        bpy.ops.object.mode_set(mode='OBJECT')
        made = []
        for ob in obs:
            if not edit.has_colours(ob):
                continue
            keys = edit.Solid(ob, V).selected_keys()
            if not keys:
                continue
            picked, rest, joint, off, v = edit.split_part_plan(ob, V, keys)
            if not picked or not rest:
                self.report({'WARNING'}, "%s: pick some of its cubes, not all of them" % ob.name)
                continue
            name = context.scene.cubekit_part_name.strip() or (ob.name + "_part")
            part = ob.copy()
            part.data = ob.data.copy()
            part.name = name
            part.data.name = name
            part.animation_data_clear()
            for coll in ob.users_collection:
                coll.objects.link(part)
            edit.keep_only(part, V, picked, joint)
            edit.drop(ob, V, picked)
            part.parent = ob
            part.matrix_parent_inverse = Matrix.Identity(4)
            part.location = Vector([joint[i] * v for i in range(3)])
            part.rotation_mode = 'XYZ'
            part.rotation_euler = (0, 0, 0)
            part.scale = (1, 1, 1)
            made.append(part)
        if not made:
            bpy.ops.object.mode_set(mode='EDIT')
            self.report({'WARNING'}, "nothing picked")
            return {'CANCELLED'}
        for o in context.view_layer.objects:
            o.select_set(False)
        for p in made:
            p.select_set(True)
        context.view_layer.objects.active = made[-1]
        context.scene.cubekit_part_name = ""
        self.report({'INFO'}, "made %s: click it, R to turn it, I to keep the pose" % ", ".join(p.name for p in made))
        return {'FINISHED'}


def draw(layout, context):
    """The Build tab's 'move and parts' section."""
    box = layout.box()
    box.label(text="move picked cubes (Alt + arrows)", icon='EMPTY_ARROWS')
    grid = box.grid_flow(columns=3, align=True)
    for label, d in (("", None), ("away", 'AWAY'), ("up", 'UP'),
                     ("left", 'LEFT'), ("", None), ("right", 'RIGHT'),
                     ("", None), ("towards", 'TOWARDS'), ("down", 'DOWN')):
        if d:
            grid.operator("cubekit.nudge", text=label).direction = d
        else:
            grid.label(text="")
    box = layout.box()
    box.label(text="moving parts (fingers)", icon='BONE_DATA')
    box.prop(context.scene, "cubekit_part_name", text="name")
    box.operator("cubekit.make_part", icon='MOD_EXPLODE')
    box.label(text="then: Tab out, click it, R turn, I keep")


CLASSES = (CUBEKIT_OT_nudge, CUBEKIT_OT_make_part)


def bind(kc, keys):
    km = kc.keymaps.new(name="Mesh", space_type='EMPTY')
    for key, d in KEYS:
        kmi = km.keymap_items.new("cubekit.nudge", type=key, value='PRESS', alt=True)
        kmi.properties.direction = d
        keys.append((km, kmi))


def register():
    bpy.types.Scene.cubekit_part_name = bpy.props.StringProperty(
        name="part name", default="", description="What to call the new part (e.g. index_finger). Empty: the object's name + _part")
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.cubekit_part_name
