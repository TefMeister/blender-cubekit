# Moving cubes, lifting cubes out into a part, and copy / paste.
# Moved out of edit.py unchanged on 2026-10-08 (file size rule); edit.py re-exports everything here.
from edit import DIRS, Solid

# ---- moving cubes, and lifting cubes out into a part of their own (Tefa, 2026-10-03) ----

def _carry(s, cells):
    """Everything painted on these cubes, so they can be put down somewhere else."""
    out = {}
    for c in cells:
        out[c] = (s.cell_rgb.get(c),
                  {d: (s.faces.get((c, d)), s.split.get((c, d)), s.level.get((c, d))) for d in DIRS})
    return out


def _put(s, cell, carried):
    rgb, sides = carried
    s.cells.add(cell)
    s.fine.pop(cell, None)
    if rgb:
        s.cell_rgb[cell] = rgb
    for d, (f, sp, lv) in sides.items():
        s._forget((cell, d))
        if f is not None:
            s.faces[(cell, d)] = f
        if sp is not None:
            s.split[(cell, d)] = list(sp)
        if lv is not None:
            s.level[(cell, d)] = lv


def move_cubes(ob, voxel_m, keys, delta):
    """Move the picked cubes (a picked side counts as its cube) by delta, in whole cubes, with their
    colours. They land on top of whatever is there; the spots they leave become empty. The moved
    cubes stay picked, so the next press moves them again. Returns how many moved."""
    s = Solid(ob, voxel_m)
    cells = {k[0] for k in keys if k[0] in s.cells}
    carried = _carry(s, cells)
    for c in cells:
        s.remove(c)
    moved = []
    for c, stuff in carried.items():
        n = (c[0] + delta[0], c[1] + delta[1], c[2] + delta[2])
        _put(s, n, stuff)
        moved.append(n)
    s.write([(n, d) for n in moved for d in DIRS])
    return len(moved)


def _shift_solid(s, g):
    """Move every cube of a Solid by -g (whole cubes), with everything painted on it."""
    m = lambda c: (c[0] - g[0], c[1] - g[1], c[2] - g[2])
    s.cells = {m(c) for c in s.cells}
    s.cell_rgb = {m(c): v for c, v in s.cell_rgb.items()}
    s.faces = {(m(c), d): v for (c, d), v in s.faces.items()}
    s.split = {(m(c), d): v for (c, d), v in s.split.items()}
    s.level = {(m(c), d): v for (c, d), v in s.level.items()}
    s.fine = {m(c): v for c, v in s.fine.items()}
    s.sfaces = {(m(c), i, d): v for (c, i, d), v in s.sfaces.items()}


def split_part_plan(ob, voxel_m, keys):
    """For lifting the picked cubes out into a part: (picked cells, the joint, in whole-cube grid
    units). The joint is where the picked cubes touch the rest, snapped to the nearest cube corner,
    so the part turns at that point (a finger at its knuckle)."""
    s = Solid(ob, voxel_m)
    picked = {k[0] for k in keys if k[0] in s.cells}
    rest = s.cells - picked
    contacts = []
    for c in picked:
        for d in DIRS:
            if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) in rest:
                contacts.append([c[i] + 0.5 + 0.5 * d[i] for i in range(3)])
    pts = contacts or [[c[i] + 0.5 for i in range(3)] for c in picked]
    joint = [round(sum(p[i] for p in pts) / len(pts)) for i in range(3)] if pts else [0, 0, 0]
    return picked, rest, joint, s.off, s.v


def keep_only(ob, voxel_m, cells, shift=(0, 0, 0)):
    """Keep only these cubes in the object (moved by -shift whole cubes), with their colours."""
    s = Solid(ob, voxel_m)
    for c in [c for c in s.cells if c not in cells]:
        s.remove(c)
    for c in [c for c in s.fine if c not in cells]:
        del s.fine[c]
    if any(shift):
        _shift_solid(s, shift)
    s.write()
    return len(s.cells)


def drop(ob, voxel_m, cells):
    """Take these cubes out of the object."""
    s = Solid(ob, voxel_m)
    for c in cells:
        s.remove(c)
        s.fine.pop(c, None)
    s.write()
    return len(s.cells)


# ---- copy and paste a block (Tefa, 2026-10-06) ----
# A copy remembers one side of one of its cubes: the GLUE side. Pasting onto a side puts the copy
# just outside that side, turned so its glue side lies flat against it, so where it lands is exact.

def _rotations():
    """The 24 ways to turn a cube onto itself, as 3 x 3 integer matrices (rows)."""
    import itertools
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            m = [[0, 0, 0] for _ in range(3)]
            for r in range(3):
                m[r][perm[r]] = signs[r]
            det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                   - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                   + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            if det == 1:
                out.append(m)
    return out


def _apply(m, v):
    return tuple(m[r][0] * v[0] + m[r][1] * v[1] + m[r][2] * v[2] for r in range(3))


def turn_for(glue, onto):
    """The turn that makes the glue side face back into the side it is pasted onto, turning as
    little as possible (an upright copy stays upright whenever it can)."""
    want = tuple(-x for x in onto)
    best = None
    for m in _rotations():
        if _apply(m, glue) == want:
            score = m[0][0] + m[1][1] + m[2][2]
            if best is None or score > best[0]:
                best = (score, m)
    return best[1]


def copy_cubes(ob, voxel_m, cells, glue_cell, glue_dir):
    """What a paste needs: every picked cube, its sides' colours, and the glue side, all measured
    from the glue cube."""
    s = Solid(ob, voxel_m)
    cells = set(cells) & s.cells
    gx, gy, gz = glue_cell
    rel = lambda c: (c[0] - gx, c[1] - gy, c[2] - gz)
    return dict(
        v=s.v,
        glue=tuple(glue_dir),
        cells={rel(c): s.cell_rgb.get(c) for c in cells},
        faces={(rel(c), d): rgb for (c, d), rgb in s.faces.items() if c in cells},
    )


def paste_cubes(ob, voxel_m, clip, onto_cell, onto_dir):
    """Paste a copy onto one side of a cube. Returns how many cubes were placed."""
    s = Solid(ob, voxel_m)
    if abs(s.v - clip["v"]) > 1e-9:
        raise ValueError("the copy is %.3g mm cubes and this part is %.3g mm" % (clip["v"] * 1000, s.v * 1000))
    m = turn_for(clip["glue"], onto_dir)
    base = tuple(onto_cell[i] + onto_dir[i] for i in range(3))
    put = lambda r: tuple(base[i] + x for i, x in enumerate(_apply(m, r)))
    new = set()
    for r, rgb in clip["cells"].items():
        c = put(r)
        new.add(c)
        s.cells.add(c)
        s.fine.pop(c, None)
        if rgb:
            s.cell_rgb[c] = rgb
        for d in DIRS:                              # forget the old sides of a cube pasted over
            s._forget((c, d))
    for (r, d), rgb in clip["faces"].items():
        s.faces[(put(r), _apply(m, d))] = rgb
    keys = [(c, d) for c in new for d in DIRS
            if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) not in s.cells]
    s.write(select=keys)
    return len(new)
