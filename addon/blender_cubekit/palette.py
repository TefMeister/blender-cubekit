# The colour palette, laid out like Microsoft Paint's (asked for by Tefa, 2026-10-03):
#   - a grid of colour squares: click one and the picked sides (or whole cubes) take it at once
#   - two rows of Paint's own colours, then your own colours underneath: every Add to my colours
#     puts a new square at the end, so the palette grows downwards (Tefa, 2026-10-03)
#   - the big square at the top is the colour in hand: clicking a colour puts it there, and you can
#     fine-tune it there before adding it
#   - keys 1 to 0 on the main keyboard (not the numpad):
#       hover a colour square and press a number   -> that number now means that colour
#       hover a cube in edit mode and press it      -> paints the side under the mouse with it,
#                                                      or the whole cube when F is on whole cubes
#   - Ctrl + click on one of your own colours takes that square away
# The number a colour carries is drawn in the corner of its square.
import bpy
import bpy.utils.previews

# Paint's colours, sRGB 0-255, in Paint's order (top row, then second row)
PAINT_COLOURS = [
    (0, 0, 0), (127, 127, 127), (136, 0, 21), (237, 28, 36), (255, 127, 39),
    (255, 242, 0), (34, 177, 76), (0, 162, 232), (63, 72, 204), (163, 73, 164),
    (255, 255, 255), (195, 195, 195), (185, 122, 87), (255, 174, 201), (255, 201, 14),
    (239, 228, 176), (181, 230, 29), (153, 217, 234), (112, 146, 190), (200, 191, 231),
]
COLUMNS = 10
PRESETS = len(PAINT_COLOURS)      # your own colours start after these
NUMBER_KEYS = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'ZERO']
ICON_PX = 32
SWATCH_SCALE = 1.5               # how tall the colour squares are drawn

# a 3 x 5 pixel font for the number in a square's corner
DIGITS = {
    '1': ["010", "110", "010", "010", "111"], '2': ["111", "001", "111", "100", "111"],
    '3': ["111", "001", "111", "001", "111"], '4': ["101", "101", "111", "001", "001"],
    '5': ["111", "100", "111", "001", "111"], '6': ["111", "100", "111", "101", "111"],
    '7': ["111", "001", "010", "010", "010"], '8': ["111", "101", "111", "101", "111"],
    '9': ["111", "101", "111", "001", "111"], '0': ["111", "101", "101", "101", "111"],
}

_icons = {"coll": None}


class CubeKitColour(bpy.types.PropertyGroup):
    color: bpy.props.FloatVectorProperty(name="colour", subtype='COLOR_GAMMA', size=3, min=0.0, max=1.0,
                                         default=(0.8, 0.8, 0.8))
    used: bpy.props.BoolProperty(default=True)


def _is_paint_layout(pal):
    return len(pal) >= PRESETS and all(
        abs(pal[i].color[j] - PAINT_COLOURS[i][j] / 255) < 1e-3 for i in range(PRESETS) for j in range(3))


def ensure(scene):
    """Give the scene the Paint layout: Paint's 20 colours, then your own. Colours from an older
    palette become your own, so nothing is lost. Empty squares from 0.6.0 are dropped."""
    pal = scene.cubekit_palette
    if _is_paint_layout(pal):
        for i in reversed(range(PRESETS, len(pal))):
            if not pal[i].used:
                _remove(scene, i)
        return
    old = [tuple(p.color) for p in pal if p.used]
    pal.clear()
    for rgb in PAINT_COLOURS:
        pal.add().color = tuple(c / 255 for c in rgb)
    for rgb in old:
        pal.add().color = rgb
    hk = scene.cubekit_hotkeys
    if all(h < 0 for h in hk):
        for i in range(10):               # 1 to 0 start as Paint's top row
            hk[i] = i


def _remove(scene, index):
    """Take one of your own squares away; number keys pointing past it move down with it."""
    scene.cubekit_palette.remove(index)
    hk = scene.cubekit_hotkeys
    for i in range(10):
        if hk[i] == index:
            hk[i] = -1
        elif hk[i] > index:
            hk[i] -= 1
    if scene.cubekit_active >= len(scene.cubekit_palette):
        scene.cubekit_active = 0


def _number_of(scene, index):
    for i, h in enumerate(scene.cubekit_hotkeys):
        if h == index:
            return "1234567890"[i]
    return None


def _icon(rgb, used, number, active):
    """A coloured square with its number in the corner, made once and kept."""
    coll = _icons["coll"]
    key = "%.3f_%.3f_%.3f_%d_%s_%d" % (rgb[0], rgb[1], rgb[2], used, number or "-", active)
    if key in coll:
        return coll[key].icon_id
    n = ICON_PX
    px = []
    light = (rgb[0] * 0.3 + rgb[1] * 0.59 + rgb[2] * 0.11) > 0.5
    ink = (0.0, 0.0, 0.0) if light else (1.0, 1.0, 1.0)
    glyph = DIGITS.get(number) if number else None
    for y in range(n):
        for x in range(n):
            edge = min(x, y, n - 1 - x, n - 1 - y)
            if not used:
                c = (0.55, 0.55, 0.55, 1.0) if edge < 1 else (0.0, 0.0, 0.0, 0.0)
            elif active and edge < 3:
                c = (1.0, 0.6, 0.1, 1.0)
            elif edge < 1:
                c = (0.15, 0.15, 0.15, 1.0)
            else:
                c = (rgb[0], rgb[1], rgb[2], 1.0)
            if glyph and used:
                gx, gy = (x - 4) // 2, (n - 1 - y - 4) // 2      # top-left corner, 2 x size
                if 0 <= gx < 3 and 0 <= gy < 5 and glyph[gy][gx] == "1":
                    c = ink + (1.0,)
            px.extend(c)
    p = coll.new(key)
    p.icon_size = (n, n)
    p.icon_pixels_float = px
    p.image_size = (n, n)
    p.image_pixels_float = px
    return p.icon_id


def draw(layout, context):
    scene = context.scene
    if not _is_paint_layout(scene.cubekit_palette):
        layout.operator("cubekit.palette_setup", icon='COLOR')
        return
    pal = scene.cubekit_palette
    active = scene.cubekit_active
    top = layout.row()
    big = top.column()
    big.scale_y = 2.0
    big.prop(scene, "cubekit_mix", text="")
    tips = top.column(align=True)
    tips.label(text="click a colour = paint")
    tips.label(text="hover + 1-0 = give it a key")
    grid = layout.grid_flow(row_major=True, columns=COLUMNS, even_columns=True, even_rows=True, align=True)
    for i, item in enumerate(pal):
        cell = grid.column(align=True)
        cell.scale_y = SWATCH_SCALE
        icon = _icon(tuple(item.color), item.used, _number_of(scene, i), i == active)
        op = cell.operator("cubekit.apply_colour", text="", icon_value=icon, emboss=False)
        op.index = i
    layout.operator("cubekit.palette_add", text="Add to my colours", icon='ADD')


# ---- operators ----

def _paint(context, rgb, keys_fn=None):
    from . import _for_each_edited
    whole = context.window_manager.cubekit_whole
    return _for_each_edited(context, lambda edit, ob, V, keys: edit.paint(ob, V, keys, rgb, whole))


class CUBEKIT_OT_apply_colour(bpy.types.Operator):
    bl_idname = "cubekit.apply_colour"
    bl_label = "Paint"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()

    @classmethod
    def description(cls, context, props):
        n = _number_of(context.scene, props.index)
        own = props.index >= PRESETS
        return ("Click: paint the picked sides (or cubes) with this colour"
                + ("; key %s" % n if n else "") + ". Hover and press 1-0 to give it a key"
                + (". Ctrl + click: take this square away" if own else ""))

    def invoke(self, context, event):
        scene = context.scene
        pal = scene.cubekit_palette
        if not (0 <= self.index < len(pal)):
            return {'CANCELLED'}
        item = pal[self.index]
        if self.index >= PRESETS and event.ctrl:
            _remove(scene, self.index)
            return {'FINISHED'}
        scene.cubekit_active = self.index
        scene.cubekit_mix = item.color          # the colour in hand, ready to fine-tune and add
        if context.mode == 'EDIT_MESH':
            _paint(context, tuple(item.color))
        return {'FINISHED'}


class CUBEKIT_OT_palette_add(bpy.types.Operator):
    """Add the colour in the big square as a new square at the end of your colours"""
    bl_idname = "cubekit.palette_add"
    bl_label = "Add to my colours"

    def execute(self, context):
        scene = context.scene
        ensure(scene)
        item = scene.cubekit_palette.add()
        item.color = scene.cubekit_mix
        scene.cubekit_active = len(scene.cubekit_palette) - 1
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class CUBEKIT_OT_palette_setup(bpy.types.Operator):
    """Lay the palette out like Paint's"""
    bl_idname = "cubekit.palette_setup"
    bl_label = "Set up the colours"

    def execute(self, context):
        ensure(context.scene)
        return {'FINISHED'}


class CUBEKIT_OT_set_hotkey(bpy.types.Operator):
    """Over a colour square: give that colour this number key"""
    bl_idname = "cubekit.set_hotkey"
    bl_label = "Give a colour a number key"

    slot: bpy.props.IntProperty()

    def invoke(self, context, event):
        op = getattr(context, "button_operator", None)
        index = None
        if op is not None and op.bl_rna.identifier == "CUBEKIT_OT_apply_colour":
            index = op.index
        if index is None:
            return {'PASS_THROUGH'}
        scene = context.scene
        if not scene.cubekit_palette[index].used:
            return {'CANCELLED'}
        for i, h in enumerate(scene.cubekit_hotkeys):     # one number per colour
            if h == index:
                scene.cubekit_hotkeys[i] = -1
        scene.cubekit_hotkeys[self.slot] = index
        scene.cubekit_active = index
        for area in context.screen.areas:
            area.tag_redraw()
        self.report({'INFO'}, "key %s = this colour" % "1234567890"[self.slot])
        return {'FINISHED'}


class CUBEKIT_OT_paint_hover(bpy.types.Operator):
    """Edit mode, 1-0: paint the side under the mouse (or its whole cube, when F is on whole cubes)
with the colour that has this number"""
    bl_idname = "cubekit.paint_hover"
    bl_label = "Paint under the mouse"
    bl_options = {'REGISTER', 'UNDO'}

    slot: bpy.props.IntProperty()

    def invoke(self, context, event):
        from bpy_extras import view3d_utils
        from . import _kit, _edit_objects
        scene = context.scene
        index = scene.cubekit_hotkeys[self.slot]
        if index < 0 or index >= len(scene.cubekit_palette) or not scene.cubekit_palette[index].used:
            self.report({'WARNING'}, "no colour on key %s yet: hover a colour square and press it" % "1234567890"[self.slot])
            return {'CANCELLED'}
        rgb = tuple(scene.cubekit_palette[index].color)
        region, rv3d = context.region, context.region_data
        if rv3d is None:
            return {'PASS_THROUGH'}
        coord = (event.mouse_region_x, event.mouse_region_y)
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        hit, _loc, _n, face, obj, _m = scene.ray_cast(context.evaluated_depsgraph_get(), origin, direction)
        if not hit:
            return {'CANCELLED'}
        ob = obj.original
        if ob not in _edit_objects(context):
            self.report({'WARNING'}, "that part is not being edited (Tab on it first)")
            return {'CANCELLED'}
        _, edit, V = _kit()
        if not edit.has_colours(ob):
            self.report({'WARNING'}, "not ready for cube editing yet (use Every cube on its own)")
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='OBJECT')
        s = edit.Solid(ob, V)
        keep = s.selected_keys()
        key = s.key_of(ob.data.polygons[face])
        edit.paint(ob, V, [key], rgb, context.window_manager.cubekit_whole, select=keep)
        bpy.ops.object.mode_set(mode='EDIT')
        scene.cubekit_active = index
        return {'FINISHED'}


CLASSES = (CubeKitColour, CUBEKIT_OT_apply_colour, CUBEKIT_OT_palette_add, CUBEKIT_OT_palette_setup,
           CUBEKIT_OT_set_hotkey, CUBEKIT_OT_paint_hover)


def bind(kc, keys):
    for i, key in enumerate(NUMBER_KEYS):
        for kmname, idname, space in (("User Interface", "cubekit.set_hotkey", 'EMPTY'),
                                      ("Mesh", "cubekit.paint_hover", 'EMPTY')):
            km = kc.keymaps.new(name=kmname, space_type=space)
            kmi = km.keymap_items.new(idname, type=key, value='PRESS')
            kmi.properties.slot = i
            keys.append((km, kmi))


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.cubekit_palette = bpy.props.CollectionProperty(type=CubeKitColour)
    bpy.types.Scene.cubekit_hotkeys = bpy.props.IntVectorProperty(size=10, default=[-1] * 10)
    bpy.types.Scene.cubekit_active = bpy.props.IntProperty(default=0, min=0)
    bpy.types.Scene.cubekit_mix = bpy.props.FloatVectorProperty(
        name="mixer", subtype='COLOR_GAMMA', size=3, min=0.0, max=1.0, default=(0.5, 0.5, 0.5),
        description="The colour in hand: click a colour to put it here, fine-tune it, then Add to my colours")
    _icons["coll"] = bpy.utils.previews.new()
    try:
        ensure(bpy.context.scene)
    except Exception:
        pass


def unregister():
    if _icons["coll"]:
        bpy.utils.previews.remove(_icons["coll"])
        _icons["coll"] = None
    for name in ("cubekit_palette", "cubekit_hotkeys", "cubekit_active", "cubekit_mix"):
        delattr(bpy.types.Scene, name)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
