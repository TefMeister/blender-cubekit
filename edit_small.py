# Smaller cubes inside one model (asked for by Tefa, 2026-10-03; built 2026-10-08).
#
# A model keeps its file's cube size as its main grid. Any one of those cubes can be made smaller:
# it then holds a 4 x 4 x 4 grid of quarter-size cubes, each solid or air, and any of its eight
# octants can be shown as ONE half-size cube instead of 8 quarter ones (the octant is then full).
# So a 3.4 mm cube can become eight 1.7 mm cubes, and each of those eight 0.85 mm cubes, and back.
# Everything sits on one fixed grid: a half-size cube always covers the same 8 quarter ones, and a
# full cube the same 8 half ones (Tefa chose the fixed grid, 2026-10-03). Shipped in add-on 0.18.0;
# the bigger sizes (whole cubes shown as one) are still to come: docs/ROADMAP.md.
#
# Going back to bigger uses the same rule as before (edit.MERGE_KEEP): a bigger cube stays when at
# least half of its 8 smaller cubes are there, and the missing ones are filled; otherwise it goes.
#
# Positions: a "fine" position is a whole number in quarter-cube units, the same units the 4 x 4
# split sides already use, so fine-square colours on a side map onto the quarter cubes behind it.
from edit import DIRS, FINE, MERGE_KEEP, UNPAINTED

SUB, SUBSIZE, PART = "cubekit_sub", "cubekit_subsize", "cubekit_part"
MIN_MM = 0.85                 # no cube smaller than this (the smallest size button)
KEY_TAG = "sub"               # a small cube's side key: (cell, dir, "sub", (owner index, size))


class FineCell:
    """The small cubes inside one main-grid cube."""

    def __init__(self):
        self.subs = {}        # index (0..63) -> rgb of that quarter cube, for every solid one
        self.half = set()     # octants (0..7) shown as one half-size cube; always full


def si(i, j, k):
    return i + FINE * j + FINE * FINE * k


def local(index):
    return (index % FINE, (index // FINE) % FINE, index // (FINE * FINE))


def octant(index):
    i, j, k = local(index)
    return i // 2 + 2 * (j // 2) + 4 * (k // 2)


def octant_subs(o):
    a, b, c = o % 2, (o // 2) % 2, o // 4
    return [si(2 * a + x, 2 * b + y, 2 * c + z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]


def owner_of(fc, index):
    """(owner index, size) of the small cube that holds this quarter position."""
    o = octant(index)
    if o in fc.half:
        return octant_subs(o)[0], 2
    return index, 1


def units(fc):
    """Every small cube in a cell, as (owner index, size)."""
    out = [(octant_subs(o)[0], 2) for o in sorted(fc.half)]
    out += [(i, 1) for i in sorted(fc.subs) if octant(i) not in fc.half]
    return out


def unit_subs(owner, size):
    if size == 1:
        return [owner]
    return octant_subs(octant(owner))


def is_sub(key):
    return len(key) == 4 and key[2] == KEY_TAG


def plain_keys(keys):
    return [k for k in keys if not is_sub(k)]


def sub_keys(keys):
    return [k for k in keys if is_sub(k)]


def fpos(cell, index):
    """Global fine position of a quarter cube."""
    i, j, k = local(index)
    return (FINE * cell[0] + i, FINE * cell[1] + j, FINE * cell[2] + k)


def split_fpos(p):
    """(cell, index) of a global fine position."""
    cell = tuple(c // FINE for c in p)
    return cell, si(*(p[a] - FINE * cell[a] for a in range(3)))


def occupied(s, p):
    cell, index = split_fpos(p)
    if cell in s.cells:
        return True
    fc = s.fine.get(cell)
    return bool(fc) and index in fc.subs


def allowed_levels(v_m):
    """How many halvings below the file's own cube size are allowed (0, 1 or 2)."""
    n = 0
    while n < 2 and v_m / 2 ** (n + 1) * 1000 >= MIN_MM - 1e-6:
        n += 1
    return n


# ---- keeping it on the object ----

def load(s):
    ob = s.ob
    s.fine, s.sfaces = {}, {}       # sfaces: (cell, index, dir) -> rgb of one quarter cube's side
    s.hidden = {}                   # (cell, dir) -> 16 colours of a whole cube's side facing small cubes
    s.restored = set()              # the sides put back from "cubekit_hidden" on this load
    hid = list(ob.get("cubekit_hidden", ()))
    for n in range(0, len(hid), 6 + 3 * FINE * FINE):
        key = (tuple(int(x) for x in hid[n:n + 3]), tuple(int(x) for x in hid[n + 3:n + 6]))
        cols = [tuple(hid[n + 6 + 3 * i:n + 9 + 3 * i]) for i in range(FINE * FINE)]
        s.split[key] = cols
        s.level[key] = 2
        s.restored.add(key)
    flat = list(ob.get("cubekit_fine", ()))
    rgb = list(ob.get("cubekit_fine_rgb", ()))
    ri = 0
    for n in range(0, len(flat), 8):
        cell = tuple(flat[n:n + 3])
        words = flat[n + 3:n + 7]
        fc = FineCell()
        for w in range(4):
            for b in range(16):
                if words[w] >> b & 1:
                    c = tuple(rgb[ri:ri + 3])
                    ri += 3
                    fc.subs[16 * w + b] = c if c and c[0] >= 0 else None
        fc.half = {o for o in range(8) if flat[n + 7] >> o & 1}
        s.fine[cell] = fc


def save(s):
    flat, rgb = [], []
    for cell, fc in s.fine.items():
        words = [0, 0, 0, 0]
        for i in sorted(fc.subs):
            words[i // 16] |= 1 << (i % 16)
        flat += list(cell) + words + [sum(1 << o for o in fc.half)]
        for i in sorted(fc.subs):
            c = fc.subs[i]
            rgb += list(c) if c else [-1.0, -1.0, -1.0]
    s.ob["cubekit_fine"] = flat
    s.ob["cubekit_fine_rgb"] = rgb
    hid = []
    for (cell, d), cols in s.hidden.items():
        hid += list(cell) + list(d)
        for c in cols:
            hid += list(c)
    s.ob["cubekit_hidden"] = hid


def tidy(s):
    """Drop emptied cells, and half octants that lost a quarter."""
    for cell in [c for c, fc in s.fine.items() if not fc.subs]:
        del s.fine[cell]
    for fc in s.fine.values():
        fc.half = {o for o in fc.half if all(i in fc.subs for i in octant_subs(o))}


def sub_colour(s, cell, index, d):
    fc = s.fine.get(cell)
    return (s.sfaces.get((cell, index, d)) or (fc.subs.get(index) if fc else None)
            or s.cell_rgb.get(cell) or UNPAINTED)


# ---- reading the mesh back ----

def _axes(d):
    ax = [i for i in range(3) if d[i]][0]
    ua, va = [i for i in range(3) if i != ax]
    return ax, ua, va


def squares_of_poly(s, me, poly, d):
    """The quarter positions just inside a small cube's side quad (one, or 2 x 2)."""
    ax, ua, va = _axes(d)
    gs = [[FINE * x for x in s.grid(me.vertices[i].co)] for i in poly.vertices]
    plane = round(gs[0][ax])
    u0, u1 = round(min(g[ua] for g in gs)), round(max(g[ua] for g in gs))
    v0, v1 = round(min(g[va] for g in gs)), round(max(g[va] for g in gs))
    out = []
    for u in range(u0, u1):
        for v in range(v0, v1):
            p = [0, 0, 0]
            p[ax] = plane - 1 if d[ax] > 0 else plane
            p[ua], p[va] = u, v
            out.append(tuple(p))
    return out


def read_poly(s, me, poly, d, rgb):
    for p in squares_of_poly(s, me, poly, d):
        cell, index = split_fpos(p)
        s.sfaces[(cell, index, d)] = rgb


def key_of(s, me, poly, d):
    p = squares_of_poly(s, me, poly, d)[0]
    cell, index = split_fpos(p)
    fc = s.fine.get(cell)
    if fc is None:
        return (cell, d, KEY_TAG, (index, 1))
    return (cell, d, KEY_TAG, owner_of(fc, index))


# ---- drawing it ----

def emit(s, quad):
    """Hand every visible small-cube side to quad(corners, d, rgb, seed, key, attrs, owner)."""
    for cell, fc in s.fine.items():
        for owner, size in units(fc):
            o = fpos(cell, owner)
            for d in DIRS:
                ax, ua, va = _axes(d)
                sq = []
                for a in range(size):
                    for b in range(size):
                        q = list(o)
                        q[ax] += size - 1 if d[ax] > 0 else 0
                        q[ua] += a
                        q[va] += b
                        q = tuple(q)
                        n = (q[0] + d[0], q[1] + d[1], q[2] + d[2])
                        if not occupied(s, n):
                            qc, qi = split_fpos(q)
                            sq.append((a, b, sub_colour(s, qc, qi, d)))
                if not sq:
                    continue
                key = (cell, d, KEY_TAG, (owner, size))
                attrs = {SUB: owner + 1, SUBSIZE: size}
                plane = o[ax] + (size if d[ax] > 0 else 0)
                cols = [c for _, _, c in sq]
                if len(sq) == size * size and len(set(cols)) == 1:
                    sq = [(0, 0, cols[0])]
                    step = size
                else:
                    step = 1
                for a, b, rgb in sq:
                    corners = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        p = [0, 0, 0]
                        p[ax] = plane
                        p[ua] = o[ua] + a + du * step
                        p[va] = o[va] + b + dv * step
                        corners.append(tuple(p))
                    quad(corners, d, rgb, o, key, attrs, ("s", cell, owner))


def hidden_square(s, cell, d, fu, fv):
    """A main cube's side facing a cell of small cubes: is fine square (fu, fv) covered by one?"""
    nb = (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2])
    fc = s.fine.get(nb)
    if fc is None:
        return False
    ax, ua, va = _axes(d)
    p = [0, 0, 0]
    p[ax] = 0 if d[ax] > 0 else FINE - 1
    p[ua], p[va] = fu, fv
    return si(*p) in fc.subs


# ---- changing sizes ----

def _majority(cols, default):
    cols = [c for c in cols if c]
    return max(set(cols), key=cols.count) if cols else default


def make_small(s, cell, half):
    """A main cube becomes 64 quarter cubes (or 8 half ones), keeping every colour on its sides."""
    rgb = s.cell_rgb.get(cell) or UNPAINTED
    fc = FineCell()
    for i in range(FINE ** 3):
        fc.subs[i] = rgb
    if half:
        fc.half = set(range(8))
    for d in DIRS:
        ax, ua, va = _axes(d)
        cols = s.split.get((cell, d))
        face = s.faces.get((cell, d))
        for fu in range(FINE):
            for fv in range(FINE):
                p = [0, 0, 0]
                p[ax] = FINE - 1 if d[ax] > 0 else 0
                p[ua], p[va] = fu, fv
                c = cols[fu + FINE * fv] if cols else face
                if c and c != rgb:
                    s.sfaces[(cell, si(*p), d)] = c
    s.remove(cell)
    s.fine[cell] = fc


def join_octant(s, cell, o):
    """Eight quarter cubes -> one half cube, if at least MERGE_KEEP of them are there; else they go."""
    fc = s.fine[cell]
    there = [i for i in octant_subs(o) if i in fc.subs]
    if len(there) >= MERGE_KEEP:
        rgb = _majority([fc.subs[i] for i in there], s.cell_rgb.get(cell))
        for i in octant_subs(o):
            fc.subs.setdefault(i, rgb)
        fc.half.add(o)
        return True
    for i in there:
        del fc.subs[i]
    return False


def join_cell(s, cell):
    """The small cubes of a cell -> one main cube, if at least MERGE_KEEP of its 8 octants are
    (at least half) there; else the cell becomes empty. Side colours are kept as a 4 x 4 split."""
    fc = s.fine.pop(cell)
    full = [o for o in range(8) if sum(i in fc.subs for i in octant_subs(o)) >= MERGE_KEEP]
    if len(full) < MERGE_KEEP:
        return False
    rgb = _majority(list(fc.subs.values()), s.cell_rgb.get(cell) or UNPAINTED)
    s.add(cell, rgb)
    for d in DIRS:
        ax, ua, va = _axes(d)
        cols = []
        for fv in range(FINE):
            for fu in range(FINE):
                p = [0, 0, 0]
                p[ax] = FINE - 1 if d[ax] > 0 else 0
                p[ua], p[va] = fu, fv
                index = si(*p)
                c = s.sfaces.get((cell, index, d)) or fc.subs.get(index) or rgb
                cols.append(c)
        # cols is in fv-major order: fu + FINE * fv, as split sides store it
        if len(set(cols)) == 1:
            s.faces[(cell, d)] = cols[0]
        else:
            s.split[(cell, d)] = cols
            quarters_flat = all(len({cols[(qu + x) + FINE * (qv + y)] for x in (0, 1) for y in (0, 1)}) == 1
                                for qu in (0, 2) for qv in (0, 2))
            s.level[(cell, d)] = 1 if quarters_flat else 2
            s.faces[(cell, d)] = _majority(cols, rgb)
    for k in [k for k in s.sfaces if k[0] == cell]:
        del s.sfaces[k]
    return True


def resize(s, keys, rel):
    """The size buttons on the picked cubes. rel: 0 = the file's own size, -1 = half, -2 = quarter.
    Returns (cubes changed, keys to leave picked)."""
    changed = 0
    touched = set()
    for k in plain_keys(keys):
        cell = k[0]
        if rel < 0 and cell in s.cells:
            make_small(s, cell, half=(rel == -1))
            touched.add(cell)
            changed += 1
    seen = set()
    for cell, _d, _t, (owner, size) in sub_keys(keys):
        if (cell, owner, size) in seen or cell not in s.fine:
            continue
        seen.add((cell, owner, size))
        fc = s.fine[cell]
        if rel == 0:
            continue                       # whole cells are joined below, once each
        if rel == -2 and size == 2:
            fc.half.discard(octant(owner))
        elif rel == -1 and size == 1:
            join_octant(s, cell, octant(owner))
        else:
            continue
        touched.add(cell)
        changed += 1
    if rel == 0:
        for cell in {k[0] for k in sub_keys(keys)}:
            if cell in s.fine:
                join_cell(s, cell)
                touched.add(cell)
                changed += 1
    tidy(s)
    pick = []
    for cell in touched:
        if cell in s.cells:
            pick += [(cell, d) for d in DIRS]
        elif cell in s.fine:
            pick += [(cell, d, KEY_TAG, u) for u in units(s.fine[cell]) for d in DIRS]
    return changed, pick


# ---- building, digging and painting with small cubes ----

def _place_unit(s, o, size, rgb):
    for x in range(size):
        for y in range(size):
            for z in range(size):
                p = (o[0] + x, o[1] + y, o[2] + z)
                cell, index = split_fpos(p)
                if cell in s.cells:
                    continue
                fc = s.fine.setdefault(cell, FineCell())
                fc.subs[index] = rgb
                for d in DIRS:
                    s.sfaces.pop((cell, index, d), None)
    if size == 2:
        cell, index = split_fpos(o)
        if cell in s.fine:
            s.fine[cell].half.add(octant(index))


def _take_unit(s, cell, owner, size):
    fc = s.fine.get(cell)
    if not fc:
        return
    for i in unit_subs(owner, size):
        fc.subs.pop(i, None)
        for d in DIRS:
            s.sfaces.pop((cell, i, d), None)
    if size == 2:
        fc.half.discard(octant(owner))


def grow(s, keys, count, colour):
    """E on small cubes' sides: a small cube of the same size outside each one."""
    new = []
    for cell, d, _t, (owner, size) in sub_keys(keys):
        rgb = colour or sub_colour(s, cell, owner, d)
        o = fpos(cell, owner)
        for _ in range(count):
            o = (o[0] + d[0] * size, o[1] + d[1] * size, o[2] + d[2] * size)
            _place_unit(s, o, size, rgb)
        c, i = split_fpos(o)
        if c in s.fine:
            new.append((c, d, KEY_TAG, owner_of(s.fine[c], i)))
    return new


def shrink(s, keys, count):
    """Q on small cubes' sides: the small cube goes; the one behind it is picked next."""
    new = []
    for cell, d, _t, (owner, size) in sub_keys(keys):
        o = fpos(cell, owner)
        c, i = cell, owner
        for _ in range(count):
            fc = s.fine.get(c)
            if not fc or i not in fc.subs:
                break
            own, sz = owner_of(fc, i)
            _take_unit(s, c, own, sz)
            o = (o[0] - d[0] * size, o[1] - d[1] * size, o[2] - d[2] * size)
            c, i = split_fpos(o)
        fc = s.fine.get(c)
        if fc and i in fc.subs:
            new.append((c, d, KEY_TAG, owner_of(fc, i)))
    tidy(s)
    return new


def remove(s, keys):
    """Q with whole cubes picked: the picked small cubes go."""
    for cell, _d, _t, (owner, size) in sub_keys(keys):
        _take_unit(s, cell, owner, size)
    tidy(s)


def paint(s, keys, rgb, whole):
    for cell, d, _t, (owner, size) in sub_keys(keys):
        fc = s.fine.get(cell)
        if not fc:
            continue
        for i in unit_subs(owner, size):
            if whole:
                fc.subs[i] = rgb
                for dd in DIRS:
                    s.sfaces.pop((cell, i, dd), None)
            else:
                s.sfaces[(cell, i, d)] = rgb
