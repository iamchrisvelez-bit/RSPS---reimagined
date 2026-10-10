"""Reusable equipment templates fitted to the standard player body.

Body landmarks (authoring units, y up, feet at 0, facing +z):
  head centre (0,190,2) r~20 | neck y170 | shoulders y160 x+-31
  chest y140 | waist y100 | hips y92 | knees y50 | hands y~95 x+-40
Weapons/shields/jewellery are built in item space (grip or centre at origin).

Angles: a body angle t places a point at (w cos t, y, -d sin t), so the
front of the body (+z) is t = 3*pi/2. FRONT is that angle.
"""
import math
import random

import numpy as np

from .geom import (Mesh, merge, loft, lathe, ring, prism, box, sphere, spike, sweep, tube, bezier,
                   chain, extrude, shade)

HEAD = np.array([0.0, 190.0, 2.0])
FRONT = 1.5 * math.pi


def rel_angle(t):
    """Signed angle from the front of the body, in [-pi, pi)."""
    return (t - FRONT + math.pi) % (2 * math.pi) - math.pi


# ------------------------------------------------------------- colour helpers

def jitter(m, amt, seed=0):
    """Small per-face brightness variation (the hand-faceted look)."""
    rng = random.Random(seed)
    m.C = [shade(c, 1 + rng.uniform(-amt, amt)) if not g else c for c, g in zip(m.C, m.G)]
    return m


def cracks(m, seeds, col, glow=True, seed=1, warp=0.35, width=1.8, lift=1.0, where=None, max_faces=None):
    """Thin crack lines on a surface, returned merged with the surface.

    Every vertex is labelled with its nearest seed of a warped Voronoi
    partition; the partition borders are traced across each face (marching
    triangles: crossing points are interpolated on the edges) and each border
    segment becomes a flat strip `width` units wide, lifted `lift` units along
    the face normal. Lines stay crisp and thin at any mesh density for only
    two faces per segment. where(point) limits the cracks to a region;
    max_faces caps the number of strip faces added."""
    if len(m.F) == 0:
        return m
    rng = random.Random(seed)
    V = m.V
    span = float(np.ptp(V, axis=0).max()) or 1.0
    ph = [rng.uniform(0, 6.3) for _ in range(6)]
    f = 6.0 / span
    amp = warp * span / max(seeds, 1) ** 0.5 * 0.5
    W = V + amp * np.stack([
        np.sin(V[:, 1] * f + ph[0]) + np.sin(V[:, 2] * f * 1.7 + ph[1]),
        np.sin(V[:, 2] * f + ph[2]) + np.sin(V[:, 0] * f * 1.7 + ph[3]),
        np.sin(V[:, 0] * f + ph[4]) + np.sin(V[:, 1] * f * 1.7 + ph[5])], 1)
    S = W[[rng.randrange(len(W)) for _ in range(seeds)]]
    D = np.sqrt(((W[:, None, :] - S[None, :, :]) ** 2).sum(-1))  # vertex-to-seed distances
    lab = np.argmin(D, axis=1)

    def cross(a, b):
        i, j = lab[a], lab[b]
        fa, fb = D[a, i] - D[a, j], D[b, i] - D[b, j]
        t = fa / (fa - fb) if fa != fb else 0.5
        t = min(max(t, 0.0), 1.0)
        return V[a] + (V[b] - V[a]) * t

    ns = m.normals()
    strips = Mesh()
    sv, sf = [], []
    for k, (a, b, c) in enumerate(m.F):
        la, lb, lc = lab[a], lab[b], lab[c]
        if la == lb == lc:
            continue
        pts = [cross(x, y) for x, y in ((a, b), (b, c), (c, a)) if lab[x] != lab[y]]
        segs = [(pts[0], pts[1])] if len(pts) == 2 else [(p, (V[a] + V[b] + V[c]) / 3) for p in pts]
        n = ns[k]
        for p0, p1 in segs:
            d = p1 - p0
            L = np.linalg.norm(d)
            if L < 1e-6 or (where is not None and not where((p0 + p1) / 2)):
                continue
            side = np.cross(d / L, n) * (width / 2)
            # extend a little past the edge so neighbouring segments overlap (no gaps)
            e = d / L * min(width * 0.3, L * 0.25)
            q0, q1 = p0 - e + n * lift, p1 + e + n * lift
            base = len(sv)
            sv += [q0 - side, q1 - side, q1 + side, q0 + side]
            # wind so the strip faces along n
            if np.dot(np.cross(sv[base + 1] - sv[base], sv[base + 2] - sv[base]), n) >= 0:
                sf += [(base, base + 1, base + 2), (base, base + 2, base + 3)]
            else:
                sf += [(base, base + 2, base + 1), (base, base + 3, base + 2)]
            if max_faces and len(sf) >= max_faces:
                break
        if max_faces and len(sf) >= max_faces:
            break
    if sf:
        strips = Mesh(np.array(sv), sf).paint(col, glow)
    return merge(m, strips)


def speckle(m, frac, col, glow=False, seed=0):
    """Scatter single bright faces (starfield / embers)."""
    rng = random.Random(seed)
    for i in range(len(m.F)):
        if rng.random() < frac:
            m.C[i], m.G[i] = tuple(col), glow
    return m


def bands(m, axis, period, cols, offset=0.0):
    cs = m.centroids()
    for i, c in enumerate(cs):
        if not m.G[i]:
            m.C[i] = cols[int(math.floor((c[axis] + offset) / period)) % len(cols)]
    return m


def scales_pattern(m, base, size=7.0, axis_r=None):
    """Diamond fish-scale shading: each scale bright at its lower tip and
    darker where the next row overlaps it."""
    cs = m.centroids()
    for i, c in enumerate(cs):
        if m.G[i]:
            continue
        r = axis_r or math.hypot(c[0], c[2]) or 1.0
        u = math.atan2(c[2], c[0]) * r / size
        v = c[1] / size
        p, q = u + v, v - u
        fy = (q % 1.0 + p % 1.0) / 2  # 0 at the bottom tip, 1 under the overlap
        m.C[i] = shade(base, 1.18 - 0.42 * fy)
    return m


def paint_where(m, pred, col, glow=False):
    cs, ns = m.centroids(), m.normals()
    for i in range(len(m.F)):
        if pred(cs[i], ns[i]):
            m.C[i], m.G[i] = tuple(col), glow
    return m


# ---------------------------------------------------------------- the body
# (y, half width, half depth) of the torso surface armour sits on
TORSO = [(84, 25.0, 15.5), (96, 25.5, 15.5), (104, 26.0, 16.0), (116, 27.5, 17.0), (128, 30.0, 18.5),
         (140, 32.0, 19.5), (152, 33.0, 19.0), (159, 31.5, 17.5), (165, 25.0, 15.0), (170, 16.0, 11.5)]


def torso_wd(y):
    ys = [r[0] for r in TORSO]
    return float(np.interp(y, ys, [r[1] for r in TORSO])), float(np.interp(y, ys, [r[2] for r in TORSO]))


def body_pt(t, y, out=0.0, bulk=1.0):
    w, d = torso_wd(y)
    keel = 1.0 + 0.10 * max(0.0, -math.sin(t)) ** 3 if 118 < y < 162 else 1.0
    return np.array([(w * bulk + out) * math.cos(t), y, -(d * bulk + out) * math.sin(t) * keel])


def body_rings(ys, n=12, out=0.0, bulk=1.0):
    return [[body_pt(2 * math.pi * j / n, y, out, bulk) for j in range(n)] for y in ys]


def body_shell(col, y0=96, y1=170, n=12, out=0.0, bulk=1.0):
    ys = sorted({y0, y1} | {r[0] for r in TORSO if y0 < r[0] < y1})
    return loft(body_rings(ys, n, out, bulk), col=col)


def plate_band(y0, y1, col, n=12, out=1.0, flare=1.8, bulk=1.0, inner_col=None):
    """One overlapping armour lame: tucked in at the top, flared at the bottom
    edge. A closed solid (outer face, rolled lower edge, hidden inner face)."""
    top_o = [body_pt(2 * math.pi * j / n, y1, out, bulk) for j in range(n)]
    bot_o = [body_pt(2 * math.pi * j / n, y0, out + flare, bulk) for j in range(n)]
    bot_i = [body_pt(2 * math.pi * j / n, y0, out - 0.6, bulk) for j in range(n)]
    top_i = [body_pt(2 * math.pi * j / n, y1, out - 1.4, bulk) for j in range(n)]
    m = loft([top_o, bot_o, bot_i, top_i], col=col, loop=True)
    if inner_col:
        paint_where(m, lambda c, nn: nn[1] < -0.6, inner_col)
    return m


def body_strip(t, y0, y1, width, col, out=0.8, th=1.4, steps=None, bulk=1.0):
    """A flat strap lying on the torso surface at body angle t (trim, placket)."""
    steps = steps or max(2, int(abs(y1 - y0) / 6))
    rings = []
    for y in np.linspace(y0, y1, steps + 1):
        p = body_pt(t, y, out, bulk)
        p2 = body_pt(t + 0.01, y, out, bulk)
        h = (p2 - p) / np.linalg.norm(p2 - p)
        nrm = np.cross(h, [0, 1.0, 0])
        nrm = nrm if np.dot(nrm, p - [0, y, 0]) > 0 else -nrm
        a = width / 2
        rings.append([p + h * a, p + h * a + nrm * th, p - h * a + nrm * th, p - h * a])
    return loft(rings, col=col)


def ring_band(r_out, r_in, y0, y1, col, n=12, sz=0.82, flare=0.0, inner_col=None, cx=0.0, cz=0.0):
    """Hollow collar / cuff / rim (outer wall, top lip, inner wall, bottom lip)."""
    m = loft([ring(r_out, y0, n, 1.0, sz, 0, cx, cz), ring(r_out + flare, y1, n, 1.0, sz, 0, cx, cz),
              ring(r_in + flare, y1, n, 1.0, sz, 0, cx, cz), ring(r_in, y0, n, 1.0, sz, 0, cx, cz)],
             col=col, loop=True)
    if inner_col:
        cs, ns = m.centroids(), m.normals()
        for i in range(len(m.F)):
            radial = np.array([cs[i][0] - cx, 0, cs[i][2] - cz])
            if np.dot(radial, ns[i]) < -0.2 * np.linalg.norm(radial):
                m.C[i] = tuple(inner_col)
    return m


def gorget(col, rim=None, inner=(16, 14, 16), y0=161, h=13, r=16.0, n=12):
    """Standing neck guard with a dark opening."""
    m = ring_band(r + 1.5, r - 2.5, y0, y0 + h, col, n, 0.8, flare=-0.8, inner_col=inner)
    if rim:
        m.add(ring_band(r + 1.4, r - 2.2, y0 + h - 2.2, y0 + h + 0.6, rim, n, 0.8, flare=-0.8, inner_col=inner))
    return m


def pauldron(col, side=1, size=1.0, layers=3, trim=None, spikes=0, spike_col=None, y=162, n=7, flat=0.78):
    """Angular shoulder guard: a domed cap plus overlapping lames below."""
    out = Mesh()
    for k in range(layers):
        r = (15.5 - k * 1.2) * size
        prof = [(r * 0.95, -r * 0.05), (r, r * 0.12), (r * 0.82, r * 0.55), (r * 0.42, r * 0.86), (0.01, r * 0.95)]
        d = lathe(prof, n, col=shade(col, 1 - 0.06 * k))
        d.scale(1.0, flat if k == 0 else flat * 0.62, 1.08)
        if trim:
            d.add(ring_band(r * 1.0 + 0.3, r * 0.82, -r * 0.08, r * 0.1, trim, n, 1.0).scale(1, 1, 1.08))
        d.rot('z', -(30 + 9 * k) * side).move(side * (30 + k * 3.2 * size), y - k * 6.5 * size, 0)
        out.add(d)
    for s in range(spikes):
        a = math.radians(-50 + 100 * (s / max(1, spikes - 1)))
        out.add(spike((side * (33 + 2 * size), y + 9 * size, 11 * math.sin(a)),
                      (side * 0.55, 1.0, 0.45 * math.sin(a)), 13 * size, 3.4, 4, spike_col or col))
    return out


def sleeve(col, side=1, length='short', r=7.6, cuff=None, bell=1.0, n=7):
    """Upper arm (short) or full arm (long) sleeve with optional cuff."""
    path = [(side * 31, 163, 0), (side * 36, 145, 0), (side * 38, 128, 2)]
    tap = [1.15, 1.0, 0.92]
    if length == 'long':
        path += [(side * 40, 110, 5), (side * 41, 95, 7)]
        tap += [0.95 * bell, 1.05 * bell]
    m = tube(path, r, n, col, taper=tap)
    if cuff:
        end, rr = path[-1], r * tap[-1]
        m.add(ring_band(rr * 1.18, rr * 0.8, end[1] - 3, end[1] + 4, cuff, n, 1.0, cx=end[0], cz=end[2],
                        inner_col=shade(col, 0.4)))
    return m


def faulds(col, trim=None, n_plates=8, y=97, length=16, flare=6, back=True, jag=0, seed=0):
    """Hip plates / tassets hanging from the waist, following the body."""
    rng = random.Random(seed)
    out = Mesh()
    for k in range(n_plates):
        t = 2 * math.pi * (k + 0.5) / n_plates
        if not back and math.sin(t) > 0.3:
            continue
        w = 2 * math.pi * 27 / n_plates * 0.62
        L = length + (rng.uniform(-jag, jag) if jag else 0)
        poly = [(-w / 2, 0), (w / 2, 0), (w / 2 * 1.08, -L), (0, -L - (4 if jag else 1.5)), (-w / 2 * 1.08, -L)]
        p = extrude(poly, 2.2, 0.6, 0.85, col=col)
        p.rot('x', -math.degrees(math.atan2(flare, length)))
        p.rot('y', math.degrees(t) - 270)
        out.add(p.move(*body_pt(t, y, 1.4)))
        if trim:
            tb = extrude([(-w / 2 - 0.4, 0.5), (w / 2 + 0.4, 0.5), (w / 2 + 0.4, -2.2), (-w / 2 - 0.4, -2.2)],
                         2.8, col=trim)
            tb.rot('x', -math.degrees(math.atan2(flare, length))).rot('y', math.degrees(t) - 270)
            out.add(tb.move(*body_pt(t, y - L + 1.5, 1.4 + flare * 0.9)))
    return out


def stud(size, col):
    """Low dome rivet head, facing +z (kept >= ~3 units: RS stores integer coordinates)."""
    return lathe([(size, 0), (size * 0.7, size * 0.35), (0.01, size * 0.45)], 5, col=col).rot('x', 90)


def studs(col, y, n=10, out=1.2, size=3.0, spread=2.4):
    m = Mesh()
    for k in range(n):
        t = FRONT + (k / (n - 1) - 0.5) * spread
        p = body_pt(t, y, out)
        s = stud(size, col).rot('y', -math.degrees(rel_angle(t)))
        m.add(s.move(*p))
    return m


def cuirass(base, *, trim=None, dark=None, lames=3, lame_col=None, lame_trim=False, pauldron_layers=3,
            pauldron_size=1.0, pauldron_col=None, gorget_col=None, gorget_rim=None, sleeves=None,
            sleeve_col=None, cuff_col=None, faulds_col=None, fauld_len=11, studs_col=None, spikes=0,
            spike_col=None, finish=None, ridge=True, n=12, belt_col=None, bulk=1.0, subdiv=0,
            breast_col=None, hem_trim=True):
    """Short-sleeved armoured torso (the player's own arms show and animate
    beneath the pauldrons). `finish(mesh)` recolours the plate surfaces
    (cracks, scales, crystal...) and must return the mesh."""
    dark = dark or shade(base, 0.6)
    lame_col = lame_col or base
    shell = body_shell(base, 96, 170, n, 0.0, bulk)
    for _ in range(subdiv):
        shell = shell.subdivide()
    plates = Mesh()
    # breastplate lower rim and abdominal lames, top to bottom
    plates.add(plate_band(125, 131, breast_col or trim or shade(base, 0.92), n, 0.5, 1.1, bulk))
    top = 125
    h = (top - 96) / max(1, lames)
    for k in range(lames):
        y1 = top - k * h
        plates.add(plate_band(y1 - h, y1 + 1.5, shade(lame_col, 1 - 0.04 * k), n, 0.9 + 0.3 * k, 1.1, bulk))
        last = k == lames - 1
        if trim and (lame_trim or (last and hem_trim)):
            plates.add(plate_band(y1 - h - 0.3, y1 - h + 2.2, trim, n, 0.9 + 0.3 * k + 1.2, 0.3, bulk))
    body = merge(shell, plates)
    for side in (1, -1):
        body.add(pauldron(pauldron_col or base, side, pauldron_size, pauldron_layers, trim, spikes,
                          spike_col or trim))
    if finish:
        body = finish(body)
    parts = [body]
    if ridge:
        parts.append(body_strip(FRONT, 130, 162, 3.0, trim or shade(base, 1.2), 0.5, 1.6, bulk=bulk))
    parts.append(gorget(gorget_col or base, gorget_rim if gorget_rim is not None else trim))
    if belt_col:
        parts.append(plate_band(94, 99, belt_col, n, 2.4, 0.2, bulk))
    if faulds_col is not False:
        parts.append(faulds(faulds_col or shade(base, 0.95), trim, 8, 97, fauld_len, 5))
    for side in (1, -1):
        if sleeves:
            parts.append(sleeve(sleeve_col or dark, side, sleeves, cuff=cuff_col or (trim if sleeves == 'long' else None)))
    if studs_col:
        h = (125 - 96) / max(1, lames)
        for k in range(lames):
            parts.append(studs(studs_col, 125 - k * h - h + 2.5, 7, 0.9 + 0.3 * k + 1.0))
        parts.append(studs(studs_col, 129, 7, 1.3))
    return merge(*parts)


# ------------------------------------------------------ head shells (grid)

def shell_grid(ys, r_of_y, n, col, *, opening=None, recess=0.55, inner_col=(14, 12, 14), sz=1.12,
               centre=HEAD, z_of_y=None, rx=1.0):
    """Lathe-like head shell on a regular (angle, height) grid. Vertices for
    which opening(rel_angle, y) is true are pushed inward, and every face that
    touches them is painted inner_col, so eye slits / face openings get crisp
    grid-aligned edges and real depth. n must be a multiple of 4 so a column
    sits exactly at the front."""
    rings, rec = [], []
    for y in ys:
        r = r_of_y(y)
        row, rrow = [], []
        for j in range(n):
            t = 2 * math.pi * j / n
            o = bool(opening and opening(rel_angle(t), y))
            k = recess if o else 1.0
            zo = z_of_y(y) if z_of_y else 0.0
            row.append((centre[0] + r * k * math.cos(t) * rx, y, centre[2] + zo - r * k * math.sin(t) * sz))
            rrow.append(o)
        rings.append(row)
        rec.append(rrow)
    m = loft(rings, col=col)
    flags = np.array([v for row in rec for v in row] + [False, False])
    for i, f in enumerate(m.F):
        if flags[f].any():
            m.C[i] = tuple(inner_col)
    return m


def helm_profile(top=1.0, r=22.5, flare=0.0, point=0.0):
    c = HEAD[1]

    def r_of_y(y):
        k = (y - c) / 25.0
        if k < -0.9:
            return r * (0.9 + flare * (-0.9 - k) * 3)
        if k <= 0.15:
            return r * (0.98 + 0.02 * (k + 0.9))
        q = min(1.0, (k - 0.15) / (0.85 * top + point * 0.3))
        return max(0.4, r * math.sqrt(max(0.0, 1 - q ** (2.2 - point))))
    ys = list(np.arange(c - 25, c + 4, 3.5)) + list(np.arange(c + 4, c + 25 * top + point * 8, 4.0))
    ys.append(c + 25 * top + point * 8)
    return ys, r_of_y


def helm(col, *, opening='slit', r=22.5, top=1.0, sz=1.12, inner=(12, 12, 14), flare=0.0, point=0.0, n=16):
    """Closed helm with a recessed opening: 'slit', 'T', 'face', 'eyes', 'Y' or None."""
    ys, r_of_y = helm_profile(top, r, flare, point)
    c = HEAD[1]

    def op(a, y):
        a = abs(a)
        if opening == 'slit':
            return a < 0.75 and c - 1 <= y <= c + 2.5
        if opening == 'T':
            return (a < 0.75 and c - 1 <= y <= c + 2.5) or (a < 0.1 and c - 18 <= y <= c + 2.5)
        if opening == 'Y':
            return (a < 0.1 and c - 18 <= y <= c - 4) or (0.05 < a < 0.62 and c - 4 <= y <= c + 2.5)
        if opening == 'face':
            return a < 0.62 and c - 18 <= y <= c + 4
        if opening == 'eyes':
            return 0.12 < a < 0.62 and c - 2 <= y <= c + 2.5
        return False
    ys = sorted(set([round(y, 2) for y in ys] + [c - 18, c - 4, c - 1, c + 2.5, c + 4]))
    return shell_grid(ys, r_of_y, n, col, opening=op if opening else None, inner_col=inner, sz=sz)


def horn(side, col, length=34, curve=1.0, r=4.5, base=(14, 205, 0), forward=0.0, n=6):
    p0 = np.array([side * base[0], base[1], base[2]])
    pts = bezier(p0, p0 + [side * 14, 6 * curve, forward * 0.4], p0 + [side * 24, 18 * curve, forward * 0.8],
                 p0 + [side * length * 0.62, length * 0.95 * curve, forward], 7)
    return tube(pts, r, n, col, taper=np.linspace(1, 0.06, len(pts)))


def feather(L, w, col, tip=None, bevel=True):
    poly = [(0, -w * 0.4), (L * 0.55, -w * 0.5), (L * 0.88, -w * 0.3), (L, 0), (L * 0.88, w * 0.3),
            (L * 0.55, w * 0.5), (0, w * 0.4)]
    f = extrude(poly, 1.8, 0.7 if bevel else 0, 0.55, col=col)
    if tip:
        paint_where(f, lambda c, nn: c[0] > L * 0.62, tip)
    return f


def wing(side, col, edge_col=None, size=1.0, at=(19, 196, -4), feathers=6, sweep_=1.0, spread=13, base_col=None):
    """Swept-back feathered wing; feathers fan from the root at `at`."""
    out = Mesh()
    for k in range(feathers):
        L = (30 - k * 2.6) * size
        f = feather(L, 6.5 * size, col, edge_col)
        f.rot('z', 25 + k * spread * sweep_).rot('y', -28)
        if side < 0:
            f = f.mirrored()
        out.add(f.move(side * at[0], at[1] - k * 0.8 * size, at[2] - k * 1.6 * size))
    root = sphere(4.5 * size, 6, 3, col=base_col or edge_col or col).move(side * at[0], at[1], at[2])
    return out.add(root)


def sunburst(col, rays=12, r_in=14, r_out=30, depth=4, centre=(0, 0, 0), alt=0.65, bevel=0.35):
    pts = []
    for k in range(rays * 2):
        a = math.pi * k / rays + math.pi / 2
        r = r_out if k % 2 == 0 else r_in
        if k % 4 == 2:
            r = r_in + (r_out - r_in) * alt
        pts.append((r * math.cos(a), r * math.sin(a)))
    return extrude(pts, depth, depth * bevel, 0.75, col=col).move(*centre)


def drape(col, y_top=172, y_bot=128, r_top=17, r_bot=36, n=14, jag=0, seed=0, back=1.0, folds=1.5):
    """Capelet/mantle hanging from the neck (open cone, double sided)."""
    rng = random.Random(seed)
    top = ring(r_top, y_top, n, 1.0, 0.85)
    mid = ring((r_top + r_bot) / 2 + 2, (y_top + y_bot) / 2 + 4, n, 1.0, 0.82)
    bot = []
    for j, p in enumerate(ring(r_bot, y_bot, n, 1.0, 0.78)):
        dy = (rng.uniform(-jag, -jag * 0.3) if j % 2 else -jag * 0.1) if jag else 0
        fz = folds * (1 if j % 2 else -1)
        extra = -(back - 1) * 12 if p[2] < 0 else 0
        bot.append((p[0] * (1 + fz * 0.02), p[1] + dy + extra, p[2] * (1 + fz * 0.03)))
    m = loft([top, mid, bot], cap_bottom=False, cap_top=False, col=col)
    return m.double()


# --------------------------------------------------------------------- legs

def leg(col, side, r=10.5, knee_col=None, flare=1.0, n=8, y_top=100):
    path = [(side * 12, y_top, 0), (side * 13, 75, 1), (side * 13, 52, 2), (side * 13, 30, 1),
            (side * 13, 8, 1)]
    m = tube(path, r, n, col, taper=[1.05, 0.97, 0.86, 0.8 * flare, 0.84 * flare])
    if knee_col:
        k = lathe([(6, -1), (7, 2), (4, 6), (0.01, 7)], 6, col=knee_col).rot('x', 90).move(side * 13, 52, 8)
        m.add(k)
    return m


def greave(col, side, trim=None, knee=True, foot=True, y_top=48, n=8, r=11.5):
    """Lower-leg plate (shin guard) with knee cop, optional sabaton."""
    out = lathe([(r * 0.78, 6), (r, 12), (r * 1.02, 26), (r * 0.9, y_top - 4), (r * 0.98, y_top)], n, col=col)
    out.move(side * 13, 0, 1)
    if knee:
        cop = [(-7, -6), (7, -6), (8, 2), (5, 8), (0, 10), (-5, 8), (-8, 2)]
        kp = extrude(cop, 3.2, 1.0, 0.75, col=col, dome=2.5)
        out.add(kp.move(side * 13, y_top + 2, 11))
        if trim:
            out.add(extrude(inset_poly(cop, 1.16), 1.6, col=trim).move(side * 13, y_top + 2, 9.6))
    if trim:
        out.add(ring_band(r * 0.98 + 0.4, r * 0.9, y_top - 2.5, y_top + 0.5, trim, n, 1.0, cx=side * 13, cz=1))
        out.add(ring_band(r * 0.82 + 0.6, r * 0.7, 6, 9, trim, n, 1.0, cx=side * 13, cz=1))
        out.add(body_free_strip((side * 13, 9, 1 + r * 0.95), (side * 13, y_top - 3, 1 + r * 1.0), 2.6, trim))
    if foot:
        sab = lathe([(7, 0), (8, 3), (6.5, 7)], 6, col=shade(col, 0.85)).scale(1, 1, 1.5).move(side * 13, 0, 6)
        out.add(sab)
    return out


def body_free_strip(p0, p1, width, col, th=1.4):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    h = np.cross(d, [0, 0, 1.0])
    if np.linalg.norm(h) < 1e-6:
        h = np.array([1.0, 0, 0])
    h /= np.linalg.norm(h)
    nn = np.cross(h, d)
    a = width / 2
    return loft([[p + h * a, p + h * a + nn * th, p - h * a + nn * th, p - h * a] for p in (p0, p1)], col=col)


def platelegs(base, trim=None, *, finish=None, seed=0, belt_col=None, thigh_col=None, greaves_=True,
              tasset_col=None, tasset_len=24):
    """Plated legs. finish() recolours the armour plates in one pass (one face
    budget); thighs in a separate thigh_col (cloth) are left unfinished."""
    armour, cloth = Mesh(), Mesh()
    for s in (1, -1):
        (cloth if thigh_col else armour).add(leg(thigh_col or base, s, 10.5, None).subdivide())
        if greaves_:
            armour.add(greave(base, s, trim, True, True))
    if finish:
        armour = finish(armour)
    hip = loft([ring(25.5, 90, 12, 1.0, 0.66), ring(27.5, 104, 12, 1.0, 0.64)], col=shade(base, 0.85))
    parts = [armour, cloth, hip, plate_band(98, 104, belt_col or trim or shade(base, 0.6), 12, 2.2, 0.2)]
    if tasset_col:
        parts.append(faulds(tasset_col, trim, 8, 99, tasset_len, 6))
    return merge(*parts)


def skirt(col, y_top=104, y_bot=40, r_top=27, r_bot=40, n=16, hem=None, jag=0, points=0, seed=0, waist=None,
          panels=(), panel_col=None, sz=0.68, rows=4):
    """Flared skirt / robe bottom. points>0 gives a zig-zag hem; panels are
    body-angle offsets (from the front) for vertical trim strips."""
    rng = random.Random(seed)
    rings = []
    for k in range(rows):
        f = k / (rows - 1)
        y = y_top + (y_bot - y_top) * f
        r = r_top + (r_bot - r_top) * (f ** 0.85)
        row = []
        for j in range(n):
            t = 2 * math.pi * j / n
            p = [r * math.cos(t), y, -r * math.sin(t) * sz]
            if k == rows - 1:
                if points:
                    p[1] -= jag if (j % 2 == 0) else 0
                elif jag:
                    p[1] -= rng.uniform(0, jag)
            row.append(p)
        rings.append(row)
    m = loft(rings, cap_bottom=False, cap_top=True, col=col).double()
    pc = panel_col or hem
    if hem:
        bot = rings[-1]
        up = [(p[0] * 0.985, p[1] + 5, p[2] * 0.985) for p in bot]
        hb = loft([[(p[0] * 1.012, p[1] - 0.2, p[2] * 1.012) for p in bot], [(p[0] * 1.012, p[1], p[2] * 1.012) for p in up]],
                  cap_bottom=False, cap_top=False, col=hem)
        m.add(hb.double())
    for a in panels:
        t = FRONT + a
        pts = []
        for k in range(rows):
            f = k / (rows - 1)
            y = y_top + (y_bot - y_top) * f
            r = (r_top + (r_bot - r_top) * (f ** 0.85)) + 0.9
            pts.append((r * math.cos(t), y, -r * math.sin(t) * sz))
        m.add(tube(pts, 1.6, 4, pc).scale(1, 1, 1))
    if waist:
        m.add(ring_band(r_top + 1.4, r_top - 1.5, y_top - 7, y_top + 0.5, waist, n, sz))
    return m


def gauntlet(base, side, trim=None, length=30, r=9.5, n=7, flare=1.15):
    """Forearm vambrace + hand, centred on the player's hand."""
    g = lathe([(r * 0.78, 0), (r * 0.86, 6), (r * 0.98, length * 0.6), (r * flare, length)], n, col=base)
    g = g.subdivide()
    g.rot('z', 4 * side).move(side * 40, 88, 7)
    out = merge(g, box(10, 9, 9, shade(base, 0.85)).move(side * 41, 84, 8))
    if trim:
        out.add(ring_band(r * flare + 0.5, r * flare - 1.5, 88 + length - 3, 88 + length + 0.5, trim, n, 1.0,
                          cx=side * 40 + 4 * side * 0.0, cz=7))
        out.add(ring_band(r * 0.9 + 0.6, r * 0.75, 90, 93, trim, n, 1.0, cx=side * 40, cz=7))
    return out


# --------------------------------------------------------------- cloth tops

def robe_top(base, trim=None, *, bell=1.5, hem_y=80, points=0, collar_col=None, seed=0, finish=None,
             lapels=True, sash=None, n=12, subdiv=1):
    """Long-sleeved robe/coat: body, flared coat skirt, standing collar, open
    front edged with trim, bell sleeves with wide cuffs."""
    shell = body_shell(base, 100, 170, n, 0.6, 1.04)
    coat = []
    for k, y in enumerate((100, 90, hem_y)):
        f = k / 2
        row = []
        for j in range(n):
            t = 2 * math.pi * j / n
            p = body_pt(t, 100, 0.6 + f * 4.5, 1.04)
            p[1] = y
            if k == 2 and points:
                p[1] -= points if j % 2 == 0 else 0
            row.append(p)
        coat.append(row)
    shell.add(loft(coat, cap_bottom=True, cap_top=False, col=base))
    for side in (1, -1):  # sleeves join the shell so one finish pass covers the whole garment
        shell.add(sleeve(base, side, 'long', 8.6, cuff=trim, bell=bell))
    for _ in range(subdiv):
        shell = shell.subdivide()
    if finish:
        shell = finish(shell)
    parts = [shell, gorget(collar_col or trim or base, None, shade(base, 0.35), 162, 11, 15.5, n)]
    for side in (1, -1):
        parts.append(pauldron(base, side, 0.82, 1, trim, n=8, flat=0.55))
    if trim:
        for dx in (-0.11, 0.11):
            parts.append(body_strip(FRONT + dx, hem_y + 1, 160, 3.6, trim, 1.4, 1.2, bulk=1.04))
        hem = []
        for y in (hem_y, hem_y + 4):
            hem.append([body_pt(2 * math.pi * j / n, 100, 0.6 + 4.5 + 0.7, 1.04) * [1, 0, 1] + [0, y, 0]
                        for j in range(n)])
        parts.append(loft(hem, cap_bottom=False, cap_top=False, col=trim).double())
        if lapels:
            for side in (1, -1):
                lp = extrude([(0, 0), (side * 10, 2), (side * 3, -22)], 1.6, col=trim)
                parts.append(lp.rot('x', -12).move(side * 2.5, 162, 18.5))
    if sash:
        parts.append(plate_band(100, 106, sash, n, 2.0, 0.3, 1.04))
    return merge(*parts)


def hood_surface(r=25.0, peak=10.0, lean=8.0):
    c = HEAD[1]

    def r_of_y(y):
        k = (y - c)
        if k < -10:
            return r * (0.98 + (-10 - k) * 0.004)
        if k < 6:
            return r
        q = min(1.0, (k - 6) / (24 + peak))
        return max(0.6, r * (1 - q ** 1.6))

    def z_of_y(y):
        k = y - c
        return -lean * max(0.0, (k - 8) / (22 + peak)) ** 2
    ys = list(np.arange(c - 26, c + 30 + peak + 0.1, 3.4))
    return ys, r_of_y, z_of_y


def hood(base, *, inner=(14, 12, 16), trim=None, mantle=True, peak=10, lean=10, seed=0, mask=None,
         finish=None, n=16, open_w=0.66, mantle_col=None, jag=6):
    """Cowl with a real recessed face opening (arched top), optional trim
    along the opening, face mask, and shoulder mantle."""
    c = HEAD[1]
    ys, r_of_y, z_of_y = hood_surface(25.5, peak, lean)
    ys = sorted(set([round(y, 2) for y in ys] + [c - 26, c + 6]))

    def op(a, y):
        w = open_w if y <= c + 1 else open_w * max(0.0, 1 - (y - c - 1) / 9.0)
        return abs(a) < w and c - 26 <= y <= c + 9
    h = shell_grid(ys, r_of_y, n, base, opening=op, recess=0.5, inner_col=inner, sz=1.1,
                   centre=HEAD + [0, 0, -1], z_of_y=z_of_y)
    if finish:
        h = finish(h)
    jitter(h, 0.04, seed)
    parts = [h]
    if trim:
        path = []
        for a, y in ([(-open_w - 0.12, yy) for yy in np.arange(c - 25, c + 1, 4)] +
                     [(-open_w * (1 - k / 4) - 0.1, c + 1 + 9 * k / 4) for k in range(5)] +
                     [(open_w * (k / 4) + 0.1, c + 10 - 9 * k / 4) for k in range(5)] +
                     [(open_w + 0.12, yy) for yy in np.arange(c, c - 26, -4)]):
            t = FRONT + a
            r = r_of_y(y) * 1.02
            path.append((r * math.cos(t), y, HEAD[2] - 1 + z_of_y(y) - r * math.sin(t) * 1.1))
        parts.append(tube(path, 1.9, 4, trim, up=(0, 0, 1)))
    if mask:
        rows = []
        for y in (c - 24, c - 14, c - 5):
            row = []
            for k in range(7):
                a = -open_w * 0.95 + 2 * open_w * 0.95 * k / 6
                t = FRONT + a
                r = r_of_y(y) * (0.8 if y > c - 6 else 0.84)
                row.append((r * math.cos(t), y, HEAD[2] - 1 - r * math.sin(t) * 1.1 + (2 if k == 3 else 0)))
            rows.append(row)
        parts.append(loft(rows, cap_bottom=False, cap_top=False, closed_ring=False, col=mask).double())
    if mantle:
        parts.append(drape(mantle_col or shade(base, 0.94), 170, 142, 18, 38, n, jag=jag, seed=seed))
    return merge(*parts)


def cape(base, y_top=168, y_bot=36, w_top=24, w_bot=50, jag=12, n=11, seed=0, folds=4.0, rows=6, points=False,
         double=True):
    """Back-hanging cloak, folded, ragged hem. double=False returns the single
    outward-facing sheet (recolour it, then call .double())."""
    rng = random.Random(seed)
    rings = []
    for r in range(rows):
        t = r / (rows - 1)
        y = y_top + (y_bot - y_top) * t
        w = w_top + (w_bot - w_top) * t ** 0.8
        z0 = -17 - 9 * t
        row = []
        for j in range(n):
            u = j / (n - 1) * 2 - 1
            dy = 0
            if r == rows - 1 and jag:
                dy = (-jag if j % 2 else -jag * 0.15) if points else -rng.uniform(0, jag)
            fold = folds * t * math.sin(u * math.pi * 2.5)
            row.append((u * w, y + dy, z0 + abs(u) ** 1.6 * 16 * (1 - 0.4 * t) + fold))
        rings.append(row)
    m = loft(rings, cap_bottom=False, cap_top=False, closed_ring=False, col=base)
    if np.mean(m.normals()[:, 2]) > 0:
        m.flip()
    m = m.subdivide()
    return m.double() if double else m


# ----------------------------------------------------------------- weapons

def grip(length=20, r=2.8, col=(80, 52, 32), wrap=None, pommel=None, pommel_r=4.0, pommel_kind='ball', n=6):
    """Sword grip below the guard (y from -length to 0), wrapped, with pommel."""
    m = prism(r, r * 0.92, length, n, -length, col=col)
    if wrap:
        k = 0
        y = -length + 1.5
        while y < -1.5:
            m.add(prism(r * 1.14, r * 1.1, 1.8, n, y, col=wrap).rot('z', 8 if k % 2 else -8, about=(0, y, 0)))
            y += 3.4
            k += 1
    if pommel:
        if pommel_kind == 'spike':
            m.add(lathe([(pommel_r * 0.6, 0), (pommel_r, -pommel_r * 0.6), (0.01, -pommel_r * 2.2)], n, col=pommel)
                  .move(0, -length, 0))
        else:
            m.add(gem_like(pommel_r, pommel).move(0, -length - pommel_r * 0.7, 0))
    return m


def gem_like(r, col, n=6):
    return lathe([(0.01, -r), (r * 0.9, -r * 0.2), (r, r * 0.2), (0.01, r)], n, col=col)


def wrapped_handle(length, r, col, wrap=None, y0=0.0, cap=None, pommel=None, pommel_kind='spike', n=6,
                   wrap_from=0.1, wrap_to=0.75):
    """Haft from y0 upward with leather wrap rings, ferrules and pommel."""
    m = prism(r, r * 0.95, length, n, y0, col=col)
    if wrap:
        y = y0 + length * wrap_from
        k = 0
        while y < y0 + length * wrap_to:
            m.add(prism(r * 1.16, r * 1.12, 2.0, n, y, col=wrap).rot('z', 9 if k % 2 else -9, about=(0, y, 0)))
            y += 3.6
            k += 1
    if cap:
        m.add(prism(r * 1.35, r * 1.25, 4, n, y0 - 1, col=cap))
        m.add(prism(r * 1.3, r * 1.3, 3, n, y0 + length - 3, col=cap))
    if pommel:
        if pommel_kind == 'spike':
            m.add(lathe([(r * 1.2, 0), (r * 1.4, -2.5), (0.01, -r * 3.2)], n, col=pommel).move(0, y0 - 1, 0))
        else:
            m.add(gem_like(r * 1.5, pommel, n).move(0, y0 - r * 1.2, 0))
    return m


def blade(length, width, col, *, curve=0.0, tip=0.18, thick=2.6, edge_col=None, base_y=0, steps=10,
          taper_end=0.35, belly=0.35, hook=0.0):
    """Diamond-section blade along +y. curve bends it toward +x (scimitar),
    belly widens the middle, hook bends the last segment back."""
    pts, sc = [], []
    for i in range(steps + 1):
        t = i / steps
        y = base_y + length * t
        x = curve * length * (t ** 2) * 0.35 - hook * length * max(0, t - 0.8) ** 2 * 6
        pts.append((x, y, 0))
        w = width * (1 - t * (1 - taper_end)) if t < 1 - tip else width * taper_end * (1 - t) / tip
        if curve or belly:
            w *= 1 + (belly if not curve else max(belly, 0.35)) * math.sin(math.pi * min(t, 0.95))
        sc.append((max(w, 0.25), 1.0 if t < 1 - tip else max(0.2, (1 - t) / tip)))
    sec = [(-0.5, 0), (-0.18, thick / 2), (0.18, thick / 2), (0.5, 0), (0.18, -thick / 2), (-0.18, -thick / 2)]
    m = sweep(pts, sec, up=(0, 0, 1), col=col, scales=sc)
    if edge_col:
        m = m.subdivide()
        ns = m.normals()
        for i in range(len(m.F)):
            if abs(ns[i][2]) < 0.75:
                m.C[i] = edge_col
    return m


def crossguard(w, col, h=4.5, d=6, flare=0.0, curl=0.0, n=5):
    if not flare and not curl:
        return box(w, h, d, col)
    pts = bezier((-w / 2, curl, 0), (-w / 4, -flare, 0), (w / 4, -flare, 0), (w / 2, curl, 0), 8)
    return tube(pts, h / 2, n, col, taper=[1.3, 1.1, 1, 0.9, 0.85, 0.9, 1, 1.1, 1.3])


def axe_head(poly, depth, col, edge=None, at=(0, 0, 0), rot=0, edge_w=5):
    m = extrude(poly, depth, depth * 0.38, 0.7, col=col).subdivide()
    if edge:
        cs = m.centroids()
        xmax = max(p[0] for p in poly)
        for i, c in enumerate(cs):
            if c[0] > xmax - edge_w:
                m.C[i] = edge
    return m.rot('z', rot).move(*at)


def crescent(r_out=24, r_in=16, span=150, offset=8, steps=10):
    """Crescent axe-blade outline opening toward -x (the haft)."""
    a0, a1 = math.radians(-span / 2), math.radians(span / 2)
    outer = [(offset + r_out * math.cos(a), r_out * math.sin(a)) for a in np.linspace(a0, a1, steps)]
    inner = [(offset - 4 + r_in * 0.55 * math.cos(a), r_in * 0.62 * math.sin(a)) for a in np.linspace(a1 * 0.8, a0 * 0.8, steps // 2)]
    return outer + inner


def staff_shaft(length, col, r=3.0, ring_col=None, n=6, y0=None, wrap=None, pommel=None):
    y0 = -length * 0.3 if y0 is None else y0
    m = wrapped_handle(length, r, col, wrap, y0, None, pommel, 'spike', n, 0.12, 0.4)
    if ring_col:
        for f in (0.0, 0.42, 0.85):
            m.add(prism(r * 1.45, r * 1.35, 3.2, n, y0 + length * f, col=ring_col))
    return m


def bow_limbs(col, length=110, depth=24, r=3.6, string_col=(200, 190, 170), grip_col=None, recurve=0.0,
              steps=12, n=6, thick_mid=1.0):
    """Bow in the xy plane, string on the -x side, grip at origin."""
    pts = []
    for i in range(steps + 1):
        t = i / steps * 2 - 1
        y = t * length / 2
        x = depth * (1 - t * t) - depth
        x += recurve * max(0.0, abs(t) - 0.7) ** 2 * 120
        pts.append((x, y, 0))
    tap = [(0.5 + 0.5 * (1 - abs(i / steps * 2 - 1)) ** 0.7) * (thick_mid if abs(i / steps * 2 - 1) < 0.2 else 1)
           for i in range(steps + 1)]
    m = tube(pts, r, n, col, taper=tap)
    top, bot = np.array(pts[-1]), np.array(pts[0])
    m.add(tube([bot + [-r * 0.4, 0, 0], top + [-r * 0.4, 0, 0]], 0.6, 3, string_col))
    if grip_col:
        m.add(prism(r * 1.3, r * 1.3, 16, n, -8, col=grip_col))
        for y in (-9, 7):
            m.add(prism(r * 1.45, r * 1.45, 2.4, n, y, col=shade(grip_col, 0.7)))
    return m, pts


def crossbow(stock_col, limb_col, *, string_col=(200, 190, 170), trim=None, length=74, span=70, limb_r=3.4,
             stock_w=9, recurve=0.0):
    """Crossbow lying along z (tip toward +z), limbs in the xz plane."""
    prof = [(-stock_w / 2, -length * 0.55), (stock_w / 2, -length * 0.55), (stock_w * 0.6, -length * 0.2),
            (stock_w * 0.42, length * 0.45), (-stock_w * 0.42, length * 0.45), (-stock_w * 0.6, -length * 0.2)]
    stock = extrude(prof, 8, 2.0, 0.78, col=stock_col).rot('x', 90)  # profile +y -> +z (forward)
    butt = extrude([(-6, 0), (6, 0), (7, 18), (-7, 18)], 10, 2.5, 0.8, col=shade(stock_col, 0.85)) \
        .rot('x', 90).move(0, -3, -length * 0.55 - 16)
    trig = box(2.4, 9, 3.4, (60, 60, 64)).move(0, -8, -length * 0.08)
    rail = box(3, 2, length * 0.9, shade(stock_col, 0.75)).move(0, 4.2, 0)
    xs = np.linspace(-span / 2, span / 2, 11)
    pts = [(x, 0, length * 0.4 - 12 * abs(2 * x / span) ** 1.6 + recurve * max(0, abs(2 * x / span) - 0.75) * 30)
           for x in xs]
    tap = [0.55, 0.7, 0.85, 0.95, 1.05, 1.15, 1.05, 0.95, 0.85, 0.7, 0.55]
    limbs = tube(pts, limb_r, 6, limb_col, taper=tap, up=(0, 1, 0))
    nock = (0, 0.5, length * 0.02)
    string = merge(tube([pts[0], nock], 0.55, 3, string_col), tube([nock, pts[-1]], 0.55, 3, string_col))
    parts = [stock, butt, trig, rail, limbs, string]
    if trim:
        parts.append(box(stock_w + 3, 4, 6, trim).move(0, 0, length * 0.4))
        parts.append(box(stock_w + 2, 3, 4, trim).move(0, 0, -length * 0.35))
    return merge(*parts), pts


# ------------------------------------------------------------------ shields

def kite_poly(w=44, h=60):
    return [(0, -h * 0.62), (w * 0.32, -h * 0.3), (w * 0.5, h * 0.12), (w * 0.47, h * 0.34),
            (w * 0.22, h * 0.4), (0, h * 0.44), (-w * 0.22, h * 0.4), (-w * 0.47, h * 0.34),
            (-w * 0.5, h * 0.12), (-w * 0.32, -h * 0.3)]


def heater_poly(w=46, h=56, top_peak=0.0):
    pts = [(-w / 2, h * 0.45), (0, h * 0.45 + top_peak), (w / 2, h * 0.45)]
    for k in range(1, 8):
        t = k / 8
        pts.append((w / 2 * math.cos(t * math.pi / 2) ** 0.8, h * 0.45 - h * 1.0 * math.sin(t * math.pi / 2)))
    pts.append((0, -h * 0.55))
    for k in range(7, 0, -1):
        t = k / 8
        pts.append((-w / 2 * math.cos(t * math.pi / 2) ** 0.8, h * 0.45 - h * 1.0 * math.sin(t * math.pi / 2)))
    return pts


def inset_poly(poly, k):
    P = np.array(poly, float)
    c = P.mean(0)
    return [tuple(c + (p - c) * k) for p in P]


def shield(poly, col, depth=6, dome=4, rim=None, rim_k=0.88, rim_depth=None):
    """Shield board; with rim, a raised border frame surrounds a domed field."""
    if not rim:
        return extrude(poly, depth, depth * 0.3, 0.86, col=col, dome=dome)
    field = extrude(inset_poly(poly, rim_k), depth, depth * 0.25, 0.9, col=col, dome=dome)
    back = extrude(poly, depth * 0.8, depth * 0.3, 0.92, col=rim).move(0, 0, -depth * 0.25)
    # frame: outline band slightly proud of the field
    P = np.array(poly, float)
    Pi = np.array(inset_poly(poly, rim_k - 0.02), float)
    rd = rim_depth or depth * 0.6
    rings = [[(p[0], p[1], -rd * 0.4) for p in P], [(p[0], p[1], depth / 2 + rd * 0.55) for p in P],
             [(p[0], p[1], depth / 2 + rd * 0.55) for p in Pi], [(p[0], p[1], depth / 2 - 1) for p in Pi]]
    frame = loft(rings, col=rim, loop=True)
    return merge(back, field, frame)


# -------------------------------------------------------------- jewellery

def necklace_chain(col, w=24, drop=40, link=3.6, top=None):
    pts = bezier((-w, drop, -2), (-w * 0.9, 4, 0), (w * 0.9, 4, 0), (w, drop, -2), 16)
    return chain(pts, link * 1.25, col, thick=0.34)


def rope(path, r, col, alt=None, n=5, twist=3.2):
    """Twisted rope: alternating colour bands along a path."""
    m = tube(path, r, n, col)
    m = m.subdivide()
    if alt:
        cs = m.centroids()
        P = np.asarray(path, float)
        for i, c in enumerate(cs):
            d = np.linalg.norm(P - c, axis=1)
            k = int(np.argmin(d))
            ang = math.atan2(c[2] - P[k][2], c[0] - P[k][0])
            if int((k * 2.0 + ang / math.pi * 2) // 1) % 2:
                m.C[i] = alt
    return m


def star_poly(points, r_out, r_in, phase=math.pi / 2):
    return [((r_out if k % 2 == 0 else r_in) * math.cos(phase + math.pi * k / points),
             (r_out if k % 2 == 0 else r_in) * math.sin(phase + math.pi * k / points)) for k in range(points * 2)]


def star3d(points, r_out, r_in, depth, col):
    """Faceted star (raised centre ridges), like an engraved/applied star."""
    P = star_poly(points, r_out, r_in)
    V = [(x, y, 0) for x, y in P] + [(0, 0, depth), (0, 0, -depth * 0.3)]
    n = len(P)
    F = [(j, (j + 1) % n, n) for j in range(n)] + [((j + 1) % n, j, n + 1) for j in range(n)]
    return Mesh(V, F).paint(col).orient_closed()
