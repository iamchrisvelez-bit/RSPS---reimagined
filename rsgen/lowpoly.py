"""Image-guided low-poly triangulation (the art style of the designs).

Points are placed densely along the silhouette and along colour-region
boundaries, sparsely elsewhere; a Delaunay triangulation of them, trimmed to
the silhouette, gives triangles that follow the artwork's outline and colour
regions. Each triangle takes the dominant palette colour beneath it.
"""
import random

import numpy as np


def delaunay(P):
    """Bowyer-Watson Delaunay triangulation of 2D points -> (M, 3) indices."""
    P = np.asarray(P, float)
    n = len(P)
    lo, hi = P.min(0), P.max(0)
    span = float((hi - lo).max()) * 20 + 1
    c = (lo + hi) / 2
    S = np.vstack([P, [c + [-span, -span], c + [span, -span], c + [0, span]]])
    tris = [(n, n + 1, n + 2)]
    for i in range(n):
        T = np.array(tris)
        A, B, C = S[T[:, 0]], S[T[:, 1]], S[T[:, 2]]
        # circumcircle test, vectorised over all triangles
        ax, ay = A[:, 0] - S[i, 0], A[:, 1] - S[i, 1]
        bx, by = B[:, 0] - S[i, 0], B[:, 1] - S[i, 1]
        cx, cy = C[:, 0] - S[i, 0], C[:, 1] - S[i, 1]
        det = ((ax * ax + ay * ay) * (bx * cy - cx * by) - (bx * bx + by * by) * (ax * cy - cx * ay)
               + (cx * cx + cy * cy) * (ax * by - bx * ay))
        orient = (B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])
        bad = (det * np.sign(orient)) > 0
        edges = {}
        for t in T[bad]:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = (min(e), max(e))
                edges[k] = edges.get(k, 0) + 1
        tris = [tuple(t) for t in T[~bad]]
        for (a, b), cnt in edges.items():
            if cnt == 1:
                tris.append((a, b, i))
    T = np.array([t for t in tris if max(t) < n])
    # consistent CCW orientation in (x, y)
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    cw = ((B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])) < 0
    T[cw] = T[cw][:, ::-1]
    return T


def boundary_pixels(m):
    p = np.pad(m, 1)
    inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~inner


def _components(m):
    from collections import deque
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    out = []
    for sy, sx in zip(*np.nonzero(m)):
        if lab[sy, sx]:
            continue
        k = len(out) + 1
        lab[sy, sx] = k
        q, n = deque([(sy, sx)]), 0
        while q:
            y, x = q.popleft()
            n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = k
                    q.append((ny, nx))
        out.append((k, n))
    return lab, out


def trace_outline(m):
    """Outer boundary of a blob as an ordered loop of pixel-corner points (y, x).

    Every inside pixel edge that faces an outside pixel becomes a directed
    edge with the inside on a consistent side; chaining the edges yields
    closed loops (outer outline and holes). The longest loop is the outline."""
    p = np.pad(m, 1)
    nxt = {}
    ys, xs = np.nonzero(m)
    for r, c in zip(ys, xs):
        R, C = r + 1, c + 1  # index into the padded mask
        if not p[R - 1, C]:
            nxt.setdefault((r, c + 1), []).append((r, c))
        if not p[R + 1, C]:
            nxt.setdefault((r + 1, c), []).append((r + 1, c + 1))
        if not p[R, C - 1]:
            nxt.setdefault((r, c), []).append((r + 1, c))
        if not p[R, C + 1]:
            nxt.setdefault((r + 1, c + 1), []).append((r, c + 1))
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop, cur = [start], start
        while True:
            outs = nxt.get(cur)
            if not outs:
                break
            nx = outs.pop()
            if not outs:
                del nxt[cur]
            if nx == start:
                break
            loop.append(nx)
            cur = nx
        loops.append(loop)
    best = max(loops, key=len)
    return np.array(best, float)


def simplify(P, eps):
    """Douglas-Peucker on a closed polyline."""
    if len(P) < 4:
        return P

    def dp(seg):
        a, b = seg[0], seg[-1]
        ab = b - a
        L = np.hypot(*ab)
        rel = seg - a
        d = np.abs(ab[0] * rel[:, 1] - ab[1] * rel[:, 0]) / L if L > 1e-9 else np.hypot(*rel.T)
        i = int(np.argmax(d))
        if d[i] > eps and 0 < i < len(seg) - 1:
            return np.vstack([dp(seg[:i + 1])[:-1], dp(seg[i:])])
        return np.vstack([a, b])
    far = int(np.argmax(np.hypot(*(P - P[0]).T)))
    return np.vstack([dp(P[:far + 1])[:-1], dp(np.vstack([P[far:], P[:1]]))[:-1]])


def resample(P, step):
    """Insert points so no closed-polyline segment is longer than step."""
    out = []
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step)))
        out += [a + (b - a) * k / n for k in range(n)]
    return np.array(out)


def outline_points(m, eps=1.0, step=6.0, min_area=30):
    """Clean, evenly spaced silhouette points for every blob of the mask."""
    lab, comps = _components(m)
    pts = []
    for k, n in comps:
        if n < min_area:
            continue
        ring = trace_outline(lab == k)
        if len(ring) >= 3:
            pts.append(resample(simplify(ring, eps), step))
    return np.vstack(pts) if pts else np.zeros((0, 2))


def poisson_pick(cands, weights, radius, limit, rng):
    """Weighted Poisson-disk selection: higher weight first, min spacing radius."""
    keys = np.array([rng.random() ** (1.0 / max(w, 1e-6)) for w in weights])
    order = np.argsort(-keys)
    cell = radius / 1.42
    grid, out = {}, []
    for i in order:
        y, x = cands[i]
        gy, gx = int(y // cell), int(x // cell)
        ok = True
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                q = grid.get((gy + dy, gx + dx))
                if q is not None and (q[0] - y) ** 2 + (q[1] - x) ** 2 < radius * radius:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            grid[(gy, gx)] = (y, x)
            out.append((y, x))
            if len(out) >= limit:
                break
    return out


def triangulate_art(mask, labels, n_points=420, edge_spacing=3.0, seed=0):
    """Points (y, x), triangles and per-triangle palette label for an item.

    mask: bool HxW silhouette; labels: int HxW palette index (-1 outside)."""
    rng = random.Random(seed)
    h, w = mask.shape
    pts = [tuple(p) for p in outline_points(mask, eps=max(0.8, edge_spacing * 0.35), step=edge_spacing * 1.6)]
    n_edge = len(pts)
    # colour-region borders inside the item attract points
    L = labels
    border = np.zeros_like(mask)
    border[:-1] |= (L[:-1] != L[1:]) & mask[:-1] & mask[1:]
    border[:, :-1] |= (L[:, :-1] != L[:, 1:]) & mask[:, :-1] & mask[:, 1:]
    shrunk = mask & ~boundary_pixels(mask)
    shrunk = shrunk & ~boundary_pixels(shrunk)  # keep interior points off the rim
    inner = np.argwhere(shrunk)
    wts = np.where(border[inner[:, 0], inner[:, 1]], 6.0, 1.0)
    budget = max(n_points - n_edge, 20)
    area = float(mask.sum())
    radius = max(2.0, (area / budget) ** 0.5 * 0.55)
    pts += poisson_pick(inner, wts, radius, budget, rng)
    P = np.array(pts, float)
    T = delaunay(P[:, ::-1])  # triangulate in (x, y)
    # keep triangles that lie inside the silhouette (test centroid and edge midpoints)
    def inside(p):
        # outline points lie on pixel corners: a point counts as inside when it
        # touches an inside pixel (pixel (r, c) spans [r, r+1) x [c, c+1))
        y0, x0 = int(np.floor(p[0] - 0.5)), int(np.floor(p[1] - 0.5))
        return any(0 <= y < h and 0 <= x < w and mask[y, x]
                   for y in (y0, y0 + 1) for x in (x0, x0 + 1))
    keep = []
    for t in T:
        a, b, c = P[t]
        cen = (a + b + c) / 3
        if (mask[min(h - 1, int(cen[0])), min(w - 1, int(cen[1]))]
                and all(inside(p) for p in ((a + b) / 2, (b + c) / 2, (c + a) / 2))):
            keep.append(t)
    T = np.array(keep)
    # dominant label under each triangle
    lab = []
    for t in T:
        a, b, c = P[t]
        y0, y1 = int(max(0, np.floor(min(a[0], b[0], c[0])))), int(min(h - 1, np.ceil(max(a[0], b[0], c[0]))))
        x0, x1 = int(max(0, np.floor(min(a[1], b[1], c[1])))), int(min(w - 1, np.ceil(max(a[1], b[1], c[1]))))
        gy, gx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            lab.append(L[int(a[0]), int(a[1])])
            continue
        l1 = ((b[1] - c[1]) * (gy - c[0]) + (c[0] - b[0]) * (gx - c[1])) / d
        l2 = ((c[1] - a[1]) * (gy - c[0]) + (a[0] - c[0]) * (gx - c[1])) / d
        inside = (l1 >= -0.05) & (l2 >= -0.05) & (1 - l1 - l2 >= -0.05)
        vals = L[gy[inside], gx[inside]]
        vals = vals[vals >= 0]
        cy = min(h - 1, int((a[0] + b[0] + c[0]) / 3))
        cx = min(w - 1, int((a[1] + b[1] + c[1]) / 3))
        lab.append(int(np.bincount(vals).argmax()) if len(vals) else int(max(L[cy, cx], 0)))
    on_edge = np.zeros(len(P), bool)
    on_edge[:n_edge] = True
    return P, T, np.array(lab), on_edge
