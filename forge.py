# Forge: cube models built in MIXED cube sizes, written as code. No Blender in here (forge_bl.py turns a model
# into Blender objects).
#
# Tefa, 2026-10-19: "use different cube sizes to really emphasize cracks and cuts but also little screws and corners
# and the design of these video game weapons, so they really have distinct shapes."
#
# Three sizes on one fixed grid, as in the add-on's small cubes (edit_small.py): the main cube (cube_size.VOXEL_M,
# 3.4 mm), the half cube (1.7 mm) and the quarter cube (0.85 mm). A main cell is either one whole cube or a 4 x 4 x 4
# grid of quarter cells; a half cube is 2 x 2 x 2 quarter cells sharing one colour and one id, so it reads as ONE cube.
# Every cube carries an id, and its brightness wobble (NOISE) comes from that id, so a big cube with a notch cut out
# still reads as the big cube it was.
#
# Units: positions are in MAIN cubes and may be fractions (0.25 steps). Axes as in every cubekit gun: x = rear ->
# muzzle, y = width (+ = the gun's LEFT side), z = up.
import math

FINE = 4                        # quarter cells per main cube along each axis
SIZES = (1.0, 0.5, 0.25)

SHADE = {(0, 0, 1): 1.12, (0, 0, -1): 0.55, (0, 1, 0): 0.88, (0, -1, 0): 0.88, (1, 0, 0): 0.74, (-1, 0, 0): 0.74}
NOISE = 0.06                    # +- share of brightness each cube wobbles by, from its id
SIDES = {'+x': (0, 1), '-x': (0, -1), '+y': (1, 1), '-y': (1, -1), '+z': (2, 1), '-z': (2, -1)}


def hash01(*v):
    h = 0x9E3779B9
    for n in v:
        h = (h ^ (int(n) & 0xFFFFFFFF)) * 0x01000193 & 0xFFFFFFFF
        h ^= h >> 15
        h = (h * 0x2C1B3C6D) & 0xFFFFFFFF
        h ^= h >> 12
    return (h & 0xFFFF) / 65535.0


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def mul(c, k):
    return tuple(max(0.0, min(255.0, v * k)) for v in c)


class Model:
    def __init__(self, name):
        self.name = name
        self.full = {}          # (x, y, z) main cell -> [rgb, id, part]
        self.fine = {}          # (x, y, z) main cell -> {(i, j, k): [rgb, id, part]}
        self.part = 'body'
        self.next_id = 1
        self.pivot = (0.0, 0.0, 0.0)
        self.notes = []
        self._qb = None         # cached quarter-cell bounds (grown as cubes are added)

    # ---------------------------------------------------------------- single cubes
    def new_id(self):
        self.next_id += 1
        return self.next_id

    def _split(self, cell):
        """Turn a whole cube into 64 quarter cells with its colour and id."""
        v = self.full.pop(cell)
        self.fine[cell] = {(i, j, k): list(v) for i in range(FINE) for j in range(FINE) for k in range(FINE)}

    def put(self, x, y, z, col, size=1.0, part=None, cid=None):
        """One cube of `size` with its low corner at (x, y, z), snapped to that size's grid."""
        part = part or self.part
        cid = cid or self.new_id()
        if callable(col):
            col = col(x + size / 2, y + size / 2, z + size / 2)
        if size >= 1.0:
            n = int(round(size))
            bx, by, bz = (math.floor(x / n) * n, math.floor(y / n) * n, math.floor(z / n) * n)
            for a in range(n):
                for b in range(n):
                    for c in range(n):
                        cell = (bx + a, by + b, bz + c)
                        self._grow(cell)
                        self.fine.pop(cell, None)
                        self.full[cell] = [col, cid, part]
            return
        q = int(round(size * FINE))
        qx, qy, qz = (math.floor(x * FINE / q) * q, math.floor(y * FINE / q) * q, math.floor(z * FINE / q) * q)
        for a in range(q):
            for b in range(q):
                for c in range(q):
                    self.put_q(qx + a, qy + b, qz + c, col, cid, part)

    def put_q(self, qx, qy, qz, col, cid=None, part=None):
        if callable(col):
            col = col((qx + 0.5) / FINE, (qy + 0.5) / FINE, (qz + 0.5) / FINE)
        cell = (qx // FINE, qy // FINE, qz // FINE)
        if cell in self.full:
            self._split(cell)
        self._grow(cell)
        sub = self.fine.setdefault(cell, {})
        sub[(qx % FINE, qy % FINE, qz % FINE)] = [col, cid or self.new_id(), part or self.part]

    def clear_q(self, qx, qy, qz):
        cell = (qx // FINE, qy // FINE, qz // FINE)
        if cell in self.full:
            self._split(cell)
        sub = self.fine.get(cell)
        if sub is not None:
            sub.pop((qx % FINE, qy % FINE, qz % FINE), None)
            if not sub:
                del self.fine[cell]

    def get_q(self, qx, qy, qz):
        cell = (qx // FINE, qy // FINE, qz // FINE)
        v = self.full.get(cell)
        if v is not None:
            return v
        sub = self.fine.get(cell)
        if sub is not None:
            return sub.get((qx % FINE, qy % FINE, qz % FINE))
        return None

    def at(self, x, y, z):
        """The cube under a point given in main units."""
        return self.get_q(math.floor(x * FINE), math.floor(y * FINE), math.floor(z * FINE))

    # ---------------------------------------------------------------- volumes
    def fill(self, inside, bounds, col, size=1.0, edge=None, part=None, carve=False, keep=False):
        """Fill (or with carve=True, empty) every cube of `size` inside a shape.

        inside(x, y, z) -> bool for a point in main units; bounds = (x0, x1, y0, y1, z0, z1).
        col: an rgb, or a function (x, y, z) -> rgb of the cube's centre.
        edge: None = a cube goes in when its centre is inside. 0.5 or 0.25 = cubes the surface passes through are
        split down to that size, so corners and curves step down in smaller cubes while the inside stays big.
        keep=True leaves cubes that are already there alone.
        """
        x0, x1, y0, y1, z0, z1 = bounds
        stop = edge or size

        def corners(cx, cy, cz, s):
            h = s / 2.0
            pts = [(cx + a * h * 0.98, cy + b * h * 0.98, cz + c * h * 0.98) for a in (-1, 1) for b in (-1, 1)
                   for c in (-1, 1)]
            return sum(1 for p in pts if inside(*p))

        def place(cx, cy, cz, s):
            h = s / 2.0
            if carve:
                if s >= 1.0:
                    cell = (math.floor(cx - h), math.floor(cy - h), math.floor(cz - h))
                    self.full.pop(cell, None)
                    self.fine.pop(cell, None)
                else:
                    q = int(round(s * FINE))
                    bq = (round((cx - h) * FINE), round((cy - h) * FINE), round((cz - h) * FINE))
                    for a in range(q):
                        for b in range(q):
                            for c in range(q):
                                self.clear_q(bq[0] + a, bq[1] + b, bq[2] + c)
                return
            if keep and self.at(cx, cy, cz) is not None:
                return
            rgb = col(cx, cy, cz) if callable(col) else col
            self.put(cx - h, cy - h, cz - h, rgb, s, part)

        def visit(cx, cy, cz, s):
            n = corners(cx, cy, cz, s)
            if n == 8:
                place(cx, cy, cz, s)
                return
            mid = inside(cx, cy, cz)
            if n == 0 and not mid:
                return
            if s <= stop + 1e-9:
                if mid:
                    place(cx, cy, cz, s)
                return
            hs = s / 2.0
            for a in (-0.5, 0.5):
                for b in (-0.5, 0.5):
                    for c in (-0.5, 0.5):
                        visit(cx + a * hs, cy + b * hs, cz + c * hs, hs)

        s = size
        xs = math.floor(x0 / s) * s
        while xs < x1:
            ys = math.floor(y0 / s) * s
            while ys < y1:
                zs = math.floor(z0 / s) * s
                while zs < z1:
                    if edge:
                        visit(xs + s / 2, ys + s / 2, zs + s / 2, s)
                    elif inside(xs + s / 2, ys + s / 2, zs + s / 2):
                        place(xs + s / 2, ys + s / 2, zs + s / 2, s)
                    zs += s
                ys += s
            xs += s

    def carve(self, inside, bounds, size=0.25, edge=None):
        self.fill(inside, bounds, None, size, edge, carve=True)

    # ---------------------------------------------------------------- shapes (all in main units)
    def box(self, x0, x1, y0, y1, z0, z1, col, size=1.0, edge=None, bevel=0.0, bevel_x=0.0, part=None, carve=False,
            keep=False):
        """A box [x0, x1) x [y0, y1) x [z0, z1). bevel cuts the four long (x) edges back, bevel_x the end edges."""
        def inside(x, y, z):
            if not (x0 <= x < x1 and y0 <= y < y1 and z0 <= z < z1):
                return False
            dy, dz, dx = min(y - y0, y1 - y), min(z - z0, z1 - z), min(x - x0, x1 - x)
            if bevel and dy + dz < bevel:
                return False
            if bevel_x and (dx + dy < bevel_x or dx + dz < bevel_x):
                return False
            return True
        self.fill(inside, (x0, x1, y0, y1, z0, z1), col, size, edge, part, carve, keep)

    def cbox(self, x0, x1, w, z0, z1, col, **kw):
        """A box centred on y = 0, w wide."""
        self.box(x0, x1, -w / 2.0, w / 2.0, z0, z1, col, **kw)

    def cyl(self, x0, x1, yc, zc, r, col, r1=None, axis='x', hollow=0.0, size=1.0, edge=0.5, part=None, carve=False,
            keep=False):
        """A round bar along `axis` from x0 to x1 (along that axis), radius r (tapering to r1), centred (yc, zc) in the
        other two axes. hollow = radius of a bore left empty."""
        r1 = r if r1 is None else r1
        rmax = max(r, r1)

        def inside(x, y, z):
            a, u, v = {'x': (x, y, z), 'y': (y, x, z), 'z': (z, x, y)}[axis]
            if not (x0 <= a < x1):
                return False
            t = (a - x0) / max(1e-9, x1 - x0)
            rr = r + (r1 - r) * t
            d2 = (u - yc) ** 2 + (v - zc) ** 2
            return d2 <= rr * rr and d2 >= hollow * hollow

        if axis == 'x':
            b = (x0, x1, yc - rmax, yc + rmax, zc - rmax, zc + rmax)
        elif axis == 'y':
            b = (yc - rmax, yc + rmax, x0, x1, zc - rmax, zc + rmax)
        else:
            b = (yc - rmax, yc + rmax, zc - rmax, zc + rmax, x0, x1)
        self.fill(inside, b, col, size, edge, part, carve, keep)

    def ball(self, xc, yc, zc, r, col, ry=None, rz=None, size=1.0, edge=0.5, part=None, carve=False):
        ry, rz = ry or r, rz or r

        def inside(x, y, z):
            return ((x - xc) / r) ** 2 + ((y - yc) / ry) ** 2 + ((z - zc) / rz) ** 2 <= 1.0
        self.fill(inside, (xc - r, xc + r, yc - ry, yc + ry, zc - rz, zc + rz), col, size, edge, part, carve)

    def prism(self, poly, y0, y1, col, size=1.0, edge=None, bevel=0.0, part=None, carve=False, keep=False):
        """A side outline [(x, z), ...] pushed out across y0..y1. bevel rounds its outline's edges where they meet
        the two flat sides (by distance to the outline)."""
        xs, zs = [p[0] for p in poly], [p[1] for p in poly]

        def in_poly(x, z):
            c = False
            j = len(poly) - 1
            for i in range(len(poly)):
                xi, zi = poly[i]
                xj, zj = poly[j]
                if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
                    c = not c
                j = i
            return c

        def edge_dist(x, z):
            best = 1e9
            j = len(poly) - 1
            for i in range(len(poly)):
                ax, az = poly[j]
                bx, bz = poly[i]
                vx, vz = bx - ax, bz - az
                L = vx * vx + vz * vz
                t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - ax) * vx + (z - az) * vz) / L))
                best = min(best, math.hypot(x - ax - t * vx, z - az - t * vz))
                j = i
            return best

        def inside(x, y, z):
            if not (y0 <= y < y1) or not in_poly(x, z):
                return False
            if bevel:
                if min(y - y0, y1 - y) + edge_dist(x, z) < bevel:
                    return False
            return True
        self.fill(inside, (min(xs), max(xs), y0, y1, min(zs), max(zs)), col, size, edge, part, carve, keep)

    def cprism(self, poly, w, col, **kw):
        self.prism(poly, -w / 2.0, w / 2.0, col, **kw)

    def recolour(self, inside, col, only=None):
        """Repaint cubes whose centre is inside, adding none. only: a set of rgbs to repaint (others kept)."""
        for cell, v in self.full.items():
            c = (cell[0] + 0.5, cell[1] + 0.5, cell[2] + 0.5)
            if inside(*c) and (only is None or v[0] in only):
                v[0] = col(*c) if callable(col) else col
        for cell, sub in self.fine.items():
            for (i, j, k), v in sub.items():
                c = (cell[0] + (i + 0.5) / FINE, cell[1] + (j + 0.5) / FINE, cell[2] + (k + 0.5) / FINE)
                if inside(*c) and (only is None or v[0] in only):
                    v[0] = col(*c) if callable(col) else col

    def mirror_y(self):
        """Copy everything on the +y side onto the -y side (the gun is symmetric unless told otherwise)."""
        for cell, v in list(self.full.items()):
            if cell[1] >= 0:
                self.full[(cell[0], -cell[1] - 1, cell[2])] = list(v)
        for cell, sub in list(self.fine.items()):
            if cell[1] >= 0:
                self.fine[(cell[0], -cell[1] - 1, cell[2])] = {(i, FINE - 1 - j, k): list(v)
                                                               for (i, j, k), v in sub.items()}

    # ---------------------------------------------------------------- surface work in quarter cubes
    def _qbounds(self):
        if self._qb is None:
            cells = list(self.full) + list(self.fine)
            lo = [min(c[n] for c in cells) * FINE for n in range(3)]
            hi = [(max(c[n] for c in cells) + 1) * FINE for n in range(3)]
            self._qb = (lo, hi)
        return self._qb

    def _grow(self, cell):
        if self._qb is not None:
            lo, hi = self._qb
            for n in range(3):
                lo[n] = min(lo[n], cell[n] * FINE)
                hi[n] = max(hi[n], (cell[n] + 1) * FINE)

    def surface_q(self, side, a, b):
        """The outermost quarter cell seen from `side` ('+y' looks at the gun's left face from outside) on the line
        through quarter coords (a, b) of the other two axes (in x, y, z order). None if the line misses."""
        ax, sign = SIDES[side]
        lo, hi = self._qbounds()
        rng = range(hi[ax] - 1, lo[ax] - 1, -1) if sign > 0 else range(lo[ax], hi[ax])
        others = [n for n in range(3) if n != ax]
        for t in rng:
            q = [0, 0, 0]
            q[ax] = t
            q[others[0]], q[others[1]] = a, b
            if self.get_q(*q) is not None:
                return tuple(q)
        return None

    def _line_q(self, pts):
        """Quarter-cube steps along a polyline given in main units [(a, b), ...]."""
        out = []
        for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
            n = max(1, int(max(abs(a1 - a0), abs(b1 - b0)) * FINE))
            for s in range(n + 1):
                t = s / n
                q = (math.floor((a0 + (a1 - a0) * t) * FINE), math.floor((b0 + (b1 - b0) * t) * FINE))
                if not out or out[-1] != q:
                    out.append(q)
        return out

    def groove(self, pts, side, depth=1, width=1, dark=0.45, col=None):
        """Cut a line into the surface seen from `side`, `depth` quarter cubes deep and `width` wide; the floor of
        the cut is painted darker (dark = brightness share) or `col`."""
        ax, sign = SIDES[side]
        for a, b in self._line_q(pts):
            for w in range(width):
                aa, bb = (a, b + w) if ax != 2 else (a, b + w)
                q = self.surface_q(side, aa, bb)
                if q is None:
                    continue
                for d in range(depth):
                    qq = list(q)
                    qq[ax] -= sign * d
                    self.clear_q(*qq)
                qq = list(q)
                qq[ax] -= sign * depth
                v = self.get_q(*qq)
                if v is not None:
                    self.put_q(*qq, col or mul(v[0], dark), v[1], v[2])

    def raised(self, pts, side, col, height=1, width=1):
        """Build a line of quarter cubes on top of the surface (welds, ribs, wires)."""
        ax, sign = SIDES[side]
        for a, b in self._line_q(pts):
            for w in range(width):
                q = self.surface_q(side, a, b + w)
                if q is None:
                    continue
                cid = self.new_id()
                for h in range(1, height + 1):
                    qq = list(q)
                    qq[ax] += sign * h
                    self.put_q(*qq, col, cid, self.get_q(*q)[2])

    def _stamp(self, side, a, b, cells, col, mode, part_from=True):
        ax, sign = SIDES[side]
        for (da, db), c in cells:
            q = self.surface_q(side, a + da, b + db)
            if q is None:
                continue
            v = self.get_q(*q)
            if mode == 'raise':
                qq = list(q)
                qq[ax] += sign
                self.put_q(*qq, c or col, None, v[2])
            elif mode == 'paint':
                self.put_q(*q, c or col, v[1], v[2])
            else:                                  # 'carve'
                self.clear_q(*q)
                qq = list(q)
                qq[ax] -= sign
                w = self.get_q(*qq)
                if w is not None:
                    self.put_q(*qq, c or col or mul(w[0], 0.45), w[1], w[2])

    def screw(self, a, b, side, col=(70, 72, 76), slot=(20, 20, 22), kind='slot'):
        """A raised screw head, 3 x 3 quarter cubes with its corners off and a slot (or a hex socket, or a plain
        rivet dome) at (a, b) main units on the face seen from `side`."""
        qa, qb = math.floor(a * FINE), math.floor(b * FINE)
        cells = []
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                if abs(i) == abs(j) == 1 and kind != 'hex':
                    continue
                c = None
                if kind == 'slot' and j == 0:
                    c = slot
                if kind == 'cross' and (i == 0 or j == 0) and not (i == j == 0):
                    c = slot
                if kind == 'hex' and i == j == 0:
                    c = slot
                cells.append(((i, j), c))
        self._stamp(side, qa, qb, cells, col, 'raise')
        if kind == 'rivet':
            ax, sign = SIDES[side]
            q = self.surface_q(side, qa, qb)
            if q:
                qq = list(q)
                qq[ax] += sign
                self.put_q(*qq, mul(col, 1.15), None, self.get_q(*q)[2])

    def bolt(self, a, b, side, col=(70, 72, 76)):
        """A bigger hex bolt head: a half-size cube ring with a quarter centre."""
        self.screw(a, b, side, col, mul(col, 0.6), 'hex')

    def decal(self, rows, a0, b_top, side, col, dot=1, mode='paint'):
        """A picture from text rows ('#' = on) placed with its top-left at (a0, b_top) main units; each '#' is
        dot x dot quarter cubes. mode: 'paint', 'raise' or 'carve'. On the +y side the rows are mirrored so it
        reads the right way round when looked at."""
        flip = side in ('+y', '-x')         # from these sides the gun's x runs right to left
        qa0, qb0 = math.floor(a0 * FINE), math.floor(b_top * FINE)
        cells = []
        for r, line in enumerate(rows):
            ln = line[::-1] if flip else line
            for c, ch in enumerate(ln):
                if ch == '.' or ch == ' ':
                    continue
                for i in range(dot):
                    for j in range(dot):
                        cells.append(((c * dot + i, -(r * dot + j)), None))
        self._stamp(side, qa0, qb0, cells, col, mode)

    def crack(self, a, b, side, length, seed, heading=None, depth=1, branch=0.25, dark=0.35):
        """A jagged crack walking across the surface from (a, b), in quarter steps, now and then splitting."""
        rnd = lambda *k: hash01(seed, *k)
        ang = heading if heading is not None else rnd(1) * math.tau
        stack = [(a, b, ang, length)]
        n = 0
        while stack and n < 400:
            a0, b0, ang0, L = stack.pop()
            pts = [(a0, b0)]
            x, z, h = a0, b0, ang0
            steps = max(2, int(L * 2))
            for s in range(steps):
                n += 1
                h += (rnd(n, 7) - 0.5) * 1.4
                x += math.cos(h) * 0.5
                z += math.sin(h) * 0.5
                pts.append((x, z))
                if rnd(n, 9) < branch / steps * 3 and L > 3:
                    stack.append((x, z, h + (0.9 if rnd(n, 11) > 0.5 else -0.9), L * 0.45))
            self.groove(pts, side, depth, 1, dark)

    def scratches(self, side, region, count, seed, lighten=1.45, length=(2.0, 7.0)):
        """Thin light scratches, one quarter cube deep, inside region (a0, a1, b0, b1) main units."""
        a0, a1, b0, b1 = region
        for i in range(count):
            r = lambda k: hash01(seed, i, k)
            a = a0 + (a1 - a0) * r(1)
            b = b0 + (b1 - b0) * r(2)
            L = length[0] + (length[1] - length[0]) * r(3)
            h = (r(4) - 0.5) * 0.9 + (math.pi if r(5) > 0.5 else 0.0)
            pts = [(a, b)]
            for s in range(int(L * 2)):
                h += (r(10 + s) - 0.5) * 0.35
                a += math.cos(h) * 0.5
                b += math.sin(h) * 0.5
                pts.append((a, b))
            self.paint_line(pts, side, lambda c: mul(mix(c, (180, 178, 170), 0.25), lighten))

    def paint_line(self, pts, side, fn):
        for a, b in self._line_q(pts):
            q = self.surface_q(side, a, b)
            if q is None:
                continue
            v = self.get_q(*q)
            self.put_q(*q, fn(v[0]), v[1], v[2])

    def wear_edges(self, amount=0.35, toward=(200, 196, 186), only=None):
        """Lighten whole cubes on outside edges (two open sides at right angles): handled, chipped edges."""
        out = []
        for (x, y, z), v in self.full.items():
            if only is not None and v[0] not in only:
                continue
            open_y = ((x, y + 1, z) not in self.full) + ((x, y - 1, z) not in self.full)
            open_z = ((x, y, z + 1) not in self.full) + ((x, y, z - 1) not in self.full)
            open_x = ((x + 1, y, z) not in self.full) + ((x - 1, y, z) not in self.full)
            if (open_y and open_z) or (open_x and (open_y or open_z)):
                if hash01(x, y, z, 77) < 0.75:
                    out.append(v)
        for v in out:
            v[0] = mix(v[0], toward, amount * (0.6 + 0.4 * hash01(v[1], 5)))

    def grime(self, amount, seed, scale=6.0, col=(30, 24, 18), only=None):
        """Dirt and rust in soft patches (value noise over the cubes)."""
        def noise(x, y, z):
            fx, fy, fz = x / scale, y / scale, z / scale
            ix, iy, iz = math.floor(fx), math.floor(fy), math.floor(fz)
            tx, ty, tz = fx - ix, fy - iy, fz - iz
            s = lambda t: t * t * (3 - 2 * t)
            tx, ty, tz = s(tx), s(ty), s(tz)
            acc = 0.0
            for dx in (0, 1):
                for dy in (0, 1):
                    for dz in (0, 1):
                        w = (tx if dx else 1 - tx) * (ty if dy else 1 - ty) * (tz if dz else 1 - tz)
                        acc += w * hash01(ix + dx, iy + dy, iz + dz, seed)
            return acc
        for (x, y, z), v in self.full.items():
            if only is not None and v[0] not in only:
                continue
            n = noise(x, y, z)
            if n > 1.0 - amount:
                v[0] = mix(v[0], col, min(0.85, (n - (1.0 - amount)) / amount * 1.2))

    # ---------------------------------------------------------------- output
    def counts(self):
        sizes = {1.0: len(self.full), 0.5: 0, 0.25: 0}
        for sub in self.fine.values():
            ids = {}
            for v in sub.values():
                ids[v[1]] = ids.get(v[1], 0) + 1
            for n in ids.values():
                if n >= 8:
                    sizes[0.5] += n // 8
                    sizes[0.25] += n % 8
                else:
                    sizes[0.25] += n
        return sizes

    @staticmethod
    def _layer_full(sub, d, part):
        """True when the quarter cells of `sub` touching a whole cube on its -d side are all solid, same part."""
        ax = [n for n in range(3) if d[n] != 0][0]
        u, w = [n for n in range(3) if n != ax]
        layer = 0 if d[ax] > 0 else FINE - 1
        for i in range(FINE):
            for j in range(FINE):
                idx = [0, 0, 0]
                idx[ax], idx[u], idx[w] = layer, i, j
                s = sub.get(tuple(idx))
                if s is None or s[2] != part:
                    return False
        return True

    def faces(self):
        """Every outside face: [(part, corners [4 x (x, y, z) main units], direction, rgb)]."""
        out = []
        dirs = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

        def quad(o, d, s):
            ax = [n for n in range(3) if d[n] != 0][0]
            u, w = [n for n in range(3) if n != ax]
            base = list(o)
            if d[ax] > 0:
                base[ax] += s
            pts = []
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                p = list(base)
                p[u] += a * s
                p[w] += b * s
                pts.append(tuple(p))
            return pts

        def tint(v, d):
            k = SHADE[d] * (1.0 + NOISE * (hash01(v[1], 3) - 0.5) * 2.0)
            return mul(v[0], k)

        for cell, v in self.full.items():
            for d in dirs:
                nb = (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2])
                nv = self.full.get(nb)
                if nv is not None and nv[2] == v[2]:
                    continue
                sub = self.fine.get(nb)
                if sub is not None and self._layer_full(sub, d, v[2]):
                    continue
                out.append((v[2], quad(cell, d, 1.0), d, tint(v, d)))
        f = 1.0 / FINE
        groups = {}                     # (direction, plane, part, rgb) -> {(u, w)} quarter faces, merged below
        for cell, sub in self.fine.items():
            for (i, j, k), v in sub.items():
                q = (cell[0] * FINE + i, cell[1] * FINE + j, cell[2] * FINE + k)
                for d in dirs:
                    nv = self.get_q(q[0] + d[0], q[1] + d[1], q[2] + d[2])
                    if nv is not None and nv[2] == v[2]:
                        continue
                    ax = 0 if d[0] else (1 if d[1] else 2)
                    u, w = [n for n in range(3) if n != ax]
                    rgb = tuple(int(round(c)) for c in tint(v, d))
                    groups.setdefault((d, q[ax], v[2], rgb), set()).add((q[u], q[w]))
        for (d, plane, part, rgb), cells in groups.items():
            ax = 0 if d[0] else (1 if d[1] else 2)
            u, w = [n for n in range(3) if n != ax]
            for a, b in sorted(cells):
                if (a, b) not in cells:
                    continue
                wa = 1
                while (a + wa, b) in cells:
                    wa += 1
                hb = 1
                while all((a + t, b + hb) in cells for t in range(wa)):
                    hb += 1
                for t in range(wa):
                    for s2 in range(hb):
                        cells.discard((a + t, b + s2))
                base = [0, 0, 0]
                base[ax] = plane + (1 if d[ax] > 0 else 0)
                pts = []
                for ea, eb in ((0, 0), (1, 0), (1, 1), (0, 1)):
                    p = list(base)
                    p[u] = a + ea * wa
                    p[w] = b + eb * hb
                    pts.append((p[0] * f, p[1] * f, p[2] * f))
                out.append((part, pts, d, rgb))
        return out
