# Whole-model cube size changes: every cube into 8 (finer) or every 8 back into one (bigger).
# Moved out of edit.py unchanged on 2026-10-08 (file size rule); edit.py re-exports everything here.
import math

from edit import FINE, DIRS, MERGE_KEEP, Solid
import edit_small as small

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
    fine, sfaces = {}, {}
    for cell, fc in s.fine.items():
        for o in range(8):
            a, b, e = o % 2, (o // 2) % 2, o // 4
            child = (2 * cell[0] + sh[0] + a, 2 * cell[1] + sh[1] + b, 2 * cell[2] + sh[2] + e)
            members = [i for i in small.octant_subs(o) if i in fc.subs]
            if not members:
                continue
            if o in fc.half:                                  # a half cube -> a whole cube
                cells.add(child)
                cols = [fc.subs[i] for i in members if fc.subs[i]]
                own = max(set(cols), key=cols.count) if cols else None
                if own:
                    cell_rgb[child] = own
                for d in DIRS:
                    ax, ua, va = small._axes(d)
                    painted = {i: s.sfaces[(cell, i, d)] for i in small.outer_subs(members[0], 2, d)
                               if (cell, i, d) in s.sfaces}
                    if not painted:
                        continue
                    fine16 = [own or s.cell_rgb.get(cell) or small.UNPAINTED] * (FINE * FINE)
                    for i, c in painted.items():
                        li = small.local(i)
                        qu, qv = (li[ua] % 2) * 2, (li[va] % 2) * 2
                        for x in (0, 1):
                            for y in (0, 1):
                                fine16[(qu + x) + FINE * (qv + y)] = c
                    faces[(child, d)] = max(set(fine16), key=fine16.count)
                    if len(set(fine16)) > 1:
                        split[(child, d)] = fine16
                        level[(child, d)] = 1
                continue
            nfc = fine.setdefault(child, small.FineCell())
            for i in members:                                 # a quarter cube -> a half cube
                x, y, z = small.local(i)
                no = (x % 2) + 2 * (y % 2) + 4 * (z % 2)
                octant = small.octant_subs(no)
                for j in octant:
                    nfc.subs[j] = fc.subs[i]
                nfc.half.add(no)
                for d in DIRS:
                    c = s.sfaces.get((cell, i, d))
                    if c is None:
                        continue
                    ax = [k for k in range(3) if d[k]][0]
                    edge = small.local(octant[0])[ax] + (1 if d[ax] > 0 else 0)
                    for j in octant:
                        if small.local(j)[ax] == edge:
                            sfaces[(child, j, d)] = c
    s.v, s.off = v / 2, new_off
    s.cells, s.cell_rgb, s.faces, s.split, s.level = cells, cell_rgb, faces, split, level
    s.fine, s.sfaces = fine, sfaces
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
    for cell in list(s.fine):                 # smaller cubes join back into whole ones first
        small.join_cell(s, cell)
    s.sfaces = {}
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
