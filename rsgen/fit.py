"""Decimation and slot fitting for arbitrary meshes headed into RS format."""
import numpy as np

from .geom import Mesh

# Target boxes in authoring units (y up, feet at 0, facing +z): (min xyz, max xyz).
# Worn slots match the player landmarks in parts.py; item-space slots are centred.
SLOT_BOX = {
    'head': ((-25, 165, -24), (25, 218, 28)),
    'body': ((-44, 90, -24), (44, 176, 26)),
    'legs': ((-30, 2, -20), (30, 106, 22)),
    'feet': ((-26, 0, -14), (26, 50, 20)),
    'hands': ((-52, 80, -8), (52, 126, 20)),
    'cape': ((-50, 34, -34), (50, 172, -14)),
    'neck': ((-26, -30, -6), (26, 30, 6)),
    'shield': ((-26, -34, -8), (26, 34, 8)),
    'weapon': ((-20, -55, -20), (20, 55, 20)),
}
WORN_SLOTS = ('head', 'body', 'legs', 'feet', 'hands', 'cape')


def reorient(mesh, up='y', forward='z'):
    """Rotate so the source `up` axis becomes +y and `forward` becomes +z.
    Axes are given as 'x', 'y', 'z' optionally prefixed with '-'."""
    def vec(a):
        s = -1.0 if a.startswith('-') else 1.0
        v = np.zeros(3)
        v['xyz'.index(a[-1])] = s
        return v
    u, f = vec(up), vec(forward)
    if abs(np.dot(u, f)) > 0.5:
        raise ValueError('up and forward must be different axes')
    r = np.cross(u, f)
    R = np.array([r, u, f])  # rows: new x, y, z expressed in source axes
    m = mesh.copy()
    m.V = mesh.V @ R.T
    if np.linalg.det(R) < 0:
        m.F = m.F[:, ::-1].copy()
    return m


def fit_to_slot(mesh, slot, fill=1.0):
    """Uniformly scale and centre the mesh inside the slot's box."""
    lo, hi = (np.array(b, float) for b in SLOT_BOX[slot])
    mlo, mhi = mesh.V.min(0), mesh.V.max(0)
    ext = np.maximum(mhi - mlo, 1e-9)
    k = float(np.min((hi - lo) / ext)) * fill
    m = mesh.copy()
    m.V = (mesh.V - (mlo + mhi) / 2) * k + (lo + hi) / 2
    return m


def cluster(mesh, cell):
    """Vertex-clustering decimation on a grid of `cell` units. Faces keep
    their colours; collapsed and duplicate faces are dropped."""
    if cell <= 0:
        return mesh.copy()
    keys = np.floor(mesh.V / cell).astype(np.int64)
    uniq, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = inv.ravel()
    sums = np.zeros((len(uniq), 3))
    np.add.at(sums, inv, mesh.V)
    cnt = np.bincount(inv, minlength=len(uniq))[:, None]
    V = sums / cnt
    F, C, G, L, seen = [], [], [], [], set()
    for (a, b, c), col, g, ly in zip(inv[mesh.F], mesh.C, mesh.G, mesh.layers()):
        if a == b or b == c or a == c:
            continue
        key = tuple(sorted((a, b, c)))
        if key in seen:
            continue
        seen.add(key)
        F.append((a, b, c))
        C.append(col)
        G.append(g)
        L.append(ly)
    return Mesh(V, F, C, G, L)


def decimate(mesh, max_faces):
    """Smallest clustering cell that brings the mesh under max_faces."""
    if len(mesh.F) <= max_faces:
        return mesh.copy()
    span = float(np.ptp(mesh.V, axis=0).max())
    lo, hi = 0.0, span / 4
    best = cluster(mesh, hi)
    for _ in range(24):
        mid = (lo + hi) / 2
        m = cluster(mesh, mid)
        if len(m.F) <= max_faces:
            best, hi = m, mid
        else:
            lo = mid
    return best
