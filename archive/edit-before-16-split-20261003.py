# Cube-level editing of a pick-mode mesh: add a cube, remove a cube, recolour a side. The add-on's
# E, Q and colour palette run through here (asked for by Tefa, 2026-10-03).
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


class Solid:
    """The cubes of one object: which cells are solid, and the colour of every cube and face."""

    def __init__(self, ob, voxel_m):
        self.ob, self.v = ob, voxel_m
        me = ob.data
        c0 = me.vertices[0].co
        self.off = [c0[i] / voxel_m - math.floor(c0[i] / voxel_m + 1e-6) for i in range(3)]
        self.faces = {}            # (cell, dir) -> base rgb (0-1) of that face
        self.split = {}            # (cell, dir) -> [rgb] * 4: a side split into 2 x 2 squares
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

    # ---- reading ----
    def grid(self, p):
        return [p[i] / self.v - self.off[i] for i in range(3)]

    def _read_mesh(self, me):
        base = me.color_attributes.get(BASE)
        px = None if base else _atlas_pixels(self.ob)
        uvl = me.uv_layers.active if px else None
        for poly in me.polygons:
            if len(poly.vertices) != 4:
                continue
            d = _dir_of(poly.normal)
            centre = poly.center - Vector(d) * (0.5 * self.v)
            cell = tuple(math.floor(c) for c in self.grid(centre))
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
            if poly.area < 0.5 * self.v * self.v:            # one of a split side's four squares
                sub = self._sub_of(poly.center, cell, d)
                self.split.setdefault((cell, d), [None] * 4)[sub] = rgb
                self.faces.setdefault((cell, d), rgb)
            else:
                self.faces[(cell, d)] = rgb
            self.cells.add(cell)
        for key, cols in self.split.items():               # a square that went missing: its side's colour
            for i in range(4):
                if cols[i] is None:
                    cols[i] = self.faces.get(key, (0.6, 0.6, 0.6))

    def _sub_of(self, centre, cell, d):
        """Which of a side's four squares a point is in: 0..3, (u half) + 2 * (v half)."""
        ax = [i for i in range(3) if d[i]][0]
        ua, va = [i for i in range(3) if i != ax]
        g = self.grid(centre)
        return (1 if g[ua] - cell[ua] > 0.5 else 0) + (2 if g[va] - cell[va] > 0.5 else 0)

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
    def add(self, cell, rgb):
        self.cells.add(cell)
        self.cell_rgb[cell] = rgb
        for d in DIRS:
            self.faces.pop((cell, d), None)
            self.split.pop((cell, d), None)

    def remove(self, cell):
        self.cells.discard(cell)
        for d in DIRS:
            self.faces.pop((cell, d), None)
            self.split.pop((cell, d), None)

    def paint_face(self, cell, d, rgb, sub=None):
        if sub is not None and (cell, d) in self.split:
            self.split[(cell, d)][sub] = rgb
        else:
            self.faces[(cell, d)] = rgb
            self.split.pop((cell, d), None)

    def paint_cube(self, cell, rgb):
        self.cell_rgb[cell] = rgb
        for d in DIRS:
            self.faces.pop((cell, d), None)
            self.split.pop((cell, d), None)

    def split_face(self, cell, d):
        if (cell, d) not in self.split:
            self.split[(cell, d)] = [self.colour_of(cell, d)] * 4

    def exposed(self, cell):
        return [d for d in DIRS if (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2]) not in self.cells]

    def colour_of(self, cell, d):
        return self.faces.get((cell, d)) or self.cell_rgb.get(cell) or (0.6, 0.6, 0.6)

    # ---- writing ----
    def write(self, select=()):
        """Rebuild the object's mesh from the cube list: one quad per exposed face, each cube with
        its own corners. select: (cell, dir) keys to leave selected."""
        ob, v = self.ob, self.v
        verts, vidx, polys, cols_b, cols_v, keys = [], {}, [], [], [], []
        off = self.off
        for cell in self.cells:
            for d in DIRS:
                nb = (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2])
                if nb in self.cells:
                    continue
                ax = [i for i in range(3) if d[i]][0]
                ua, va = [i for i in range(3) if i != ax]
                plane2 = 2 * (cell[ax] + (1 if d[ax] > 0 else 0))     # corners in half-cube units
                base = self.colour_of(cell, d)
                self.faces.setdefault((cell, d), base)
                cols = self.split.get((cell, d))
                squares = ([(0, 0, 0, cols[0]), (1, 0, 1, cols[1]), (0, 1, 2, cols[2]), (1, 1, 3, cols[3])]
                           if cols else [(None, None, None, base)])
                k = SHADE[d] * (1.0 + (hash01(*cell, 9) - 0.5) * 2 * NOISE)
                for su, sv, sub, rgb in squares:
                    size = 2 if su is None else 1
                    u0 = 2 * cell[ua] + (0 if su is None else su)
                    v0 = 2 * cell[va] + (0 if sv is None else sv)
                    corners = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        p = [0, 0, 0]
                        p[ax] = plane2
                        p[ua] = u0 + du * size
                        p[va] = v0 + dv * size
                        corners.append(tuple(p))
                    pts = [Vector(((p[0] / 2 + off[0]) * v, (p[1] / 2 + off[1]) * v, (p[2] / 2 + off[2]) * v))
                           for p in corners]
                    if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(Vector(d)) < 0:
                        corners.reverse()
                        pts.reverse()
                    ids = []
                    for kk, p in zip(corners, pts):
                        key = (cell, kk)
                        if key not in vidx:
                            vidx[key] = len(verts)
                            verts.append(p)
                        ids.append(vidx[key])
                    polys.append(ids)
                    view = tuple(min(1.0, c * k) for c in rgb)
                    cols_b.append(tuple(to_linear(c) for c in rgb))
                    cols_v.append(tuple(to_linear(c) for c in view))
                    keys.append((cell, d) if sub is None else (cell, d, sub))
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
        # Edit mode reads the selection from the corners, so corners, edges and faces are all set:
        # only the given faces (none by default) come up picked.
        sel = set(select)
        whole = {k[:2] for k in sel if len(k) == 2}       # a whole side picked: all its squares too
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
        return len(polys)

    def key_of(self, poly):
        """(cell, dir), or (cell, dir, square) for a split side's square, of one mesh face."""
        d = _dir_of(poly.normal)
        centre = poly.center - Vector(d) * (0.5 * self.v)
        cell = tuple(math.floor(c) for c in self.grid(centre))
        if poly.area < 0.5 * self.v * self.v:
            return (cell, d, self._sub_of(poly.center, cell, d))
        return (cell, d)

    def selected_keys(self):
        """(cell, dir) of every selected face, or (cell, dir, square) for a split side's square."""
        me = self.ob.data
        out = []
        for poly in me.polygons:
            if poly.select and len(poly.vertices) == 4:
                d = _dir_of(poly.normal)
                centre = poly.center - Vector(d) * (0.5 * self.v)
                cell = tuple(math.floor(c) for c in self.grid(centre))
                if poly.area < 0.5 * self.v * self.v:
                    out.append((cell, d, self._sub_of(poly.center, cell, d)))
                else:
                    out.append((cell, d))
        return out


def has_colours(ob):
    return ob.type == 'MESH' and VIEW in ob.data.color_attributes


def convert(ob, voxel_m):
    """Atlas-textured pick mesh -> colour-attribute pick mesh with the full cube list. Returns faces."""
    s = Solid(ob, voxel_m)
    return s.write()


def grow(ob, voxel_m, keys, count=1):
    """E: for every selected face, put a cube outside it, in the face's colour; the new cube's outer
    face becomes the selected one, so E E E builds a row. Returns the new selection keys."""
    s = Solid(ob, voxel_m)
    new = []
    for cell, d in {k[:2] for k in keys}:
        rgb = s.colour_of(cell, d)
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
    """C: every picked side (or every outside side of a picked cube) becomes four smaller squares
    that can be picked and painted on their own, for cracks, wear and fine lines. The cube keeps
    its size: this is detail on the surface, so the one-cube-size rule still holds."""
    s = Solid(ob, voxel_m)
    picked = []
    for k in keys:
        cell = k[0]
        for d in (s.exposed(cell) if whole_cubes else [k[1]]):
            s.split_face(cell, d)
            picked += [(cell, d, i) for i in range(4)]
    s.write(picked)
    return len(picked) // 4
