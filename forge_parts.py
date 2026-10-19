# Gun pieces and paints for forge models, shared by every forge gun (Ashes and Brutal Doom). No Blender here.
# Units are main cubes (3.4 mm); x = rear -> muzzle, y = left, z = up, the bore on y = 0.
import math

from forge import hash01, mix, mul


# ---------------------------------------------------------------- paints: functions of a cube's centre
def flat(rgb):
    return lambda x, y, z: rgb


def metal(rgb, speck=0.06, seed=1):
    """Gun metal: a little speckle per cube."""
    return lambda x, y, z: mul(rgb, 1.0 + speck * (hash01(math.floor(x * 4), math.floor(y * 4), math.floor(z * 4),
                                                          seed) - 0.5) * 2)


def wood(light, dark, ring=2.6, seed=3, along='x'):
    """Wood with its grain running along x (or z): bands of the dark colour that wander."""
    def f(x, y, z):
        a, b = (x, z) if along == 'x' else (z, x)
        w = math.sin((b + 1.7 * math.sin(a * 0.11 + seed) + 0.6 * math.sin(a * 0.37 + y * 0.5)) * math.pi / ring)
        t = max(0.0, w) ** 3 * 0.85 + 0.15 * hash01(math.floor(a), math.floor(b), seed)
        return mix(light, dark, t)
    return f


def rusty(rgb, rust=(110, 52, 26), amount=0.35, scale=5.0, seed=9):
    """Metal with rust blooming in patches."""
    def f(x, y, z):
        n = (math.sin(x / scale + seed) * math.sin(z / scale * 1.3 + seed * 2) * math.sin(y / scale * 0.7 + seed)
             + hash01(math.floor(x / 2), math.floor(y / 2), math.floor(z / 2), seed) * 0.6)
        t = max(0.0, min(1.0, (n - (1.0 - amount)) * 2.2))
        return mix(mul(rgb, 1 + 0.08 * (hash01(math.floor(x), math.floor(y), math.floor(z), seed + 1) - 0.5)), rust,
                   t * (0.5 + 0.5 * hash01(math.floor(x * 2), math.floor(z * 2), seed + 2)))
    return f


def stripes(a, b, step=3.0, axis='x'):
    def f(x, y, z):
        v = {'x': x, 'y': y, 'z': z}[axis]
        return a if math.floor(v / step) % 2 == 0 else b
    return f


# ---------------------------------------------------------------- pieces
def barrel(m, x0, x1, zc, r, col, bore=None, bore_col=(8, 8, 9), yc=0.0, edge=0.5, muzzle_ring=None):
    """A round barrel along x with its bore cut into the muzzle end (bore radius, depth 4 cubes)."""
    m.cyl(x0, x1, yc, zc, r, col, edge=edge)
    if muzzle_ring:
        rr, length, rc = muzzle_ring
        m.cyl(x1 - length, x1, yc, zc, rr, rc, edge=0.25)
    if bore:
        m.cyl(x1 - 4, x1 + 1, yc, zc, bore, None, edge=0.25, carve=True)
        m.cyl(x1 - 4.5, x1 - 4, yc, zc, bore, bore_col, size=0.25, edge=0.25)


def trigger(m, x, ztop, col, length=7.0, curve=2.5, part='trigger'):
    """A curved trigger blade hanging from (x, ztop), curling forward, one cube wide."""
    pts = []
    for i in range(int(length * 4) + 1):
        t = i / (length * 4)
        pts.append((x + curve * math.sin(t * 1.4) - curve * 0.6 * t, ztop - t * length))
    for (a, b) in pts:
        m.put(a - 0.25, -0.5, b - 0.25, col, 0.5, part)
        m.put(a - 0.25, 0.0, b - 0.25, col, 0.5, part)


def guard(m, x0, x1, z_bottom, z_top, col, w=2.0, thick=1.5):
    """A trigger guard loop: a flat bottom bar from x0 to x1, rising to z_top at both ends, open in the middle."""
    def inside(x, y, z):
        if abs(y) > w / 2:
            return False
        cx, cz = (x0 + x1) / 2, z_top
        rx, rz = (x1 - x0) / 2, z_top - z_bottom
        d = ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2
        din = ((x - cx) / max(0.1, rx - thick)) ** 2 + ((z - cz) / max(0.1, rz - thick)) ** 2
        return z <= z_top and d <= 1.0 and din > 1.0
    m.fill(inside, (x0, x1, -w / 2, w / 2, z_bottom, z_top), col, 0.5, 0.25)


def checker(m, poly_region, side, col_a, col_b, step=1):
    """Checkered grip panel: alternate quarter-cube diamonds painted over a region (x0, x1, z0, z1)."""
    x0, x1, z0, z1 = poly_region
    q = 4
    for qa in range(int(x0 * q), int(x1 * q)):
        for qb in range(int(z0 * q), int(z1 * q)):
            if ((qa + qb) // (2 * step)) % 2 == 0 and ((qa - qb) // (2 * step)) % 2 == 0:
                qq = m.surface_q(side, qa, qb)
                if qq:
                    v = m.get_q(*qq)
                    m.put_q(*qq, col_b if v[0] != col_b else col_a, v[1], v[2])


def sight_post(m, x, z_base, h, col, w=1.0, dot=None):
    m.box(x, x + 1, -w / 2, w / 2, z_base, z_base + h, col, size=0.5, edge=0.25)
    if dot:
        m.box(x, x + 0.25, -0.25, 0.25, z_base + h - 0.75, z_base + h - 0.25, dot, size=0.25)


def rear_sight(m, x, z_base, h, col, w=4.0, notch=1.5, dots=None):
    m.box(x, x + 1.5, -w / 2, w / 2, z_base, z_base + h, col, size=0.5, edge=0.25, bevel_x=0.5)
    m.box(x - 0.5, x + 2.5, -notch / 2, notch / 2, z_base + h - 1.5, z_base + h + 0.5, None, size=0.25, carve=True)
    if dots:
        for y in (-notch / 2 - 0.75, notch / 2 + 0.25):
            m.box(x, x + 0.25, y, y + 0.5, z_base + h - 1.0, z_base + h - 0.5, dots, size=0.25)


def screws_row(m, side, a0, a1, b, n, col=(70, 72, 76), kind='slot'):
    for i in range(n):
        a = a0 + (a1 - a0) * (i / max(1, n - 1))
        m.screw(a, b, side, col, kind=kind)


def both(fn, *args, **kw):
    """Run a side job (screw, groove, decal...) on both the left (+y) and right (-y) faces."""
    for side in ('+y', '-y'):
        fn(*args, side=side, **kw)


def band(m, x0, x1, zc, r, col, yc=0.0):
    """A clamp band round a round part: slightly bigger radius, quarter-cube edges."""
    m.cyl(x0, x1, yc, zc, r, col, edge=0.25)


def ellipse_tube_profile(xs, zs):
    return list(zip(xs, zs))
