# Game-style movement in the 3D view, always on (asked for by Tefa, 2026-10-03):
#   W A S D        move forward, left, back, right, the way the view is facing
#   Z / X          lower / raise
#   Shift          faster while held
#   middle mouse   held: turn your head (look around from where you stand) instead of Blender's
#                  spin-the-model orbit
#   wheel          Blender's own zoom, unchanged
# Plus the brush circle that follows the mouse in edit mode, and Ctrl + wheel to size it.
#
# No mode to switch on: pressing a movement key starts a short-lived mover that runs while any of
# them is held and stops when the last one is let go. Every other key and click passes straight
# through, so picking with the mouse works while moving.
import math

import bpy
from mathutils import Quaternion, Vector

MOVE_SPEED = 0.30          # metres per second; a hand-held model is under a metre long. Approved by Tefa 2026-10-03
LIFT_SPEED = 0.30          # Z / X, metres per second. Both are only the starting values: the CubeKit
                           # Move tab changes them, kept in Blender's preferences (Tefa, 2026-10-03)
FAST = 3.0                 # Shift multiplies the speed by this
TICK = 1 / 60              # how often the view is moved, seconds
LOOK_DEG_PER_PX = 0.25     # middle-mouse look: degrees turned per pixel of mouse movement
BRUSH_STEP_SMALL = 3       # Ctrl + wheel: pixels per notch below BRUSH_STEP_SWITCH
BRUSH_STEP_BIG = 8
BRUSH_STEP_SWITCH = 40
BRUSH_MIN, BRUSH_MAX = 2, 300

MOVE_KEYS = {           # key -> direction in view space (x right, y up, -z forward)
    'W': Vector((0, 0, -1)), 'S': Vector((0, 0, 1)),
    'A': Vector((-1, 0, 0)), 'D': Vector((1, 0, 0)),
}
LIFT_KEYS = {'X': 1.0, 'Z': -1.0}   # world up / down


def _rv(context):
    sd = context.space_data
    return sd.region_3d if sd and sd.type == 'VIEW_3D' else None


def _eye(rv):
    return rv.view_location + rv.view_rotation @ Vector((0, 0, rv.view_distance))


class CUBEKIT_OT_move(bpy.types.Operator):
    """W A S D move, Z down, X up, Shift faster - while held"""
    bl_idname = "cubekit.move"
    bl_label = "Move the view"

    def invoke(self, context, event):
        rv = _rv(context)
        if rv is None:
            return {'PASS_THROUGH'}
        if rv.view_perspective == 'CAMERA':
            rv.view_perspective = 'PERSP'
        if rv.view_perspective == 'ORTHO':
            rv.view_perspective = 'PERSP'
        self.held = {event.type}
        self.fast = event.shift
        self.timer = context.window_manager.event_timer_add(TICK, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _step(self, context):
        rv = _rv(context)
        if rv is None:
            return
        d = Vector((0, 0, 0))
        for k in self.held:
            if k in MOVE_KEYS:
                d += rv.view_rotation @ MOVE_KEYS[k]
        lift = sum(LIFT_KEYS.get(k, 0.0) for k in self.held)
        p = prefs()
        fast = p.fast if self.fast else 1.0
        if d.length:
            rv.view_location += d.normalized() * p.move_speed * fast * TICK
        if lift:
            rv.view_location.z += (1 if lift > 0 else -1) * p.lift_speed * fast * TICK

    def modal(self, context, event):
        if event.type == 'TIMER':
            self._step(context)
            context.area.tag_redraw() if context.area else None
            return {'RUNNING_MODAL'}
        if event.type in ('LEFT_SHIFT', 'RIGHT_SHIFT'):
            self.fast = event.value == 'PRESS'
            return {'RUNNING_MODAL'}
        if event.type in MOVE_KEYS or event.type in LIFT_KEYS:
            if event.value == 'PRESS':
                self.held.add(event.type)
            elif event.value == 'RELEASE':
                self.held.discard(event.type)
                if not self.held:
                    context.window_manager.event_timer_remove(self.timer)
                    return {'FINISHED'}
            return {'RUNNING_MODAL'}
        if event.type == 'WINDOW_DEACTIVATE':
            context.window_manager.event_timer_remove(self.timer)
            return {'FINISHED'}
        return {'PASS_THROUGH'}


class CUBEKIT_OT_look(bpy.types.Operator):
    """Middle mouse held: turn your head - look around from where you stand"""
    bl_idname = "cubekit.look"
    bl_label = "Look around"

    def invoke(self, context, event):
        rv = _rv(context)
        if rv is None:
            return {'PASS_THROUGH'}
        if rv.view_perspective != 'PERSP':
            rv.view_perspective = 'PERSP'
        self.last = (event.mouse_x, event.mouse_y)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            rv = _rv(context)
            dx, dy = event.mouse_x - self.last[0], event.mouse_y - self.last[1]
            self.last = (event.mouse_x, event.mouse_y)
            eye = _eye(rv)
            look = prefs().look
            yaw = Quaternion((0, 0, 1), -math.radians(dx * look))
            right = rv.view_rotation @ Vector((1, 0, 0))
            pitch = Quaternion(right, math.radians(dy * look))
            new = yaw @ pitch @ rv.view_rotation
            # do not tip over the top: keep the view's up pointing upwards
            if (new @ Vector((0, 1, 0))).z > 0.02:
                rv.view_rotation = new
            else:
                rv.view_rotation = yaw @ rv.view_rotation
            rv.view_location = eye - rv.view_rotation @ Vector((0, 0, rv.view_distance))
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE':
            return {'FINISHED'}
        if event.type in MOVE_KEYS or event.type in LIFT_KEYS:
            return {'PASS_THROUGH'}
        if event.type == 'ESC':
            return {'FINISHED'}
        return {'RUNNING_MODAL'}


# ---- the brush circle that follows the mouse in edit mode ----

_hover = {"pos": None, "region": None, "handle": None}


def _draw_hover():
    ctx = bpy.context
    if ctx.mode != 'EDIT_MESH' or _hover["pos"] is None or ctx.region != _hover["region"]:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    x, y = _hover["pos"]
    r = ctx.window_manager.cubekit_brush
    pts = [(x + r * math.cos(a), y + r * math.sin(a)) for a in [i * 2 * math.pi / 48 for i in range(49)]]
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pts})
    shader.bind()
    shader.uniform_float("color", (1.0, 0.6, 0.1, 0.55))
    gpu.state.blend_set('ALPHA')
    batch.draw(shader)
    gpu.state.blend_set('NONE')


class CUBEKIT_OT_hover(bpy.types.Operator):
    """Keeps the brush circle under the mouse while in cube editing. Lets every event through"""
    bl_idname = "cubekit.hover"
    bl_label = "Brush circle follows the mouse"

    _running = False

    def invoke(self, context, event):
        if CUBEKIT_OT_hover._running:
            return {'CANCELLED'}
        CUBEKIT_OT_hover._running = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if context.mode != 'EDIT_MESH':
            CUBEKIT_OT_hover._running = False
            _hover["pos"] = None
            for area in context.screen.areas if context.screen else ():
                area.tag_redraw()
            return {'FINISHED'}
        if event.type == 'MOUSEMOVE':
            area = None
            for a in context.screen.areas:
                if a.type == 'VIEW_3D' and a.x <= event.mouse_x < a.x + a.width and a.y <= event.mouse_y < a.y + a.height:
                    area = a
            if area:
                region = next(r for r in area.regions if r.type == 'WINDOW')
                _hover["pos"] = (event.mouse_x - region.x, event.mouse_y - region.y)
                _hover["region"] = region
                area.tag_redraw()
        return {'PASS_THROUGH'}


class CUBEKIT_OT_brush_size(bpy.types.Operator):
    """Ctrl + wheel: brush circle bigger or smaller"""
    bl_idname = "cubekit.brush_size"
    bl_label = "Brush size"

    bigger: bpy.props.BoolProperty(default=True)

    def invoke(self, context, event):
        wm = context.window_manager
        step = BRUSH_STEP_SMALL if wm.cubekit_brush < BRUSH_STEP_SWITCH else BRUSH_STEP_BIG
        wm.cubekit_brush = max(BRUSH_MIN, min(BRUSH_MAX, wm.cubekit_brush + (step if self.bigger else -step)))
        _hover["pos"] = (event.mouse_region_x, event.mouse_region_y)
        _hover["region"] = context.region
        if context.area:
            context.area.tag_redraw()
        return {'FINISHED'}


# ---- the speeds, in Blender's preferences so they are the same in every file ----

_pkg = {"name": __package__}


class _Defaults:
    move_speed, lift_speed, fast, look = MOVE_SPEED, LIFT_SPEED, FAST, LOOK_DEG_PER_PX


def prefs():
    try:
        return bpy.context.preferences.addons[_pkg["name"]].preferences
    except (KeyError, AttributeError):
        return _Defaults


class CubeKitPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__

    move_speed: bpy.props.FloatProperty(name="moving speed (W A S D)", default=MOVE_SPEED, min=0.01, max=10.0,
                                        soft_max=3.0, unit='VELOCITY', description="How fast W A S D move you")
    lift_speed: bpy.props.FloatProperty(name="up / down speed (X / Z)", default=LIFT_SPEED, min=0.01, max=10.0,
                                        soft_max=3.0, unit='VELOCITY', description="How fast X raises and Z lowers you")
    fast: bpy.props.FloatProperty(name="Shift makes it", default=FAST, min=1.0, max=20.0,
                                  description="Holding Shift multiplies both speeds by this")
    look: bpy.props.FloatProperty(name="look speed (middle mouse)", default=LOOK_DEG_PER_PX, min=0.02, max=2.0,
                                  description="Degrees the view turns per pixel of mouse movement")

    def draw(self, context):
        _draw_speeds(self.layout, self)


def _draw_speeds(lay, p):
    col = lay.column(align=True)
    col.prop(p, "move_speed")
    col.prop(p, "lift_speed")
    lay.prop(p, "fast", text="Shift makes it  x")
    lay.prop(p, "look")
    lay.operator("cubekit.speed_reset", icon='LOOP_BACK')


class CUBEKIT_OT_speed_reset(bpy.types.Operator):
    """Put every speed back to how it started"""
    bl_idname = "cubekit.speed_reset"
    bl_label = "Back to the starting speeds"

    def execute(self, context):
        p = prefs()
        if p is _Defaults:
            return {'CANCELLED'}
        p.move_speed, p.lift_speed, p.fast, p.look = MOVE_SPEED, LIFT_SPEED, FAST, LOOK_DEG_PER_PX
        return {'FINISHED'}


class CUBEKIT_PT_move(bpy.types.Panel):
    bl_label = "Moving speed"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CubeKit Move"

    def draw(self, context):
        p = prefs()
        if p is _Defaults:
            self.layout.label(text="(speeds not found)", icon='ERROR')
            return
        self.layout.label(text="same in every file", icon='INFO')
        _draw_speeds(self.layout, p)


CLASSES = (CubeKitPrefs, CUBEKIT_OT_speed_reset, CUBEKIT_PT_move,
           CUBEKIT_OT_move, CUBEKIT_OT_look, CUBEKIT_OT_hover, CUBEKIT_OT_brush_size)

# What W A S D Z X and the middle mouse did before, moved to F-keys so nothing is lost.
# (keymap, operator, key, extra properties)
MOVED = [
    ("Mesh", "mesh.select_all", 'F7', {"action": 'TOGGLE'}),         # was A: pick all / none
    ("Object Mode", "object.select_all", 'F7', {"action": 'TOGGLE'}),
    ("Mesh", "transform.resize", 'F8', {}),                         # was S: scale
    ("Object Mode", "transform.resize", 'F8', {}),
    ("3D View", "wm.call_menu_pie", 'F9', {"name": "VIEW3D_MT_shading_pie"}),   # was Z: shading wheel
    ("3D View", "view3d.rotate", 'F10', {}),                        # was the middle mouse: Blender's orbit
]


def bind(kc, keys):
    """Add the movement keys to every 3D-view keymap they must win in. keys: list to append to."""
    def add(kmname, idname, key, value='PRESS', shift=False, ctrl=False, any_mod=False, **props):
        km = kc.keymaps.new(name=kmname, space_type='VIEW_3D' if kmname == "3D View" else 'EMPTY')
        kmi = km.keymap_items.new(idname, type=key, value=value, shift=shift, ctrl=ctrl, any=any_mod)
        for k, v in props.items():
            setattr(kmi.properties, k, v)
        keys.append((km, kmi))

    for kmname in ("Object Mode", "Mesh", "3D View"):
        for key in list(MOVE_KEYS) + list(LIFT_KEYS):
            add(kmname, "cubekit.move", key)
            add(kmname, "cubekit.move", key, shift=True)
        add(kmname, "cubekit.look", 'MIDDLEMOUSE')
    add("Mesh", "cubekit.brush_size", 'WHEELUPMOUSE', ctrl=True, bigger=True)
    add("Mesh", "cubekit.brush_size", 'WHEELDOWNMOUSE', ctrl=True, bigger=False)
    for kmname, idname, key, props in MOVED:
        add(kmname, idname, key, **props)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    _hover["handle"] = bpy.types.SpaceView3D.draw_handler_add(_draw_hover, (), 'WINDOW', 'POST_PIXEL')


def unregister():
    if _hover["handle"]:
        bpy.types.SpaceView3D.draw_handler_remove(_hover["handle"], 'WINDOW')
        _hover["handle"] = None
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
