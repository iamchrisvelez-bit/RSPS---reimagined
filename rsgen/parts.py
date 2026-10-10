"""Reusable equipment templates fitted to the standard player body.

Body landmarks (authoring units, y up, feet at 0, facing +z):
  head centre (0,190,2) r~20 | neck y172 | shoulders y165 x+-30
  chest y140 | waist y105 | hips y95 | knees y50 | hands y~95 x+-40
Weapons/shields/jewellery are built in item space (grip or centre at origin).
"""
import math
import random
import numpy as np
from .geom import (Mesh, merge, loft, lathe, ring, prism, box, sphere, spike,
                   sweep, tube, bezier, torus, chain, extrude, shade, mix)

HEAD = np.array([0.0, 190.0, 2.0])


# ------------------------------------------------------------- colour helpers

def jitter(m, amt, seed=0):
    rng = random.Random(seed)
    m.C = [shade(c, 1 + rng.uniform(-amt, amt)) if not g else c for c, g in zip(m.C, m.G)]
    return m


def cracks(m, seeds, width, col, glow=True, seed=1, base=None):
    """Voronoi-edge crack pattern (lava veins, magic veins)."""
    rng = random.Random(seed)
    cs = m.centroids()
    if len(cs) == 0:
        return m
    S = cs[[rng.randrange(len(cs)) for _ in range(seeds)]]
    for i, c in enumerate(cs):
        d = np.sort(np.linalg.norm(S - c, axis=1))
        if len(d) > 1 and d[1] - d[0] < width:
            m.C[i], m.G[i] = col, glow
        elif base is not None:
            m.C[i] = base
    return m


def bands(m, axis, period, cols, offset=0.0):
    cs = m.centroids()
    for i, c in enumerate(cs):
        if not m.G[i]:
            m.C[i] = cols[int(math.floor((c[axis] + offset) / period)) % len(cols)]
    return m


def scales_pattern(m, cols, period=7.0):
    cs = m.centroids()
    for i, c in enumerate(cs):
        a = math.atan2(c[2], c[0])
        k = int(math.floor(c[1] / period)) + int(math.floor(a * 6 + (c[1] // period) * 0.5))
        m.C[i] = cols[k % len(cols)]
    return m


# ------------------------------------------------------------------- torso

def torso_rings(n=10, wide=1.0, deep=1.0, waist_y=100, flare=0.0, bulk=1.0):
    spec = [(waist_y - 2, 26 + flare, 16), (118, 28, 17.5), (138, 31.5, 19.5), (155, 33.5, 18.5),
            (165, 27, 15), (171, 13, 10.5)]

    def front(t):  # chest a touch fuller in front
        return 1.0 + 0.08 * max(0.0, -math.sin(t))

    rings = []
    for y, w, d in spec:
        w, d = w * wide * bulk, d * deep * bulk
        pts = []
        for j in range(n):
            t = 2 * math.pi * j / n + math.pi / n
            f = front(t) if y < 165 else 1.0
            pts.append((w * math.cos(t), y, -d * math.sin(t) * f))
        rings.append(pts)
    return rings


def torso(col, n=10, **kw):
    return loft(torso_rings(n, **kw), col=col)


def pauldron(col, side=1, size=1.0, layers=2, trim=None, spikes=0, spike_col=None, y=163):
    out = Mesh()
    for k in range(layers):
        r = (15 - k * 2.2) * size
        d = lathe([(r, 0), (r * 0.92, r * 0.45), (r * 0.55, r * 0.85), (0.01, r * 1.0)], 8, col=col)
        d.scale(1.05, 0.75, 1.0).rot('z', -28 * side).move(side * (31 + k * 2.5) * size ** 0.3, y - k * 7, 0)
        out.add(d)
        if trim and k == 0:
            out.add(torus(r * 1.0, 1.5, 10, 3, trim).rot('x', 90).scale(1.05, 1, 1)
                    .rot('z', -28 * side).move(side * 31 * size ** 0.3, y, 0))
    for s in range(spikes):
        a = math.radians(-40 + 80 * (s / max(1, spikes - 1)))
        out.add(spike((side * (36 + 3 * size), y + 6, 9 * math.sin(a)),
                      (side * 0.6, 1.0, 0.5 * math.sin(a)), 12 * size, 3.2, 4, spike_col or col))
    return out


def arm(col, side=1, r=7.5, cuff=None, hand=False, sleeve_flare=1.0):
    path = [(side * 33, 162, 0), (side * 37, 140, 0), (side * 39, 124, 2), (side * 40, 108, 5),
            (side * 40, 96, 7)]
    tap = [1.15, 1.0, 0.92, 0.88 * sleeve_flare, 0.86 * sleeve_flare]
    m = tube(path, r, 6, col, taper=tap, up=(0, 0, 1))
    if cuff:
        m.add(prism(r * 1.15, r * 1.25, 9, 6, col=cuff).move(side * 40, 96, 7))
    return m


def belt(col, y=103, h=6, buckle=None, wide=1.0):
    m = loft([ring(27.5 * wide, y, 10, 1.0, 0.64), ring(28.5 * wide, y + h, 10, 1.0, 0.64)], col=col)
    if buckle:
        m.add(box(8, 8, 3, buckle).move(0, y + h / 2, 18.8 * wide))
    return m


def collar(col, r=13.5, y=168, h=6):
    return lathe([(r, y), (r + 1.5, y + h * 0.6), (r - 1, y + h)], 10, 1.0, 0.82, col=col)


def tassets(col, trim=None, n=5, y=100, length=30, spread=1.0, jag=False, back=True):
    """Hanging armour flaps around the waist."""
    out = Mesh()
    ks = range(n) if back else range(n // 2 + 1)
    for k in ks:
        a = math.pi * (0.15 + 0.7 * k / max(1, n - 1)) if not back else 2 * math.pi * k / n + math.pi / 2
        x, z = 30 * math.cos(a) * spread, 20 * math.sin(a) * spread
        poly = [(-8, 0), (8, 0), (9, -length), (0, -length - (6 if jag else 2)), (-9, -length)]
        p = extrude(poly, 2.5, col=col)
        p.rot('x', -8).rot('y', -math.degrees(a) + 90).move(x, y, z)
        out.add(p)
        if trim:
            t = box(17, 2.4, 3, trim).rot('y', -math.degrees(a) + 90).move(x, y - 1, z)
            out.add(t)
    return out


def rivets(m_out, col, y, n=8, r=29.5, d=19.5, size=2.2):
    for k in range(n):
        t = math.pi * (0.1 + 0.8 * k / (n - 1))
        m_out.add(box(size, size, size, col).move(r * math.cos(t), y, d * math.sin(t)))
    return m_out


def platebody(base, dark=None, trim=None, *, pattern='plates', arms=True, pauldron_layers=2,
              pauldron_size=1.0, skirt=False, skirt_col=None, seed=0, accent=None, spikes=0,
              glow_col=None, collar_col=None, belt_col=None, sleeve_col=None, bulk=1.0):
    dark = dark or shade(base, 0.6)
    t = torso(base, 12, bulk=bulk)
    if pattern in ('scale', 'lava', 'veins', 'filigree', 'crystal', 'chain'):
        t = t.subdivide()
        if pattern == 'lava':
            t = t.subdivide()
    if pattern == 'plates':
        bands(t, 1, 13, [base, shade(base, 0.86)], offset=3)
    elif pattern == 'scale':
        scales_pattern(t, [base, shade(base, 0.78), shade(base, 1.12)], 6.5)
    elif pattern == 'lava':
        cracks(t, 50, 1.3, glow_col or (255, 120, 30), True, seed)
    elif pattern == 'veins':
        cracks(t, 30, 1.1, accent or (140, 70, 220), True, seed)
    elif pattern == 'filigree':
        cracks(t, 40, 1.6, accent or shade(base, 0.72), False, seed)
    elif pattern == 'crystal':
        jitter(t, 0.22, seed)
    elif pattern == 'chain':
        cs = t.centroids()
        for i, c in enumerate(cs):
            t.C[i] = base if (int(c[1] / 3) + int((c[0] + 60) / 3)) % 2 else dark
    jitter(t, 0.05, seed + 1)
    parts = [t]
    # breastplate ridge down the centre
    parts.append(box(3, 46, 3, trim or shade(base, 1.15)).rot('x', -6).move(0, 135, 20.5 * bulk))
    parts.append(collar(collar_col or trim or dark))
    parts.append(belt(belt_col or trim or dark, buckle=trim or accent, wide=bulk))
    for side in (1, -1):
        parts.append(pauldron(base, side, pauldron_size, pauldron_layers, trim, spikes,
                              accent or trim))
        if arms:
            parts.append(arm(sleeve_col or dark, side, cuff=trim or base))
    if skirt:
        parts.append(tassets(skirt_col or base, trim, 7, 101, 26))
    return merge(*parts)


# -------------------------------------------------------------------- helms

def helm_shell(col, r=22.5, sz=1.1, n=10, top=1.0):
    c = HEAD
    prof = [(r * 0.86, c[1] - 22), (r * 0.98, c[1] - 12), (r, c[1]), (r * 0.94, c[1] + 10 * top),
            (r * 0.72, c[1] + 18 * top), (r * 0.36, c[1] + 23 * top), (0.01, c[1] + 25 * top)]
    return lathe(prof, n, 1.0, sz, col=col).move(0, 0, c[2]).subdivide()


def visor(m, col, kind='slit', y=192, z_min=10):
    """Paint the eye slit / face opening on the front of a helm."""
    def fn(c, n, i):
        rel = c - HEAD
        if c[2] < z_min:
            return None
        if kind == 'slit' and abs(rel[1] - (y - HEAD[1])) < 3.2:
            return col
        if kind == 'T' and (abs(rel[1] - 2) < 3.2 or (abs(rel[0]) < 3.2 and -14 < rel[1] < 2)):
            return col
        if kind == 'grille' and -12 < rel[1] < 5 and abs(rel[0]) < 13 and (int(rel[0] + 30) // 3) % 2 == 0:
            return col
        if kind == 'face' and -16 < rel[1] < 6 and abs(rel[0]) < 12:
            return col
        return None
    return m.paint_fn(fn)


def horn(side, col, length=34, curve=1.0, r=4.5, base=(14, 205, 0)):
    p0 = np.array([side * base[0], base[1], base[2]])
    pts = bezier(p0, p0 + [side * 14, 10 * curve, -2], p0 + [side * 26, 22 * curve, -6],
                 p0 + [side * length * 0.7, length * 0.9 * curve, -12], 6)
    return tube(pts, r, 5, col, taper=np.linspace(1, 0.08, len(pts)))


def wing(side, col, edge_col=None, size=1.0, at=(19, 196, -4), feathers=5):
    out = Mesh()
    for k in range(feathers):
        L = (26 - k * 3.2) * size
        poly = [(0, -2.5), (L * 0.8, -3.5), (L, 0), (L * 0.8, 3.5), (0, 2.5)]
        f = extrude(poly, 2.0, 0.6, 0.6, col=mix(col, edge_col or col, k / max(1, feathers - 1)))
        f.rot('z', 15 + k * 14).rot('y', -18)
        if side < 0:
            f = f.mirrored()
        out.add(f.move(side * at[0], at[1] - k * 1.5, at[2] - k * 1.8))
    return out


def sunburst(col, rays=12, r_in=14, r_out=30, depth=4, centre=(0, 0, 0), alt=0.65):
    pts = []
    for k in range(rays * 2):
        a = math.pi * k / rays + math.pi / 2
        r = r_out if k % 2 == 0 else r_in
        if k % 4 == 2:
            r = r_in + (r_out - r_in) * alt
        pts.append((r * math.cos(a), r * math.sin(a)))
    return extrude(pts, depth, depth * 0.3, 0.8, col=col).move(*centre)


def drape(col, y_top=172, y_bot=128, r_top=17, r_bot=34, n=12, back_only=False, jag=0, seed=0):
    """Capelet/mantle hanging from the neck (open cone, double sided)."""
    rng = random.Random(seed)
    top = ring(r_top, y_top, n, 1.0, 0.85)
    bot = []
    for j, p in enumerate(ring(r_bot, y_bot, n, 1.0, 0.75)):
        dy = (rng.uniform(-jag, 0) if j % 2 else -jag) if jag else 0
        bot.append((p[0], p[1] + dy, p[2]))
    m = loft([top, ring((r_top + r_bot) / 2 + 2, (y_top + y_bot) / 2 + 4, n, 1.0, 0.82), bot],
             cap_bottom=False, cap_top=False, col=col)
    return m.double()


# --------------------------------------------------------------------- legs

def leg(col, side, r=10.5, knee_col=None, flare=1.0):
    path = [(side * 12, 100, 0), (side * 13, 75, 1), (side * 13, 52, 2), (side * 13, 30, 1),
            (side * 13, 10, 1)]
    m = tube(path, r, 7, col, taper=[1.05, 0.96, 0.85, 0.8 * flare, 0.82 * flare])
    if knee_col:
        m.add(sphere(6.5, 6, 3, 0.8, knee_col).move(side * 13, 53, 9))
    return m


def platelegs(base, trim=None, *, pattern='plates', knee=True, seed=0, belt_col=None, glow_col=None):
    parts = []
    for s in (1, -1):
        l = leg(base, s, knee_col=(trim or shade(base, 1.1)) if knee else None)
        if pattern == 'scale':
            l = l.subdivide()
            scales_pattern(l, [base, shade(base, 0.78), shade(base, 1.12)], 6)
        elif pattern == 'plates':
            bands(l, 1, 11, [base, shade(base, 0.85)])
        elif pattern == 'lava':
            l = l.subdivide().subdivide()
            cracks(l, 24, 1.1, glow_col or (255, 120, 30), True, seed + s)
        jitter(l, 0.05, seed + s)
        parts.append(l)
    hip = loft([ring(26, 92, 10, 1.0, 0.68), ring(28, 106, 10, 1.0, 0.66)], col=shade(base, 0.9))
    parts += [hip, belt(belt_col or trim or shade(base, 0.6), 103, 5, trim)]
    return merge(*parts)


def skirt(col, y_top=106, y_bot=40, r_top=28, r_bot=40, n=12, hem=None, jag=0, seed=0, trim=None,
          front_panel=None):
    rng = random.Random(seed)
    rings = [ring(r_top, y_top, n, 1.0, 0.66), ring((r_top + r_bot) / 2, (y_top + y_bot) / 2, n, 1.0, 0.66)]
    bot = []
    for j, p in enumerate(ring(r_bot, y_bot, n, 1.0, 0.68)):
        dy = (-jag if j % 2 == 0 else -jag * 0.25 * rng.random()) if jag else 0
        bot.append((p[0], p[1] + dy, p[2]))
    rings.append(bot)
    m = loft(rings, cap_bottom=False, cap_top=True, col=col).double()
    if hem:
        m.add(loft([ring(r_bot + 0.6, y_bot + 1, n, 1.0, 0.69), ring(r_bot - 0.6, y_bot + 6, n, 1.0, 0.68)],
                   cap_bottom=False, cap_top=False, col=hem).double())
    if trim:
        m.add(belt(trim, y_top - 5, 5))
    if front_panel:
        L = y_top - y_bot - 6
        m.add(extrude([(-8, 0), (8, 0), (10, -L), (0, -L - 6), (-10, -L)], 2, col=front_panel)
              .rot('x', -10).move(0, y_top - 4, 20))
    return m


def greaves(base, trim=None, seed=0):
    out = Mesh()
    for s in (1, -1):
        g = lathe([(9, 0), (11.5, 6), (12, 22), (10.5, 40), (11.5, 46)], 8, 1.0, 1.0, col=base)
        g.move(s * 13, 2, 1)
        out.add(g)
        out.add(box(11, 6, 16, shade(base, 0.85)).move(s * 13, 3, 6))  # sabaton
        out.add(extrude([(-6, 0), (6, 0), (4, 14), (0, 18), (-4, 14)], 2.5, col=trim or base)
                .move(s * 13, 32, 11))  # knee guard
        if trim:
            out.add(prism(12.3, 12.3, 2.5, 8, col=trim).move(s * 13, 44, 1))
    return jitter(out, 0.05, seed)


def gauntlets(base, trim=None, claws=False, glow=None, seed=0, spikes=False):
    out = Mesh()
    for s in (1, -1):
        g = lathe([(7, 0), (8.5, 6), (9.5, 20), (11, 30)], 7, col=base)
        g.move(0, -6, 0).rot('z', 4 * s).move(s * 40, 94, 7)
        if glow:
            g = g.subdivide().subdivide()
            cracks(g, 14, 1.0, glow, True, seed + s)
        out.add(g)
        out.add(box(10, 10, 9, shade(base, 0.85)).move(s * 41, 86, 8))  # fist
        if trim:
            out.add(prism(11.3, 11.6, 3, 7, col=trim).move(s * 40, 117, 7))
        if claws:
            for k in range(3):
                out.add(spike((s * (38 + k * 2.5), 82, 10), (s * 0.1, -1, 0.3), 9, 1.6, 3, claws))
        if spikes:
            out.add(spike((s * 49, 104, 7), (s, 0.3, 0), 9, 2.5, 4, trim or base))
    return out


# --------------------------------------------------------------- cloth tops

def robe_top(base, trim=None, sleeve=1.25, collar_col=None, seed=0):
    t = torso(base, 12, bulk=1.05)
    t.add(loft([ring(28, 70, 12, 1.0, 0.68), ring(27.5, 100, 12, 1.0, 0.64)], cap_bottom=True,
               cap_top=False, col=base))
    jitter(t, 0.05, seed)
    parts = [t, collar(collar_col or trim or base, 14, 167, 8)]
    for s in (1, -1):
        a = arm(base, s, 8.5, sleeve_flare=sleeve)
        parts.append(a)
        if trim:
            parts.append(prism(8.5 * sleeve * 0.95, 8.5 * sleeve * 1.05, 4, 6, col=trim).move(s * 40, 94, 7))
    if trim:
        parts.append(box(5, 98, 2, trim).move(0, 120, 19.5))  # front placket
        parts.append(loft([ring(28.6, 70, 12, 1.0, 0.69), ring(28.4, 75, 12, 1.0, 0.69)],
                          cap_bottom=False, cap_top=False, col=trim))
    return merge(*parts)


def hood(base, inner=(14, 12, 14), trim=None, mantle=True, peak=8, seed=0):
    c = HEAD
    prof = [(24, c[1] - 24), (25.5, c[1] - 8), (25, c[1] + 6), (21, c[1] + 18), (12, c[1] + 26),
            (0.01, c[1] + 28 + peak * 0.3)]
    h = lathe(prof, 12, 1.0, 1.12, col=base).move(0, 0, c[2] - 2)
    h = h.subdivide()

    def opening(cn, n, i):
        rel = cn - c
        if cn[2] > 10 and rel[1] < 10 and abs(rel[0]) < 15 - max(0, rel[1]) * 0.2 and rel[1] > -24:
            return inner
        return None
    h.paint_fn(opening)
    if peak:
        h.add(spike((0, c[1] + 18, c[2] + 18), (0, 0.6, 0.8), peak, 7, 4, base))
    jitter(h, 0.06, seed)
    parts = [h]
    if mantle:
        parts.append(drape(shade(base, 0.92), 172, 140, 18, 36, 12, jag=5, seed=seed))
    if trim:
        parts.append(torus(15, 1.6, 10, 3, trim).scale(1, 1.3, 1).move(0, c[1] - 4, c[2] + 23))
    return merge(*parts)


def cape(base, y_top=170, y_bot=40, w_top=26, w_bot=46, jag=10, n=9, seed=0, curl=14, rows=5):
    """Back-hanging cloak, double sided, ragged hem."""
    rng = random.Random(seed)
    rings = []
    for r in range(rows):
        t = r / (rows - 1)
        y = y_top + (y_bot - y_top) * t
        w = w_top + (w_bot - w_top) * t
        z0 = -18 - 10 * t
        row = []
        for j in range(n):
            u = j / (n - 1) * 2 - 1
            dy = 0
            if r == rows - 1 and jag:
                dy = -rng.uniform(0, jag) if j % 2 else rng.uniform(0, jag * 0.3)
            row.append((u * w, y + dy, z0 + curl * (1 - u * u) * -0.3 + abs(u) * curl * 0.6))
        rings.append(row)
    m = loft(rings, cap_bottom=False, cap_top=False, closed_ring=False, col=base)
    # face outward = away from the body (toward -z)
    if np.mean(m.normals()[:, 2]) > 0:
        m.flip()
    m = m.subdivide()
    return m.double()


# ----------------------------------------------------------------- weapons

def grip(length=34, r=2.6, col=(80, 52, 32), wrap=None, pommel=None, pommel_r=4.0):
    m = prism(r, r * 0.9, length, 6, -length, col=col)
    if wrap:
        m = m.subdivide()
        bands(m, 1, 3.5, [col, wrap])
    if pommel:
        m.add(sphere(pommel_r, 6, 3, col=pommel).move(0, -length - pommel_r * 0.5, 0))
    return m


def blade(length, width, col, *, curve=0.0, tip=0.18, thick=2.4, edge_col=None, base_y=0, steps=8,
          taper_end=0.25, serr=0):
    """Diamond-section blade along +y. curve bends it toward +x (scimitar)."""
    pts, sc = [], []
    for i in range(steps + 1):
        t = i / steps
        y = base_y + length * t
        x = curve * length * (t ** 2) * 0.35
        pts.append((x, y, 0))
        w = width * (1 - t * (1 - taper_end)) if t < 1 - tip else width * taper_end * (1 - t) / tip
        if curve:
            w *= 1 + 0.35 * math.sin(math.pi * t)
        if serr and i % 2 == 1 and i < steps:
            w *= 1.35
        sc.append((max(w, 0.2), 1.0 if t < 1 - tip else max(0.15, (1 - t) / tip)))
    sec = [(-0.5, 0), (0, thick / 2), (0.5, 0), (0, -thick / 2)]
    m = sweep(pts, [(u, v) for u, v in sec], up=(0, 0, 1), col=col, scales=sc)
    if edge_col:
        m = m.subdivide()
        cs, ns = m.centroids(), m.normals()
        for i, (c, n) in enumerate(zip(cs, ns)):
            if abs(n[2]) < 0.5:
                m.C[i] = edge_col
    return m


def crossguard(w, col, h=4.5, d=6, flare=0.0, curl=0.0):
    if not flare and not curl:
        return box(w, h, d, col)
    pts = bezier((-w / 2, curl, 0), (-w / 4, -flare, 0), (w / 4, -flare, 0), (w / 2, curl, 0), 8)
    return tube(pts, h / 2, 5, col, taper=[1.3, 1.1, 1, 0.9, 0.85, 0.9, 1, 1.1, 1.3])


def handle(length, r=2.8, col=(92, 64, 40), cap=None, y0=0.0, n=6):
    m = prism(r, r * 0.92, length, n, y0, col=col)
    if cap:
        m.add(prism(r * 1.35, r * 1.2, 4, n, y0 - 2, col=cap))
        m.add(prism(r * 1.25, r * 1.25, 3, n, y0 + length * 0.55, col=cap))
    return m


def axe_head(poly, depth, col, edge=None, at=(0, 0, 0), rot=0):
    m = extrude(poly, depth, depth * 0.35, 0.82, col=col).subdivide()
    if edge:
        cs = m.centroids()
        xmax = max(p[0] for p in poly)
        for i, c in enumerate(cs):
            if c[0] > xmax - 5:
                m.C[i] = edge
    return m.rot('z', rot).move(*at)


def staff_shaft(length, col, r=2.6, ring_col=None, twist=0, n=6):
    pts = [(math.sin(t * 6) * twist, length * t - length * 0.25, math.cos(t * 6) * twist * 0.5)
           for t in np.linspace(0, 1, 10)]
    m = tube(pts, r, n, col, taper=np.linspace(1.0, 1.15, 10))
    if ring_col:
        for y in (length * 0.15, length * 0.55, length * 0.72):
            m.add(prism(r * 1.4, r * 1.4, 3, n, y - length * 0.25 - 1.5, col=ring_col))
    return m


def bow_limbs(col, length=110, depth=24, r=3.4, string_col=(220, 215, 200), grip_col=None, recurve=0.0,
              steps=10):
    """Bow in the xy plane, string on the -x side, grip at origin."""
    pts = []
    for i in range(steps + 1):
        t = i / steps * 2 - 1
        y = t * length / 2
        x = depth * (1 - t * t) - depth
        x += recurve * (abs(t) ** 6) * 14
        pts.append((x, y, 0))
    tap = [0.55 + 0.45 * (1 - abs(i / steps * 2 - 1)) for i in range(steps + 1)]
    m = tube(pts, r, 5, col, taper=tap)
    top, bot = np.array(pts[-1]), np.array(pts[0])
    m.add(tube([bot, top], 0.55, 3, string_col))
    if grip_col:
        m.add(prism(r * 1.25, r * 1.25, 16, 6, -8, col=grip_col).move(-depth * 0 + 0, 0, 0))
    return m, pts


def crossbow(stock_col, limb_col, *, string_col=(210, 205, 190), trim=None, length=70, span=64):
    stock = extrude([(-4, -length * 0.55), (4, -length * 0.55), (5, -length * 0.15), (3.5, length * 0.45),
                     (-3.5, length * 0.45), (-5, -length * 0.15)], 7, 1.6, 0.8, col=stock_col)
    stock.rot('x', -90)  # lies along z, pointing forward (+z = tip)
    stock.rot('y', 0)
    butt = box(9, 12, 14, shade(stock_col, 0.85)).move(0, -3, -length * 0.55)
    trig = box(2, 8, 3, (60, 60, 64)).move(0, -7, -length * 0.1)
    pts = [(x, 0, length * 0.42 - 8 * (1 - (2 * x / span) ** 2) * -1 - 6) for x in np.linspace(-span / 2, span / 2, 9)]
    pts = [(p[0], 0, length * 0.42 - 9 * (abs(2 * p[0] / span) ** 1.5)) for p in pts]
    limbs = tube(pts, 2.6, 5, limb_col, taper=[0.6, 0.8, 0.95, 1.05, 1.1, 1.05, 0.95, 0.8, 0.6], up=(0, 1, 0))
    string = merge(tube([pts[0], (0, 0.5, length * 0.05)], 0.5, 3, string_col),
                   tube([(0, 0.5, length * 0.05), pts[-1]], 0.5, 3, string_col))
    parts = [stock, butt, trig, limbs, string]
    if trim:
        parts.append(box(10, 3, 5, trim).move(0, 0, length * 0.4))
    return merge(*parts), pts


# ------------------------------------------------------------------ shields

def kite_poly(w=44, h=60):
    return [(0, -h * 0.62), (w * 0.32, -h * 0.3), (w * 0.5, h * 0.15), (w * 0.46, h * 0.36),
            (w * 0.2, h * 0.38), (0, h * 0.42), (-w * 0.2, h * 0.38), (-w * 0.46, h * 0.36),
            (-w * 0.5, h * 0.15), (-w * 0.32, -h * 0.3)]


def heater_poly(w=46, h=56):
    pts = [(-w / 2, h * 0.45), (w / 2, h * 0.45)]
    for k in range(1, 8):
        t = k / 8
        pts.append((w / 2 * math.cos(t * math.pi / 2) ** 0.8, h * 0.45 - h * 1.0 * math.sin(t * math.pi / 2)))
    pts.append((0, -h * 0.55))
    for k in range(7, 0, -1):
        t = k / 8
        pts.append((-w / 2 * math.cos(t * math.pi / 2) ** 0.8, h * 0.45 - h * 1.0 * math.sin(t * math.pi / 2)))
    return pts


def shield(poly, col, depth=6, dome=4, rim=None, rim_w=0.9):
    body = extrude(poly, depth, depth * 0.3, 0.86, col=col, dome=dome)
    out = body
    if rim:
        P = np.array(poly, float)
        c = P.mean(0)
        outer = [tuple(c + (p - c) * 1.0) for p in P]
        rimm = extrude(outer, depth * 0.7, col=rim).move(0, 0, -depth * 0.25)
        rimm.scale(1.06, 1.05, 1.0)
        out = merge(body, rimm)
    return out


# -------------------------------------------------------------- jewellery

def necklace_chain(col, w=26, drop=34, link=3.2):
    pts = bezier((-w, drop, -2), (-w * 0.9, 4, 0), (w * 0.9, 4, 0), (w, drop, -2), 14)
    return chain(pts, link * 1.25, col, thick=0.32)  # chunky links stay visible at icon size


def star_poly(points, r_out, r_in, phase=math.pi / 2):
    return [((r_out if k % 2 == 0 else r_in) * math.cos(phase + math.pi * k / points),
             (r_out if k % 2 == 0 else r_in) * math.sin(phase + math.pi * k / points)) for k in range(points * 2)]
