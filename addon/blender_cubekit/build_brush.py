# The build brush (B switches it on and off). While it is on, in edit mode, the left mouse held and swept
# over the model adds ONE cube on top of every surface square it passes over, and the right mouse carves
# ONE cube out from under every square. Tefa, 2026-10-23: "adds cubes as i go over the model, just 1 cube on
# top of the surface at a time, and doesn't add a cube on top of the already added cube as long as the left
# mouse button is held, same for carving and the right mouse button does the carving. this mode has to be
# toggleable".
#
# How it keeps to one layer: during a stroke the mouse is tested against the model as it was when the button
# went down, so a cube added (or a hole carved) by this stroke can never be hit again by it. What the stroke
# will do shows as see-through boxes while the button is held; it happens when the button is let go, in one
# go, as one undo step. Let go and press again to build (or carve) the next layer.
import bpy

from . import _kit, _edit_objects

ADD_COLOUR = (0.35, 1.0, 0.45, 0.45)     # the boxes of cubes about to be added
CARVE_COLOUR = (1.0, 0.25, 0.2, 0.45)    # the cubes about to be carved out
STEP_PX = 3.0                            # a fast sweep is tested every this many pixels, so no square is skipped


def _faces_of(me):
    """A ray-test tree of the mesh as it is now (its faces keep the mesh's face numbers)."""
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons([v.co for v in me.vertices], [p.vertices for p in me.polygons], all_triangles=False)


def _draw(self, context):
    import gpu
    from gpu_extras.batch import batch_for_shader
    if not self._tris:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    batch = batch_for_shader(shader, 'TRIS', {"pos": self._tris})
    shader.bind()
    shader.uniform_float("color", CARVE_COLOUR if self.carve else ADD_COLOUR)
    batch.draw(shader)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def _box_tris(corners, normal, depth):
    """Triangles of the box standing on (or, with a negative depth, sunk into) a square side."""
    top = [c + normal * depth for c in corners]
    quads = [corners, top] + [[corners[i], corners[(i + 1) % 4], top[(i + 1) % 4], top[i]] for i in range(4)]
    out = []
    for q in quads:
        out += [tuple(q[0]), tuple(q[1]), tuple(q[2]), tuple(q[0]), tuple(q[2]), tuple(q[3])]
    return out


class CUBEKIT_OT_build_toggle(bpy.types.Operator):
    """B: the build brush on or off. On: left mouse sweeps add one cube on top of the surface, right mouse
sweeps carve one cube out. Off: the mouse picks as before"""
    bl_idname = "cubekit.build_toggle"
    bl_label = "Build brush on / off"

    def execute(self, context):
        wm = context.window_manager
        wm.cubekit_build = not wm.cubekit_build
        self.report({'INFO'}, "BUILD BRUSH ON: left mouse adds a layer, right mouse carves one" if wm.cubekit_build
                    else "build brush off: the mouse picks again")
        return {'FINISHED'}


class CUBEKIT_OT_build_stroke(bpy.types.Operator):
    """Build brush stroke: one cube added on top of (or carved out from under) every square swept over"""
    bl_idname = "cubekit.build_stroke"
    bl_label = "Build brush stroke"
    bl_options = {'REGISTER', 'UNDO'}

    carve: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.window_manager.cubekit_build

    def invoke(self, context, event):
        obs = [o for o in _edit_objects(context) if o.get("cubekit_voxel_m")]
        if not obs:
            self.report({'WARNING'}, "not a cube-edit part: use Every cube on its own first")
            return {'CANCELLED'}
        self._names = [o.name for o in obs]
        bpy.ops.object.mode_set(mode='OBJECT')          # the mesh as it is now, read once for the whole stroke
        self._trees = {}
        for ob in obs:
            self._trees[ob.name] = _faces_of(ob.data)
        self._hits = {n: set() for n in self._names}    # face indices swept over
        self._tris = []
        self._button = 'RIGHTMOUSE' if self.carve else 'LEFTMOUSE'
        self._last = None
        self._test(context, (event.mouse_region_x, event.mouse_region_y))
        self._handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (self, context), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _ray_hit(self, context, co):
        from bpy_extras import view3d_utils
        region, rv3d = context.region, context.region_data
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, co)
        ray = view3d_utils.region_2d_to_vector_3d(region, rv3d, co)
        best = None
        for name in self._names:
            ob = bpy.data.objects[name]
            inv = ob.matrix_world.inverted()
            d = (inv.to_3x3() @ ray).normalized()
            hit, normal, idx, _ = self._trees[name].ray_cast(inv @ origin, d)
            if hit is None or normal.dot(d) > 0:         # nothing, or a wall seen from inside the model
                continue
            dist = (ob.matrix_world @ hit - origin).length
            if best is None or dist < best[0]:
                best = (dist, ob, idx)
        return best

    def _test(self, context, co):
        """Every square under the mouse between the last test and now."""
        pts = [co]
        if self._last is not None:
            dx, dy = co[0] - self._last[0], co[1] - self._last[1]
            n = int(max(abs(dx), abs(dy)) / STEP_PX)
            pts = [(self._last[0] + dx * i / (n + 1), self._last[1] + dy * i / (n + 1)) for i in range(1, n + 2)]
        self._last = co
        for p in pts:
            best = self._ray_hit(context, p)
            if best is None:
                continue
            _d, ob, idx = best
            if idx in self._hits[ob.name]:
                continue
            self._hits[ob.name].add(idx)
            self._preview(ob, idx)

    def _preview(self, ob, idx):
        me = ob.data
        poly = me.polygons[idx]
        v = ob["cubekit_voxel_m"]
        sub = me.attributes.get("cubekit_subsize")
        k = sub.data[idx].value if sub is not None else 0
        size = v * (k / 4.0 if k else 1.0)                # a smaller cube's side stands for a smaller cube
        mw = ob.matrix_world
        corners = [mw @ me.vertices[i].co for i in poly.vertices]
        if len(corners) != 4:
            return
        n = (mw.to_3x3() @ poly.normal).normalized()
        self._tris += _box_tris(corners, n, -size if self.carve else size)

    def _finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        self._tris = []
        context.area.tag_redraw()

    def _apply(self, context):
        _, edit, V = _kit()
        done = 0
        for name in self._names:
            idx = self._hits[name]
            if not idx:
                continue
            ob = bpy.data.objects[name]
            s = edit.Solid(ob, V)
            keys, seen = [], set()
            for i in sorted(idx):
                poly = ob.data.polygons[i]
                if len(poly.vertices) != 4:
                    continue
                key = s.key_of(poly)
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
            if not keys:
                continue
            (edit.shrink if self.carve else edit.grow)(ob, V, keys)
            done += len(keys)
        return done

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self._test(context, (event.mouse_region_x, event.mouse_region_y))
            context.area.tag_redraw()
        elif event.type == self._button and event.value == 'RELEASE':
            self._finish(context)
            n = self._apply(context)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')       # nothing stays picked: ready for the next layer
            self.report({'INFO'}, "%s %d cube(s)" % ("carved" if self.carve else "added", n))
            return {'FINISHED'}
        elif event.type == 'ESC':
            self._finish(context)
            bpy.ops.object.mode_set(mode='EDIT')
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


CLASSES = (CUBEKIT_OT_build_toggle, CUBEKIT_OT_build_stroke)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.cubekit_build = bpy.props.BoolProperty(
        name="build brush", default=False,
        description="On: left mouse sweeps add one cube on top of the surface, right mouse sweeps carve one out. B toggles")


def unregister():
    del bpy.types.WindowManager.cubekit_build
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)


def bind(kc, keys):
    """The stroke goes FIRST on the mouse buttons: while the build brush is off its poll fails and the
    click falls through to the picking brush."""
    km = kc.keymaps.new(name="Mesh", space_type='EMPTY')
    for button, carve in (('LEFTMOUSE', False), ('RIGHTMOUSE', True)):
        kmi = km.keymap_items.new("cubekit.build_stroke", type=button, value='PRESS')
        kmi.properties.carve = carve
        keys.append((km, kmi))
    kmi = km.keymap_items.new("cubekit.build_toggle", type='B', value='PRESS')
    keys.append((km, kmi))
