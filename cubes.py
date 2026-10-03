# Small shape helpers shared by the cube models. No Blender in here.


def hash01(x, y, z, seed=0):
    h = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def ragged_cut(cells, depth_of, depth, seed=0):
    """Fray the end of something instead of slicing it flat.

    `depth_of(cell)` says how far past the cut that cube is: 0 at the cut, `depth` at the
    very end. A cube is dropped more and more often the further past the cut it is, so the
    edge breaks up into single cubes rather than ending on a clean face. Tefa asked for
    this on the gloves (2026-09-23): "end it with a pixelated cut off, not just a clean
    cut off".
    """
    out = {}
    for cell, colour in cells.items():
        d = depth_of(cell)
        if d <= 0:
            out[cell] = colour
            continue
        if d >= depth:
            continue
        if hash01(cell[0], cell[1], cell[2], seed) > (d / float(depth)) ** 0.8:
            out[cell] = colour
    return out
