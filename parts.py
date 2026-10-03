# A cube prop as named parts: {part: {(x, y, z): colour name}}. Moved here from the cube shotgun
# (2026-09-23) so every weapon builds its shape with the same few tools.
import math


class Parts:
    def __init__(self):
        self.p = {}

    def put(self, part, x, y, z, c):
        """One cube. A cube belongs to one part only, so placing it removes it from any other."""
        for other in self.p.values():
            other.pop((x, y, z), None)
        self.p.setdefault(part, {})[(x, y, z)] = c

    def fill(self, part, x0, x1, y0, y1, z0, z1, c):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    self.put(part, x, y, z, c)

    def cut(self, x0, x1, y0, y1, z0, z1):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    for d in self.p.values():
                        d.pop((x, y, z), None)

    def owned(self, cell):
        return any(cell in d for d in self.p.values())

    def tube(self, part, x0, x1, zc, r, colour, keep=True, yc=0):
        """A round tube along x. keep=False will not overwrite cells another part already owns."""
        ri = math.ceil(r)
        for x in range(x0, x1 + 1):
            for y in range(-ri, ri + 1):
                for z in range(math.floor(zc - r), math.ceil(zc + r) + 1):
                    if y * y + (z - zc) ** 2 <= r * r + 0.3:
                        if keep or not self.owned((x, y + yc, z)):
                            self.put(part, x, y + yc, z, colour)
