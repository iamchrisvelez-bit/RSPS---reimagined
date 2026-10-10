"""Detail lines: thin features of the artwork (glow cracks, engraved lines,
trim, stitching) that a triangulation would blur or break up.

They are found in the design image, traced to centre-line polylines, and
built as their own thin strips lying just in front of the surface. A strip
follows its line exactly however coarse the faces under it are, so the lines
stay crisp and continuous while the surface itself can be smoothed.
"""
import numpy as np

from .lowpoly import _components



def _box(a, r):
    """Box blur of a 2D float array (repeated three times ~ Gaussian)."""
    k = max(1, int(round(r)))
    out = a.astype(np.float64)
    for axis in (0, 1):
        for _ in range(3):
            p = np.pad(out, [(k, k) if i == axis else (0, 0) for i in range(2)], mode='edge')
            c = np.insert(np.cumsum(p, axis=axis), 0, 0, axis=axis)
            n = out.shape[axis]
            out = (np.take(c, np.arange(2 * k + 1, 2 * k + 1 + n), axis=axis)
                   - np.take(c, np.arange(0, n), axis=axis)) / (2 * k + 1)
    return out


def _shift(m, dy, dx):
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = \
        m[max(0, -dy):h + min(0, -dy), max(0, -dx):w + min(0, -dx)]
    return out


def erode(m):
    out = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out &= _shift(m, dy, dx)
    return out


def dilate(m, n=1):
    out = m.copy()
    for _ in range(n):
        cur = out.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                out |= _shift(cur, dy, dx)
    return out


def skeletonize(m):
    """Zhang-Suen thinning of a boolean image to 1-pixel-wide centre lines."""
    img = np.pad(m.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P = [img[1:-1, 1:-1]] + [img[1 + dy:img.shape[0] - 1 + dy, 1 + dx:img.shape[1] - 1 + dx]
                                     for dy, dx in ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1),
                                                    (-1, -1))]
            p1, p2, p3, p4, p5, p6, p7, p8, p9 = P
            nb = [p2, p3, p4, p5, p6, p7, p8, p9]
            B = sum(x.astype(int) for x in nb)
            A = sum(((nb[i] == 0) & (nb[(i + 1) % 8] == 1)).astype(int) for i in range(8))
            if step == 0:
                c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            kill = (p1 == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if kill.any():
                img[1:-1, 1:-1][kill] = 0
                changed = True
        if not changed:
            return img[1:-1, 1:-1].astype(bool)


_NB = ((-1, 0), (0, 1), (1, 0), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1))


def trace_polylines(skel):
    """Split a skeleton into polylines of (y, x) pixel centres, breaking at
    end points and junctions (closed loops come back as one polyline)."""
    h, w = skel.shape
    pts = set(map(tuple, np.argwhere(skel)))

    def nbrs(p):
        return [(p[0] + dy, p[1] + dx) for dy, dx in _NB if (p[0] + dy, p[1] + dx) in pts]
    deg = {p: len(nbrs(p)) for p in pts}
    seen_edges, lines = set(), []
    starts = [p for p in pts if deg[p] != 2] + [p for p in pts if deg[p] == 2]
    for s in starts:
        for n in nbrs(s):
            if (s, n) in seen_edges:
                continue
            line, prev, cur = [s], s, n
            seen_edges.add((s, n))
            seen_edges.add((n, s))
            while True:
                line.append(cur)
                if deg[cur] != 2 or cur == s:
                    break
                nxt = [q for q in nbrs(cur) if q != prev and (cur, q) not in seen_edges]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                seen_edges.add((prev, cur))
                seen_edges.add((cur, prev))
            lines.append(np.array(line, float) + 0.5)
    return lines


def simplify_open(P, eps):
    """Douglas-Peucker for an open polyline (end points kept)."""
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    ab = b - a
    L = np.hypot(*ab)
    if L < 1e-9:
        d = np.hypot(*(P - a).T)
    else:
        d = np.abs(ab[0] * (P[:, 1] - a[1]) - ab[1] * (P[:, 0] - a[0])) / L
    i = int(np.argmax(d))
    if d[i] <= eps:
        return np.array([a, b])
    return np.vstack([simplify_open(P[:i + 1], eps)[:-1], simplify_open(P[i:], eps)])


def _length(line):
    return float(np.hypot(*np.diff(line, axis=0).T).sum()) if len(line) > 1 else 0.0


def _resample(line, step):
    out = [line[0]]
    for a, b in zip(line[:-1], line[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step)))
        out += [a + (b - a) * k / n for k in range(1, n + 1)]
    return np.array(out)


def _shift_img(a, dy, dx):
    """a shifted by (dy, dx) with edge replication (works for HxW and HxWx3)."""
    h, w = a.shape[:2]
    yy = np.clip(np.arange(h) - dy, 0, h - 1)
    xx = np.clip(np.arange(w) - dx, 0, w - 1)
    return a[yy][:, xx]


def ridge_strength(target, radii=(1, 2, 3), mask=None):
    """How much each pixel looks like part of a thin line: it differs from
    the pixels on *both* sides of it (at distance r, in some direction) while
    those two sides look alike. A step edge between two flat areas - such as a
    facet border in the low-poly art - differs on one side only and scores
    low. With a mask, samples outside the item don't count (otherwise every
    thin horn or spike would read as a line against the background).
    Returns (strength, HxW)."""
    best = np.zeros(target.shape[:2])
    for r in radii:
        for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
            A, B = _shift_img(target, dy * r, dx * r), _shift_img(target, -dy * r, -dx * r)
            dA = np.linalg.norm(target - A, axis=-1)
            dB = np.linalg.norm(target - B, axis=-1)
            s = np.minimum(dA, dB) - 0.5 * np.linalg.norm(A - B, axis=-1)
            if mask is not None:
                s = np.where(_shift_img(mask, dy * r, dx * r) & _shift_img(mask, -dy * r, -dx * r), s, 0)
            best = np.maximum(best, s)
    return best


def join_polylines(lines, gap, max_turn=60.0):
    """Greedily join polylines whose ends meet (within `gap` px) and continue
    in roughly the same direction (turn below max_turn degrees), so a line
    that the skeleton split at junctions and spurs becomes one long stroke."""
    lines = [np.asarray(l, float) for l in lines if len(l) >= 2]
    cos_max = np.cos(np.radians(max_turn))

    def end_dir(l, at_end):
        k = min(len(l) - 1, 4)
        d = l[-1] - l[-1 - k] if at_end else l[0] - l[k]
        return d / max(np.hypot(*d), 1e-9)  # pointing out of the line
    changed = True
    while changed:
        changed = False
        best = None
        for i in range(len(lines)):
            for j in range(len(lines)):
                if i == j:
                    continue
                for ei in (True, False):
                    for ej in (True, False):
                        a = lines[i][-1] if ei else lines[i][0]
                        b = lines[j][-1] if ej else lines[j][0]
                        d = np.hypot(*(a - b))
                        if d > gap:
                            continue
                        # continuing straight: i's outward direction opposes j's
                        c = -float(end_dir(lines[i], ei) @ end_dir(lines[j], ej))
                        if c < cos_max:
                            continue
                        score = d - 2 * c
                        if best is None or score < best[0]:
                            best = (score, i, j, ei, ej)
        if best:
            _, i, j, ei, ej = best
            li = lines[i] if ei else lines[i][::-1]   # li ends at the joint
            lj = lines[j] if not ej else lines[j][::-1]  # lj starts at the joint
            lines[i] = np.vstack([li, lj])
            del lines[j]
            changed = True
    return lines


def _extend(pl, by):
    """Lengthen both ends of a polyline by `by` px along its end directions."""
    if len(pl) < 2 or by <= 0:
        return pl
    d0 = pl[0] - pl[1]
    d1 = pl[-1] - pl[-2]
    pl = pl.copy()
    pl[0] = pl[0] + d0 / max(np.hypot(*d0), 1e-9) * by
    pl[-1] = pl[-1] + d1 / max(np.hypot(*d1), 1e-9) * by
    return pl


def find_lines(target, mask, thr=None, weak=None, min_len=8.0, max_width=5.0, contrast=45.0, unit=1.0):
    """Detail lines of a design: [(polyline (y, x), width px, RGB)].

    Hysteresis: pixels above `weak` count as line when they connect to a
    pixel above `thr`, so a line keeps going through faint stretches and
    junctions instead of breaking into dashes. By default both thresholds
    adapt to the design: strong = half the 97th-percentile ridge strength
    (at least 45), weak = 0.55 x strong. A line whose colour is close
    to the surface around it (a facet edge of the low-poly art rather than a
    painted line) is dropped: it must differ by `contrast` or more.

    unit: design pixels per in-game (RS) unit. RS vertices sit on an integer
    grid and items are small (a helm is ~50 units across), so lines are
    widened to at least ~1.8 units and traced with segments of ~3 units:
    thinner or shorter would snap into a jagged, broken line in game."""
    h, w = mask.shape
    inner = erode(erode(mask))
    rs = ridge_strength(target, (1, 2, 3, 4), mask)
    if thr is None:
        thr = max(45.0, 0.5 * float(np.percentile(rs[mask], 97))) if mask.any() else 45.0
    if weak is None:
        weak = 0.55 * thr
    strong = (rs > thr) & inner
    cand = (rs > weak) & inner
    cand = erode(dilate(cand)) | cand  # bridge one-pixel gaps
    lab, comps = _components(cand)
    keep = np.zeros(len(comps) + 1, bool)
    keep[np.unique(lab[strong & cand])] = True
    keep[0] = False
    ridge = keep[lab]
    bg = np.stack([_box(target[..., c] * mask * ~ridge, 3) for c in range(3)], -1) / \
        np.maximum(_box((mask & ~ridge).astype(float), 3), 1e-6)[..., None]  # surface colour without lines
    standout = np.linalg.norm(target - bg, axis=-1)
    lines = []
    raw = [pl for pl in trace_polylines(skeletonize(ridge)) if _length(pl) >= 3]  # drop skeleton spurs
    for pl in join_polylines(raw, gap=max(2.5, 0.8 * unit)):
        if _length(pl) < min_len:
            continue
        pl = simplify_open(pl, max(0.6, 0.5 * unit))
        if len(pl) < 2:
            continue
        pl = _resample(pl, max(3.0, 3.0 * unit))
        yy, xx = np.clip(pl[:, 0].astype(int), 0, h - 1), np.clip(pl[:, 1].astype(int), 0, w - 1)
        near = np.zeros_like(mask)
        near[yy, xx] = True
        band = dilate(near, 2) & ridge
        width = float(np.clip(band.sum() / max(_length(pl), 1.0), 1.3, max_width))
        width = max(width, 1.8 * unit)
        if not band.any():
            continue
        # colour from the line's core: the pixels that stand out most from the
        # surface, not the anti-aliased blend at its sides
        v = standout[band]
        col = target[band][v >= np.percentile(v, 80)].mean(0)
        surf = bg[band].mean(0)
        if np.linalg.norm(col - surf) < contrast:
            continue
        # at design resolution thin lines are anti-aliased into the surface;
        # undo part of that blend so the line keeps its own colour in game
        col = np.clip(surf + (col - surf) * 1.25, 0, 255)
        grey = col.mean()
        col = np.clip(grey + (col - grey) * 1.3, 0, 255)  # and some of its saturation
        if _length(pl) < 3 * width:  # a blob or a dot, not a line
            continue
        lines.append((_extend(pl, width / 2), width, col))
    return lines


def line_coverage(lines, shape):
    """(covered mask, colour image) of the strips drawn flat at design resolution."""
    h, w = shape
    cov = np.zeros(shape, bool)
    img = np.zeros(shape + (3,))
    gy, gx = np.mgrid[0:h, 0:w] + 0.5
    for pl, width, col in lines:
        y0, x0 = np.maximum(pl.min(0) - width - 1, 0).astype(int)
        y1, x1 = np.minimum(pl.max(0) + width + 2, (h, w)).astype(int)
        sy, sx = gy[y0:y1, x0:x1], gx[y0:y1, x0:x1]
        d = np.full(sy.shape, np.inf)
        for a, b in zip(pl[:-1], pl[1:]):
            ab = b - a
            t = np.clip(((sy - a[0]) * ab[0] + (sx - a[1]) * ab[1]) / max(ab @ ab, 1e-9), 0, 1)
            d = np.minimum(d, np.hypot(sy - (a[0] + t * ab[0]), sx - (a[1] + t * ab[1])))
        on = d <= width / 2
        cov[y0:y1, x0:x1] |= on
        img[y0:y1, x0:x1][on] = col
    return cov, img


def strip_faces(lines):
    """2D strip geometry for the lines: (points (y, x), triangles, line index
    per triangle). Triangles are CCW in image (x, y-down) coordinates, the
    same convention as the surface triangulation."""
    P, T, which = [], [], []
    for li, (pl, width, _) in enumerate(lines):
        d = np.gradient(pl, axis=0) if len(pl) > 2 else np.repeat(pl[1:] - pl[:1], len(pl), 0)
        d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
        n = np.stack([-d[:, 1], d[:, 0]], 1) * (width / 2)
        base = len(P)
        for p, o in zip(pl, n):
            P += [p + o, p - o]
        for i in range(len(pl) - 1):
            a, b, c, e = base + 2 * i, base + 2 * i + 1, base + 2 * i + 2, base + 2 * i + 3
            for t in ((a, b, c), (b, e, c)):
                T.append(t)
                which.append(li)
    P = np.array(P, float).reshape(-1, 2)
    T = np.array(T, int).reshape(-1, 3)
    if len(T):  # make every triangle CCW in (x, y)
        A, B, C = P[T[:, 0]][:, ::-1], P[T[:, 1]][:, ::-1], P[T[:, 2]][:, ::-1]
        cw = ((B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])) < 0
        T[cw] = T[cw][:, ::-1]
    return P, T, np.array(which, int)


def budget_lines(lines, max_faces):
    """Keep the most visible lines (length x contrast proxy) within a face budget."""
    order = sorted(range(len(lines)), key=lambda i: -_length(lines[i][0]) * lines[i][1])
    out, used = [], 0
    for i in order:
        cost = 2 * (len(lines[i][0]) - 1)
        if used + cost <= max_faces:
            out.append(lines[i])
            used += cost
    return out
