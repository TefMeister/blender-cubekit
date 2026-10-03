# Cubes -> as few flat faces as possible, with every cube's colour kept in one texture.
#
# Lifted from the cube pistol's vp_atlas.py (2026-09-22) so the lantern and any later
# model can share it. The only change: the face shading and the per-cube wobble are
# arguments instead of imports, because different props want different amounts.
#
# Why greedy meshing at all: one quad per cube face is tens of thousands of faces, and
# the game's model format stores every vertex in every frame. Merging each flat run of
# cube faces into one rectangle cuts that by a large factor, and the per-cube colours
# move into a texture atlas.
#
# The game smooths textures, which would blur one-pixel cubes into soft gradients. So
# every cube is drawn TEXELS_PER_CUBE pixels wide with a padded border round each
# rectangle; the smoothing then only touches the last pixel at each cube edge.

TEXELS_PER_CUBE = 4
PAD = 2
ATLAS_W = 2048

# top, bottom, sides, front/back - painted into the colour, not lighting
SHADE = {(0, 0, 1): 1.15, (0, 0, -1): 0.50, (0, 1, 0): 0.85, (0, -1, 0): 0.85,
         (1, 0, 0): 0.72, (-1, 0, 0): 0.72}
NOISE = 0.06

AXES = {0: (1, 2), 1: (0, 2), 2: (0, 1)}


def hash01(x, y, z, seed=0):
    h = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def greedy_quads(cells_rgb, shade=None, noise=None):
    """Returns [(corners [4 voxel-space points], direction, pixel rows [[rgb]*w]*h)]."""
    shade = SHADE if shade is None else shade
    noise = NOISE if noise is None else noise
    quads = []
    for axis in (0, 1, 2):
        ua, va = AXES[axis]
        for sign in (1, -1):
            d = [0, 0, 0]; d[axis] = sign; d = tuple(d)
            slices = {}
            for c in cells_rgb:
                n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
                if n in cells_rgb: continue
                slices.setdefault(c[axis], {})[(c[ua], c[va])] = c
            for s, mask in sorted(slices.items()):
                done = set()
                for (u, v) in sorted(mask, key=lambda p: (p[1], p[0])):
                    if (u, v) in done: continue
                    w = 1
                    while (u + w, v) in mask and (u + w, v) not in done: w += 1
                    h = 1
                    while all((u + i, v + h) in mask and (u + i, v + h) not in done for i in range(w)):
                        h += 1
                    rows = []
                    for j in range(h):
                        row = []
                        for i in range(w):
                            done.add((u + i, v + j))
                            c = mask[(u + i, v + j)]
                            k = shade[d] * (1.0 + (hash01(*c, 9) - 0.5) * 2 * noise)
                            row.append(tuple(min(255.0, ch * k) for ch in cells_rgb[c]))
                        rows.append(row)
                    plane = s + (1 if sign > 0 else 0)
                    corners = []
                    for (du, dv) in ((0, 0), (w, 0), (w, h), (0, h)):
                        p = [0, 0, 0]; p[axis] = plane; p[ua] = u + du; p[va] = v + dv
                        corners.append(tuple(p))
                    quads.append((corners, d, rows))
    return quads


class Atlas:
    """Shelf-packs pixel rectangles; call add() for each, then pack() and pixels()."""

    def __init__(self):
        self.items = []

    def add(self, rows):
        self.items.append(rows)
        return len(self.items) - 1

    def pack(self):
        P = TEXELS_PER_CUBE
        order = sorted(range(len(self.items)), key=lambda i: -len(self.items[i]))
        self.pos = {}
        x = y = shelf = 0
        for i in order:
            rows = self.items[i]
            w, h = len(rows[0]) * P + 2 * PAD, len(rows) * P + 2 * PAD
            if x + w > ATLAS_W:
                x, y, shelf = 0, y + shelf, 0
            self.pos[i] = (x, y)
            x += w; shelf = max(shelf, h)
        used = y + shelf
        self.h = 1
        while self.h < used: self.h *= 2
        self.w = ATLAS_W

    def uv_rect(self, i):
        """(u0, v0, u1, v1) of the inner rectangle, Blender UV (v up, row 0 at the bottom)."""
        P = TEXELS_PER_CUBE
        rows = self.items[i]
        x, y = self.pos[i]
        x0, y0 = x + PAD, y + PAD
        return x0 / self.w, y0 / self.h, (x0 + len(rows[0]) * P) / self.w, (y0 + len(rows) * P) / self.h

    def pixels(self):
        """Flat RGBA float list, bottom row first (Blender image layout)."""
        import numpy as np
        P = TEXELS_PER_CUBE
        img = np.zeros((self.h, self.w, 4), dtype=np.float32); img[..., 3] = 1.0
        for i, rows in enumerate(self.items):
            x, y = self.pos[i]
            a = np.array(rows, dtype=np.float32) / 255.0
            a = np.repeat(np.repeat(a, P, axis=0), P, axis=1)
            a = np.pad(a, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='edge')
            img[y:y + a.shape[0], x:x + a.shape[1], :3] = a
        return img.ravel()
