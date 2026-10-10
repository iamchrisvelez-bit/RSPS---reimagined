"""Low-poly mesh construction kit.

Authoring space: y up, +z toward the viewer (the model's front), units are
RuneScape model units (a tile is 128 units; a player is ~200 tall with feet
at y=0). Faces are triangles wound counter-clockwise when seen from outside.
Every face carries one RGB colour and a "glow" flag (used only by the preview
renderer to keep lava/rune faces bright).
"""
import math
import numpy as np


def _rot(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == 'x':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 'y':
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Mesh:
    def __init__(self, V=None, F=None, C=None, G=None):
        self.V = np.zeros((0, 3)) if V is None else np.asarray(V, float).reshape(-1, 3)
        self.F = np.zeros((0, 3), int) if F is None else np.asarray(F, int).reshape(-1, 3)
        n = len(self.F)
        self.C = list(C) if C is not None else [(128, 128, 128)] * n
        self.G = list(G) if G is not None else [False] * n

    # ---- assembly -------------------------------------------------------
    def copy(self):
        return Mesh(self.V.copy(), self.F.copy(), list(self.C), list(self.G))

    def add(self, *others):
        for o in others:
            off = len(self.V)
            self.V = np.vstack([self.V, o.V])
            self.F = np.vstack([self.F, o.F + off])
            self.C += o.C
            self.G += o.G
        return self

    # ---- transforms (in place, chainable) --------------------------------
    def move(self, x=0, y=0, z=0):
        self.V = self.V + np.array([x, y, z], float)
        return self

    def rot(self, axis, deg, about=(0, 0, 0)):
        p = np.array(about, float)
        self.V = (self.V - p) @ _rot(axis, deg).T + p
        return self

    def scale(self, sx, sy=None, sz=None):
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        self.V = self.V * np.array([sx, sy, sz], float)
        if sx * sy * sz < 0:
            self.F = self.F[:, ::-1].copy()
        return self

    def mirrored(self):
        """Copy mirrored across x=0 (left/right counterpart)."""
        return self.copy().scale(-1, 1, 1)

    def flip(self):
        self.F = self.F[:, ::-1].copy()
        return self

    def double(self):
        """Make an open sheet visible from both sides."""
        back = self.copy().flip()
        return self.add(back)

    # ---- colour ---------------------------------------------------------
    def paint(self, col, glow=False):
        self.C = [tuple(col)] * len(self.F)
        self.G = [glow] * len(self.F)
        return self

    def centroids(self):
        return self.V[self.F].mean(axis=1)

    def normals(self):
        t = self.V[self.F]
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        ln[ln == 0] = 1
        return n / ln

    def paint_fn(self, fn):
        """fn(centroid, normal, index) -> rgb | (rgb, glow) | None (keep)."""
        cs, ns = self.centroids(), self.normals()
        for i in range(len(self.F)):
            r = fn(cs[i], ns[i], i)
            if r is None:
                continue
            if isinstance(r[0], (tuple, list)):
                self.C[i], self.G[i] = tuple(r[0]), bool(r[1])
            else:
                self.C[i], self.G[i] = tuple(r), False
        return self

    # ---- topology -------------------------------------------------------
    def subdivide(self):
        """Split each triangle into four (gives colour patterns finer grain)."""
        V = [tuple(v) for v in self.V]
        cache = {}

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                cache[k] = len(V)
                V.append(tuple((self.V[a] + self.V[b]) / 2))
            return cache[k]

        F, C, G = [], [], []
        for (a, b, c), col, g in zip(self.F, self.C, self.G):
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            F += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
            C += [col] * 4
            G += [g] * 4
        return Mesh(V, F, C, G)

    def signed_volume(self):
        t = self.V[self.F]
        return np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6

    def orient_closed(self):
        if self.signed_volume() < 0:
            self.flip()
        return self

    def bounds(self):
        return self.V.min(axis=0), self.V.max(axis=0)


def merge(*parts):
    m = Mesh()
    for p in parts:
        if p is not None:
            m.add(p)
    return m


# ---------------------------------------------------------------- primitives

def loft(rings, cap_bottom=True, cap_top=True, closed_ring=True, col=(128, 128, 128)):
    """Join a list of equal-length point rings with quads. Caps are fans to the
    ring centroid. Orientation is fixed afterwards so faces point outward."""
    rings = [np.asarray(r, float) for r in rings]
    n = len(rings[0])
    V = np.vstack(rings)
    F = []
    seg = n if closed_ring else n - 1
    for i in range(len(rings) - 1):
        for j in range(seg):
            a = i * n + j
            b = i * n + (j + 1) % n
            c = (i + 1) * n + (j + 1) % n
            d = (i + 1) * n + j
            F += [(a, b, c), (a, c, d)]
    V = list(V)
    if cap_bottom and closed_ring:
        ci = len(V)
        V.append(rings[0].mean(axis=0))
        F += [(ci, (j + 1) % n, j) for j in range(n)]
    if cap_top and closed_ring:
        ci = len(V)
        V.append(rings[-1].mean(axis=0))
        base = (len(rings) - 1) * n
        F += [(ci, base + j, base + (j + 1) % n) for j in range(n)]
    m = Mesh(V, F).paint(col)
    _orient_by_center(m)
    return m


def _orient_by_center(m):
    """Point faces away from the mesh's centre axis (works for open shells and
    closed solids built by loft/sweep). Uses majority vote."""
    if len(m.F) == 0:
        return m
    if _is_closed(m):
        return m.orient_closed()
    c = m.V.mean(axis=0)
    score = np.einsum('ij,ij->i', m.centroids() - c, m.normals()).sum()
    if score < 0:
        m.flip()
    return m


def _is_closed(m):
    edges = {}
    for a, b, c in m.F:
        for e in ((a, b), (b, c), (c, a)):
            k = (min(e), max(e))
            edges[k] = edges.get(k, 0) + 1
    return all(v == 2 for v in edges.values())


def ring(r, y, n, sx=1.0, sz=1.0, phase=0.0, cx=0.0, cz=0.0, fn=None):
    pts = []
    for j in range(n):
        t = 2 * math.pi * j / n + phase
        rr = r * (fn(t) if fn else 1.0)
        pts.append((cx + rr * math.cos(t) * sx, y, cz - rr * math.sin(t) * sz))
    return pts


def lathe(profile, n=8, sx=1.0, sz=1.0, phase=None, col=(128, 128, 128), caps=True):
    """profile: [(radius, y), ...] bottom to top. Radius 0 rows collapse to a point."""
    phase = math.pi / n if phase is None else phase
    rings = [ring(max(r, 0.01), y, n, sx, sz, phase) for r, y in profile]
    return loft(rings, cap_bottom=caps, cap_top=caps, col=col)


def prism(r_bot, r_top, h, n=6, y0=0.0, sx=1.0, sz=1.0, col=(128, 128, 128)):
    return lathe([(r_bot, y0), (r_top, y0 + h)], n, sx, sz, col=col)


def box(sx, sy, sz, col=(128, 128, 128)):
    x, y, z = sx / 2, sy / 2, sz / 2
    return loft([[(-x, -y, z), (x, -y, z), (x, -y, -z), (-x, -y, -z)],
                 [(-x, y, z), (x, y, z), (x, y, -z), (-x, y, -z)]], col=col)


def sphere(r, n=8, rings_=5, sy=1.0, col=(128, 128, 128)):
    prof = []
    for i in range(rings_ + 1):
        a = -math.pi / 2 + math.pi * i / rings_
        prof.append((r * math.cos(a), r * math.sin(a) * sy))
    return lathe(prof, n, col=col)


def gem(r, h=None, n=6, col=(128, 128, 128)):
    """Faceted bi-pyramid crystal along +y."""
    h = h or r * 2.2
    return lathe([(0, -h * 0.35), (r, 0), (r * 0.8, h * 0.25), (0, h * 0.65)], n, col=col)


def spike(base, direction, length, radius, n=4, col=(128, 128, 128)):
    """Cone from base point along direction."""
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    m = lathe([(radius, 0), (0.01, length)], n, col=col)
    _align_y_to(m, d)
    return m.move(*base)


def _align_y_to(m, d):
    y = np.array([0, 1.0, 0])
    v = np.cross(y, d)
    s, c = np.linalg.norm(v), float(np.dot(y, d))
    if s < 1e-9:
        if c < 0:
            m.scale(1, -1, -1)  # 180deg about x (det +1)
        return m
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    R = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)
    m.V = m.V @ R.T
    return m


def sweep(path, section, up=(0, 0, 1), col=(128, 128, 128), caps=True, scales=None):
    """Sweep a 2D section [(u, v), ...] along a 3D path. u runs along
    binormal (tangent x up), v along 'up'. scales: per-point (su, sv)."""
    P = np.asarray(path, float)
    U = np.asarray(up, float)
    rings = []
    for i, p in enumerate(P):
        if i == 0:
            t = P[1] - P[0]
        elif i == len(P) - 1:
            t = P[-1] - P[-2]
        else:
            t = P[i + 1] - P[i - 1]
        t = t / np.linalg.norm(t)
        nv = U - np.dot(U, t) * t
        if np.linalg.norm(nv) < 1e-6:
            nv = np.array([1.0, 0, 0]) - t[0] * t
        nv /= np.linalg.norm(nv)
        b = np.cross(t, nv)
        su, sv = scales[i] if scales is not None else (1, 1)
        rings.append([p + u * su * b + v * sv * nv for u, v in section])
    return loft(rings, cap_bottom=caps, cap_top=caps, col=col)


def circle2d(r, n, phase=None):
    phase = math.pi / n if phase is None else phase
    return [(r * math.cos(phase + 2 * math.pi * j / n), r * math.sin(phase + 2 * math.pi * j / n)) for j in range(n)]


def tube(path, r, n=5, col=(128, 128, 128), taper=None, up=(0, 0, 1)):
    """taper: list of radius multipliers per path point."""
    sc = None if taper is None else [(t, t) for t in taper]
    return sweep(path, circle2d(r, n), up=up, col=col, scales=sc)


def bezier(p0, p1, p2, p3=None, steps=8):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        if p3 is None:
            q = (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)
        else:
            q = ((1 - t) ** 3 * np.array(p0) + 3 * (1 - t) ** 2 * t * np.array(p1)
                 + 3 * (1 - t) * t ** 2 * np.array(p2) + t ** 3 * np.array(p3))
        pts.append(q)
    return np.array(pts, float)


def torus(R, r, n_major=8, n_minor=4, col=(128, 128, 128)):
    """Ring lying in the xy plane (hole along z)."""
    path = [(R * math.cos(2 * math.pi * i / n_major), R * math.sin(2 * math.pi * i / n_major), 0)
            for i in range(n_major)]
    rings = []
    for i, p in enumerate(path):
        a = 2 * math.pi * i / n_major
        radial = np.array([math.cos(a), math.sin(a), 0])
        rings.append([np.array(p) + r * (math.cos(b) * radial + math.sin(b) * np.array([0, 0, 1.0]))
                      for b in [2 * math.pi * k / n_minor for k in range(n_minor)]])
    rings.append(rings[0])
    m = loft(rings, cap_bottom=False, cap_top=False, col=col)
    # loft duplicated the first ring; weld it
    n = n_minor
    last = len(rings) - 1
    F = m.F.copy()
    F[F >= last * n] -= last * n
    m.F = F
    m.V = m.V[:last * n]
    # outward = away from tube centre line
    cs, ns = m.centroids(), m.normals()
    ang = np.arctan2(cs[:, 1], cs[:, 0])
    core = np.stack([R * np.cos(ang), R * np.sin(ang), np.zeros_like(ang)], 1)
    if np.einsum('ij,ij->i', cs - core, ns).sum() < 0:
        m.flip()
    return m


def chain(path, link=5.0, col=(150, 150, 150), thick=0.18):
    """String of interlocking low-poly links following a path (polyline)."""
    P = np.asarray(path, float)
    seg = np.diff(P, axis=0)
    L = np.linalg.norm(seg, axis=1)
    total, step = L.sum(), link * 1.5
    out = Mesh()
    d, k = 0.0, 0
    while d <= total:
        acc, i = d, 0
        while i < len(L) - 1 and acc > L[i]:
            acc -= L[i]
            i += 1
        p = P[i] + seg[i] / L[i] * min(acc, L[i])
        t = seg[i] / L[i]
        lk = torus(link * 0.55, link * thick, 6, 3, col).scale(1.0, 0.65, 1.0)
        lk.rot('y' if k % 2 else 'x', 90 if k % 2 else 0)
        # point the link's long (x) axis along t
        m2 = Mesh(lk.V.copy(), lk.F, lk.C, lk.G)
        _align_x_to(m2, t)
        out.add(m2.move(*p))
        d += step
        k += 1
    return out


def _align_x_to(m, d):
    # rotate so +x maps to d: align y to d then rotate -90 about z first
    m.rot('z', 90)
    return _align_y_to(m, d)


# ------------------------------------------------------------ flat extrusion

def _area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def triangulate(poly):
    """Ear clipping for a simple CCW polygon. Returns index triples."""
    idx = list(range(len(poly)))
    P = [np.array(p, float) for p in poly]
    tris = []

    def inside(p, a, b, c):
        d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1])
        d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1])
        d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1])
        neg = d1 < 0 or d2 < 0 or d3 < 0
        pos = d1 > 0 or d2 > 0 or d3 > 0
        return not (neg and pos)

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        n = len(idx)
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]
            a, b, c = P[i0], P[i1], P[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 1e-9:
                continue
            if any(inside(P[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def extrude(poly, depth, bevel=0.0, inset=0.85, col=(128, 128, 128), dome=0.0):
    """Extrude a 2D polygon (x, y) along z. With bevel>0 the front/back caps
    are shrunk toward the centroid by `inset`, giving a chamfered slab.
    dome pushes the front cap centre forward (shield bulge)."""
    poly = [tuple(p) for p in poly]
    if _area(poly) < 0:
        poly = poly[::-1]
    P = np.array(poly, float)
    c = P.mean(axis=0)
    h = depth / 2
    if bevel > 0:
        Pi = c + (P - c) * inset
        layers = [(Pi, -h), (P, -h + bevel), (P, h - bevel), (Pi, h)]
    else:
        layers = [(P, -h), (P, h)]
    n = len(P)
    V, F = [], []
    for L, z in layers:
        V += [(x, y, z) for x, y in L]
    for i in range(len(layers) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            c2, d = (i + 1) * n + (j + 1) % n, (i + 1) * n + j
            F += [(a, b, c2), (a, c2, d)]
    tris = triangulate([tuple(p) for p in layers[-1][0]])
    top = (len(layers) - 1) * n
    if dome:
        # fan the front cap from a raised centre for a gentle bulge
        ci = len(V)
        V.append((c[0], c[1], h + dome))
        F += [(top + j, top + (j + 1) % n, ci) for j in range(n)]
    else:
        F += [(top + a, top + b, top + c3) for a, b, c3 in tris]
    F += [(c3, b, a) for a, b, c3 in tris]
    m = Mesh(V, F).paint(col)
    return m.orient_closed()


def shade(col, k):
    """Scale an RGB colour's brightness (k<1 darker)."""
    return tuple(int(max(0, min(255, c * k))) for c in col)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
