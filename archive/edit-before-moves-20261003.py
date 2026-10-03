# Cube-level editing of a pick-mode mesh: add a cube, remove a cube, recolour a side, split a side for
# fine detail. The add-on's E, Q, C and colour palette run through here (asked for by Tefa, 2026-10-03).
#
# A pick-mode mesh only holds the EXPOSED faces, so on its own it cannot say whether the cube behind
# a face is solid or air (the mug's wall is solid two cubes deep, the mug's inside is air; neither
# has a face in the mesh). Solid() works that out once by flooding from outside the model: a face
# is a wall between a solid cube and an air cube, so every cube the flood cannot reach is solid.
# The answer is kept on the object ("cubekit_cells"), and from then on the object carries the full
# cube list, which is rewritten after every edit.
#
# Colours live on the mesh as two face-corner colour attributes:
#   cubekit_base   the colour as painted (what a palette click sets)
#   cubekit_view   base x the per-direction shade x a per-cube wobble: what is shown
# The first conversion of an atlas-textured pick mesh samples each face's texel from the atlas and
# divides the shade back out. After that the UVs are gone: a pick file is for editing, and the game
# file is rebuilt from it.
import math

import bpy
from mathutils import Vector

DIRS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
# Object space: z up, +-x across, +-y along. Top lightest, underneath darkest.
SHADE = {(0, 0, 1): 1.12, (0, 0, -1): 0.55, (1, 0, 0): 0.88, (-1, 0, 0): 0.88,
         (0, 1, 0): 0.74, (0, -1, 0): 0.74}
NOISE = 0.05
BASE, VIEW = "cubekit_base", "cubekit_view"
# Colours are kept as sRGB 0-1 (what a colour picker shows, and what the atlas holds). Blender's
# colour attributes are linear, so they are converted on the way in and out.


def to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_srgb(c):
    c = max(0.0, c)
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def hash01(x, y, z, seed=0):
    h = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def _dir_of(n):
    ax = max(range(3), key=lambda i: abs(n[i]))
    d = [0, 0, 0]
    d[ax] = 1 if n[ax] > 0 else -1
    return tuple(d)


def _atlas_pixels(ob):
    """(pixels as a flat numpy array, w, h) of the image the object's material shows, or None."""
    try:
        import numpy as np
    except ImportError:
        return None
    for slot in ob.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        for n in mat.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                img = n.image
                w, h = img.size
                px = np.empty(w * h * 4, dtype='f')
                img.pixels.foreach_get(px)
                return px, w, h
    return None

# A side of a cube can be split for fine detail (C). Its colours are always kept as a 4 x 4 grid
# (FINE x FINE); what is shown depends on its level:
#   level 1  four quarters - a quarter whose four fine colours match is one square, one that holds
#            detail painted at level 2 shows that detail but is picked and painted as one quarter
#   level 2  sixteen small squares, each picked and painted on its own
# C goes plain -> 1 -> 2 -> 1 -> 2 ...; Shift + C joins a side back into one (Tefa, 2026-10-03).
FINE = 4
LEVEL, GROUP = "cubekit_level", "cubekit_group"
MERGE_KEEP = 4      # going back to bigger cubes: a big cube stays when at least 4 of its 8 small ones are there


def _quarter_of(fi):
    """The four fine squares in the same quarter as fine square fi."""
    fu, fv = fi % FINE, fi // FINE
    qu, qv = fu // 2 * 2, fv // 2 * 2
    return tuple(sorted((qu + a) + FINE * (qv + b) for a in range(2) for b in range(2)))


class Solid:
    """The cubes of one object: which cells are solid, and the colour of every cube and face."""

    def __init__(self, ob, voxel_m):
        # The mesh says what size its cubes are (written by write()); that wins over the caller's
        # number, so an object not yet made finer can never be read at the wrong size.
        voxel_m = ob.get("cubekit_voxel_m", voxel_m)
        self.ob, self.v = ob, voxel_m
        me = ob.data
        if "cubekit_off" in ob:
            self.off = list(ob["cubekit_off"])
        else:
            c0 = me.vertices[0].co
            self.off = [c0[i] / voxel_m - math.floor(c0[i] / voxel_m + 1e-6) for i in range(3)]
        self.faces = {}            # (cell, dir) -> base rgb (0-1) of that face
        self.split = {}            # (cell, dir) -> [rgb] * 16: a split side's 4 x 4 fine colours
        self.level = {}            # (cell, dir) -> 1 or 2: how a split side is shown and picked
        self.cell_rgb = {}         # cell -> base rgb, the cube's own colour
        self.cells = set()
        self._read_mesh(me)
        if "cubekit_cells" in ob and len(ob["cubekit_cells"]) >= 3:
            flat = list(ob["cubekit_cells"])
            self.cells = {tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)}
            if "cubekit_cell_rgb" in ob:
                rgb = list(ob["cubekit_cell_rgb"])
                for i, c in enumerate(tuple(flat[j:j + 3]) for j in range(0, len(flat), 3)):
                    r = rgb[i * 3:i * 3 + 3]
                    if r and r[0] >= 0:
                        self.cell_rgb[c] = tuple(r)
        else:
            self._flood()
        for (cell, d), rgb in self.faces.items():
            self.cell_rgb.setdefault(cell, rgb)
        self._colour_inside()

    def _colour_inside(self):
        """Cubes deep inside the model were never painted, so a hole dug into it showed plain grey
        walls that looked like cubes had been ADDED (Tefa, 2026-10-03). Every unpainted cube takes the
        colour of the nearest painted one, spreading inwards from the surface, so the material simply
        carries on inside."""
        if all(c in self.cell_rgb for c in self.cells):
            return
        frontier = [c for c in self.cells if c in self.cell_rgb]
        while frontier:
            nxt = []
            for c in frontier:
                rgb = self.cell_rgb[c]
                for d in DIRS:
                    n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
                    if n in self.cells and n not in self.cell_rgb:
                        self.cell_rgb[n] = rgb
                        nxt.append(n)
            frontier = nxt

    # ---- reading ----
    def grid(self, p):
        return [p[i] / self.v - self.off[i] for i in range(3)]

    def _place(self, me, poly):
        """(cell, dir, fine squares the face covers, its size in fine squares, its level)."""
        d = _dir_of(poly.normal)
        centre = poly.center - Vector(d) * (0.5 * self.v)
        cell = tuple(math.floor(c) for c in self.grid(centre))
        ax = [i for i in range(3) if d[i]][0]
        ua, va = [i for i in range(3) if i != ax]
        gs = [self.grid(me.vertices[i].co) for i in poly.vertices]
        fu0 = round(min((g[ua] - cell[ua]) * FINE for g in gs))
        fv0 = round(min((g[va] - cell[va]) * FINE for g in gs))
        size = max(1, round(max((g[ua] - cell[ua]) * FINE for g in gs)) - fu0)
        covered = tuple(sorted((fu0 + a) + FINE * (fv0 + b) for a in range(size) for b in range(size)))
        lv_attr = me.attributes.get(LEVEL)
        if lv_attr is not None:
            level = lv_attr.data[poly.index].value
        else:
            level = 0 if size == FINE else 1          # files from before 16-way splitting
        return cell, d, covered, size, level

    def _read_mesh(self, me):
        base = me.color_attributes.get(BASE)
        px = None if base else _atlas_pixels(self.ob)
        uvl = me.uv_layers.active if px else None
        for poly in me.polygons:
            if len(poly.vertices) != 4:
                continue
            cell, d, covered, size, level = self._place(me, poly)
            if base:
                col = base.data[poly.loop_indices[0]].color
                rgb = (to_srgb(col[0]), to_srgb(col[1]), to_srgb(col[2]))
            elif px is not None and uvl:
                u = sum(uvl.data[l].uv[0] for l in poly.loop_indices) / 4
                w = sum(uvl.data[l].uv[1] for l in poly.loop_indices) / 4
                pixels, pw, ph = px
                x = min(pw - 1, max(0, int(u * pw)))
                y = min(ph - 1, max(0, int(w * ph)))
                i = (y * pw + x) * 4
                k = SHADE[d]
                rgb = tuple(min(1.0, float(pixels[i + j]) / k) for j in range(3))
            else:
                rgb = (0.6, 0.6, 0.6)
            key = (cell, d)
            if size == FINE and level == 0:
                self.faces[key] = rgb
            else:
                cols = self.split.setdefault(key, [None] * (FINE * FINE))
                for fi in covered:
                    cols[fi] = rgb
                self.level[key] = max(1, level)
                self.faces.setdefault(key, rgb)
            self.cells.add(cell)
        for key, cols in self.split.items():               # a square that went missing: its side's colour
            for i in range(FINE * FINE):
                if cols[i] is None:
                    cols[i] = self.faces.get(key, (0.6, 0.6, 0.6))

    def _flood(self):
        """Air = every cell reachable from outside without crossing a face. The rest is solid."""
        if not self.faces:
            return
        cs = [c for c, _ in self.faces]
        lo = [min(c[i] for c in cs) - 1 for i in range(3)]
        hi = [max(c[i] for c in cs) + 1 for i in range(3)]
        walls = set()
        for (cell, d) in self.faces:
            walls.add((cell, d))
            walls.add(((cell[0] + d[0], cell[1] + d[1], cell[2] + d[2]), (-d[0], -d[1], -d[2])))
        start = tuple(lo)
        air = {start}
        stack = [start]
        while stack:
            a = stack.pop()
            for d in DIRS:
                b = (a[0] + d[0], a[1] + d[1], a[2] + d[2])
                if b in air or any(b[i] < lo[i] or b[i] > hi[i] for i in range(3)):
                    continue
                if (a, d) in walls:
                    continue
                air.add(b)
                stack.append(b)
        for x in range(lo[0], hi[0] + 1):
            for y in range(lo[1], hi[1] + 1):
                for z in range(lo[2], hi[2] + 1):
                    c = (x, y, z)
                    if c not in air:
                        self.cells.add(c)

    # ---- editing ----
    def _forget(self, key):
        self.faces.pop(key, None)
        self.split.pop(key, None)
        self.level.pop(key, None)

    def add(self, cell, rgb):
        self.cells.add(cell)
        self.cell_rgb[cell] = rgb
        for d in DIRS:
            self._forget((cell, d))

    def remove(self, cell):
        self.cells.discard(cell)
        for d in DIRS:
            self._forget((cell, d))

    def paint_face(self, cell, d, rgb, covered=None):
        key = (cell, d)
        if covered is not None and key in self.split:
            for fi in covered:
                self.split[key][fi] = rgb
        else:
            self._forget(key)
            self.faces[key] = rgb

    def paint_cube(self, cell, rgb):
        self.cell_rgb[cell] = rgb
        for d in DIRS:
            self._forget((cell, d))

    def cycle_split(self, cell, d):
        """C: plain -> 4 -> 16 -> 4 -> 16 ... Colours painted at 16 are kept at 4."""
        key = (cell, d)
        if key not in self.split:
            self.split[key] = [self.colour_of(cell, d)] * (FINE * FINE)
            self.level[key] = 1
        else:
            self.level[key] = 2 if self.level.get(key, 1) == 1 else 1

    def join(self, cell, d):
        """Shift + C: the side becomes one square again, in its most common colour."""
        key = (cell, d)
        cols = self.split.get(key)
        if not cols:
            return
        rgb = max(set(cols), key=cols.count)
        self._forget(key)
        self.faces[key] = rgb

    def exposed(self, cell):
        return [d for d in DIRS if (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2]) not in self.cells]

    def colour_of(self, cell, d):
        return self.faces.get((cell, d)) or self.cell_rgb.get(cell) or (0.6, 0.6, 0.6)

    # ---- writing ----
    def _squares(self, key):
        """[(fu, fv, size, covered, rgb, level, group)] for one side; group > 0 ties together the
        small squares of a level-1 quarter that holds detail."""
        cols = self.split.get(key)
        if not cols:
            return [(0, 0, FINE, tuple(range(FINE * FINE)), self.colour_of(*key), 0, 0)]
        level = self.level.get(key, 1)
        out = []
        if level == 2:
            for fv in range(FINE):
                for fu in range(FINE):
                    fi = fu + FINE * fv
                    out.append((fu, fv, 1, (fi,), cols[fi], 2, 0))
            return out
        for qv in (0, 2):
            for qu in (0, 2):
                quarter = _quarter_of(qu + FINE * qv)
                if len({cols[fi] for fi in quarter}) == 1:
                    out.append((qu, qv, 2, quarter, cols[quarter[0]], 1, 0))
                else:
                    self._group += 1
                    for fi in quarter:
                        out.append((fi % FINE, fi // FINE, 1, quarter, cols[fi], 1, self._group))
        return out

    def write(self, select=()):
        """Rebuild the object's mesh from the cube list: one quad per exposed face (or per square of a
        split side), each cube with its own corners. select: keys to leave picked."""
        ob, v = self.ob, self.v
        verts, vidx, polys, cols_b, cols_v, keys, levels, groups = [], {}, [], [], [], [], [], []
        off = self.off
        self._group = 0
        for cell in self.cells:
            for d in DIRS:
                nb = (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2])
                if nb in self.cells:
                    continue
                ax = [i for i in range(3) if d[i]][0]
                ua, va = [i for i in range(3) if i != ax]
                planeF = FINE * (cell[ax] + (1 if d[ax] > 0 else 0))     # corners in fine units
                self.faces.setdefault((cell, d), self.colour_of(cell, d))
                k = SHADE[d] * (1.0 + (hash01(*cell, 9) - 0.5) * 2 * NOISE)
                for fu, fv, size, covered, rgb, level, group in self._squares((cell, d)):
                    corners = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        p = [0, 0, 0]
                        p[ax] = planeF
                        p[ua] = FINE * cell[ua] + fu + du * size
                        p[va] = FINE * cell[va] + fv + dv * size
                        corners.append(tuple(p))
                    pts = [Vector(((p[0] / FINE + off[0]) * v, (p[1] / FINE + off[1]) * v, (p[2] / FINE + off[2]) * v))
                           for p in corners]
                    if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(Vector(d)) < 0:
                        corners.reverse()
                        pts.reverse()
                    ids = []
                    for kk, p in zip(corners, pts):
                        vkey = (cell, kk)
                        if vkey not in vidx:
                            vidx[vkey] = len(verts)
                            verts.append(p)
                        ids.append(vidx[vkey])
                    polys.append(ids)
                    view = tuple(min(1.0, c * k) for c in rgb)
                    cols_b.append(tuple(to_linear(c) for c in rgb))
                    cols_v.append(tuple(to_linear(c) for c in view))
                    keys.append((cell, d) if level == 0 else (cell, d, covered))
                    levels.append(level)
                    groups.append(group)
        old = ob.data
        me = bpy.data.meshes.new(old.name)
        me.from_pydata(verts, [], polys)
        me.update()
        for m in old.materials:
            me.materials.append(m)
        ab = me.color_attributes.new(BASE, 'FLOAT_COLOR', 'CORNER')
        av = me.color_attributes.new(VIEW, 'FLOAT_COLOR', 'CORNER')
        flat_b, flat_v = [], []
        for b, w in zip(cols_b, cols_v):
            flat_b += [b[0], b[1], b[2], 1.0] * 4
            flat_v += [w[0], w[1], w[2], 1.0] * 4
        ab.data.foreach_set("color", flat_b)
        av.data.foreach_set("color", flat_v)
        me.color_attributes.active_color = av
        me.color_attributes.render_color_index = me.color_attributes.find(VIEW)
        me.attributes.new(LEVEL, 'INT', 'FACE').data.foreach_set("value", levels)
        me.attributes.new(GROUP, 'INT', 'FACE').data.foreach_set("value", groups)
        # Edit mode reads the selection from the corners, so corners, edges and faces are all set:
        # only the given keys (none by default) come up picked. A plain (cell, dir) key picks every
        # square of that side.
        sel = set(select)
        whole = {k[:2] for k in sel if len(k) == 2}
        fsel = [k in sel or k[:2] in whole for k in keys]
        me.vertices.foreach_set("select", [False] * len(me.vertices))
        me.edges.foreach_set("select", [False] * len(me.edges))
        me.polygons.foreach_set("select", fsel)
        for poly, on in zip(me.polygons, fsel):
            if on:
                for vi in poly.vertices:
                    me.vertices[vi].select = True
        ob.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
        flat = []
        rgbs = []
        for c in self.cells:
            flat += list(c)
            r = self.cell_rgb.get(c)
            rgbs += list(r) if r else [-1.0, -1.0, -1.0]
        ob["cubekit_cells"] = flat
        ob["cubekit_cell_rgb"] = rgbs
        ob["cubekit_voxel_m"] = self.v
        ob["cubekit_off"] = list(self.off)
        return len(polys)

    def key_of(self, poly):
        """(cell, dir) of a plain side, or (cell, dir, fine squares) of a split side's square. A small
        square inside a level-1 quarter stands for its whole quarter."""
        me = self.ob.data
        cell, d, covered, size, level = self._place(me, poly)
        if level == 0:
            return (cell, d)
        if level == 1 and size == 1:
            covered = _quarter_of(covered[0])
        return (cell, d, covered)

    def selected_keys(self):
        """The key (see key_of) of every picked face, each once."""
        out = []
        seen = set()
        for poly in self.ob.data.polygons:
            if poly.select and len(poly.vertices) == 4:
                k = self.key_of(poly)
                if k not in seen:
                    seen.add(k)
                    out.append(k)
        return out


def has_colours(ob):
    return ob.type == 'MESH' and VIEW in ob.data.color_attributes


def convert(ob, voxel_m):
    """Atlas-textured pick mesh -> colour-attribute pick mesh with the full cube list. Returns faces."""
    s = Solid(ob, voxel_m)
    return s.write()


def grow(ob, voxel_m, keys, count=1, colour=None):
    """E: for every selected face, put count cubes outside it, in the face's colour (or colour); the
    last new cube's outer face becomes the selected one, so E E E builds a row. Returns the new keys."""
    s = Solid(ob, voxel_m)
    new = []
    for cell, d in {k[:2] for k in keys}:
        rgb = colour or s.colour_of(cell, d)
        c = cell
        for _ in range(count):
            c = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            s.add(c, rgb)
        new.append((c, d))
    s.write(new)
    return new


def shrink(ob, voxel_m, keys, count=1):
    """Q: for every selected face, remove the cube behind it; the next cube inward shows its face in
    the same direction and that becomes the selected one, so Q Q Q digs a row."""
    s = Solid(ob, voxel_m)
    new = []
    for cell, d in {k[:2] for k in keys}:
        rgb = s.colour_of(cell, d)
        c = cell
        for _ in range(count):
            if c not in s.cells:
                break
            s.remove(c)
            c = (c[0] - d[0], c[1] - d[1], c[2] - d[2])
            if c in s.cells and c not in s.cell_rgb:
                s.cell_rgb[c] = rgb
        if c in s.cells:
            new.append((c, d))
    s.write(new)
    return new


def remove_cubes(ob, voxel_m, keys):
    """Q with whole cubes picked: the picked cubes go."""
    s = Solid(ob, voxel_m)
    for k in keys:
        s.remove(k[0])
    s.write()


def paint(ob, voxel_m, keys, rgb, whole_cubes, select=None):
    """A palette click: the picked sides (or whole cubes) take the colour. select: what stays
    picked afterwards (default: the painted faces)."""
    s = Solid(ob, voxel_m)
    if whole_cubes:
        for k in keys:
            s.paint_cube(k[0], rgb)
    else:
        for k in keys:
            s.paint_face(k[0], k[1], rgb, k[2] if len(k) == 3 else None)
    s.write(keys if select is None else select)


def split(ob, voxel_m, keys, whole_cubes):
    """C: every picked side (or every outside side of a picked cube) goes one step finer: plain -> 4
    squares -> 16 -> back to 4, keeping every colour painted at 16. The cube keeps its size: this is
    detail on the surface, so the one-cube-size rule still holds."""
    s = Solid(ob, voxel_m)
    sides = set()
    for k in keys:
        for d in (s.exposed(k[0]) if whole_cubes else [k[1]]):
            sides.add((k[0], d))
    for cell, d in sides:
        s.cycle_split(cell, d)
    s.write(list(sides))
    return len(sides)


def join(ob, voxel_m, keys, whole_cubes):
    """Shift + C: every picked side (or every side of a picked cube) becomes one square again."""
    s = Solid(ob, voxel_m)
    sides = set()
    for k in keys:
        for d in (s.exposed(k[0]) if whole_cubes else [k[1]]):
            sides.add((k[0], d))
    for cell, d in sides:
        s.join(cell, d)
    s.write(list(sides))
    return len(sides)


def _stack(ob):
    flat = list(ob.get("cubekit_off_stack", []))
    return [flat[i:i + 3] for i in range(0, len(flat), 3)]


def _set_stack(ob, stack):
    ob["cubekit_off_stack"] = [x for off in stack for x in off]


def subdivide(ob, voxel_m):
    """One tier finer: every cube becomes 8 cubes of half the size, in the same place and colours.
    A split side's 4 x 4 fine colours land exactly on the four smaller sides that replace it."""
    s = Solid(ob, voxel_m)
    v = s.v
    _set_stack(ob, _stack(ob) + [list(s.off)])        # how to find the bigger grid again
    sh = [math.floor(2 * o + 1e-6) for o in s.off]
    new_off = [2 * o - sh[i] for i, o in enumerate(s.off)]
    cells, cell_rgb = set(), {}
    for c in s.cells:
        rgb = s.cell_rgb.get(c)
        for a in (0, 1):
            for b in (0, 1):
                for e in (0, 1):
                    n = (2 * c[0] + sh[0] + a, 2 * c[1] + sh[1] + b, 2 * c[2] + sh[2] + e)
                    cells.add(n)
                    if rgb:
                        cell_rgb[n] = rgb
    faces, split, level = {}, {}, {}
    for (cell, d), rgb in s.faces.items():
        if cell not in s.cells or (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2]) in s.cells:
            continue                                     # only the outside sides carry over
        ax = [i for i in range(3) if d[i]][0]
        ua, va = [i for i in range(3) if i != ax]
        cols = s.split.get((cell, d))
        for a in (0, 1):
            for b in (0, 1):
                o3 = [0, 0, 0]
                o3[ax] = 1 if d[ax] > 0 else 0
                o3[ua], o3[va] = a, b
                child = tuple(2 * cell[i] + sh[i] + o3[i] for i in range(3))
                if not cols:
                    faces[(child, d)] = rgb
                    continue
                fine = [None] * (FINE * FINE)
                for cv in range(FINE):
                    for cu in range(FINE):
                        fine[cu + FINE * cv] = cols[(2 * a + cu // 2) + FINE * (2 * b + cv // 2)]
                faces[(child, d)] = fine[0]
                if len(set(fine)) > 1:
                    split[(child, d)] = fine
                    level[(child, d)] = 1
    s.v, s.off = v / 2, new_off
    s.cells, s.cell_rgb, s.faces, s.split, s.level = cells, cell_rgb, faces, split, level
    return s.write()


def merge(ob, voxel_m):
    """One tier bigger: every block of 8 small cubes becomes one cube of twice the size. A block
    keeps its cube when at least MERGE_KEEP of its 8 small cubes are there, otherwise it goes: a hole
    smaller than a big cube cannot exist at the bigger size. Each side keeps its colours as finely
    as the bigger cube can hold them (a 4 x 4 grid per side)."""
    s = Solid(ob, voxel_m)
    stack = _stack(ob)
    if not stack:
        return 0                                      # never was finer: nothing bigger to go back to
    p_off = stack.pop()
    # the small grid sits at 2 x the big grid's offset, less a whole number of small cubes: work that
    # whole number out from both offsets, so float noise (0.9999 against 0.0) cannot shift it by one
    sh = [round(2 * p_off[i] - s.off[i]) for i in range(3)]
    count, rgbs = {}, {}
    for c in s.cells:
        p = tuple((c[i] - sh[i]) // 2 for i in range(3))
        count[p] = count.get(p, 0) + 1
        r = s.cell_rgb.get(c)
        if r:
            rgbs.setdefault(p, []).append(r)
    cells = {p for p, n in count.items() if n >= MERGE_KEEP}
    cell_rgb = {p: max(set(rgbs[p]), key=rgbs[p].count) for p in cells if p in rgbs}
    faces, split, level = {}, {}, {}
    for p in cells:
        for d in DIRS:
            if (p[0] + d[0], p[1] + d[1], p[2] + d[2]) in cells:
                continue
            ax = [i for i in range(3) if d[i]][0]
            ua, va = [i for i in range(3) if i != ax]
            fine = [None] * (FINE * FINE)
            for a in (0, 1):
                for b in (0, 1):
                    o3 = [0, 0, 0]
                    o3[ax] = 1 if d[ax] > 0 else 0
                    o3[ua], o3[va] = a, b
                    child = tuple(2 * p[i] + sh[i] + o3[i] for i in range(3))
                    cols = s.split.get((child, d))
                    for y in (0, 1):
                        for x in (0, 1):
                            if cols:
                                q = [cols[(2 * x + i) + FINE * (2 * y + j)] for i in (0, 1) for j in (0, 1)]
                                col = max(set(q), key=q.count)
                            else:
                                col = s.faces.get((child, d)) or s.cell_rgb.get(child) or cell_rgb.get(p) or (0.6, 0.6, 0.6)
                            fine[(2 * a + x) + FINE * (2 * b + y)] = col
            faces[(p, d)] = fine[0]
            if len(set(fine)) > 1:
                split[(p, d)] = fine
                level[(p, d)] = 1
    s.v, s.off = s.v * 2, p_off
    s.cells, s.cell_rgb, s.faces, s.split, s.level = cells, cell_rgb, faces, split, level
    n = s.write()
    _set_stack(ob, stack)
    return n


def ensure_size(ob, target_m, design_m):
    """Bring an object's cubes to the file's size: finer (each cube into 8) or bigger (each 8 back
    into one). Returns how many steps it took (0 when it already matched)."""
    v = ob.get("cubekit_voxel_m", design_m)
    steps = 0
    while v > target_m * 1.01 and v / 2 >= target_m * 0.99:
        subdivide(ob, v)
        v /= 2
        steps += 1
    while v < target_m * 0.99 and _stack(ob):
        merge(ob, v)
        v *= 2
        steps += 1
    return steps
