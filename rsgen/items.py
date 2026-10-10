"""The 84 redesigns from the reference sheet (B01..B14, six per batch,
read left-to-right, top-to-bottom).

Each builder returns one Mesh. Worn items are modelled on the standard
player (see parts.py); weapons/shields/jewellery in item space.
`hides` lists player kit parts the item covers: 6 arms, 8 hair, 11 jaw.
"""
import math
import random

import numpy as np

from .geom import (Mesh, merge, lathe, box, sphere, gem, spike, tube, bezier, torus, chain,
                   extrude, circle2d, shade, mix, _align_y_to)
from .parts import (HEAD, FRONT, body_pt, body_strip, body_shell, plate_band, ring_band, pauldron,
                    sleeve, faulds, cuirass, helm, horn, wing, feather, sunburst, drape, leg, greave,
                    platelegs, skirt, gauntlet, robe_top, hood, cape, grip, wrapped_handle, blade,
                    crossguard, axe_head, crescent, staff_shaft, bow_limbs, crossbow, kite_poly, heater_poly,
                    inset_poly, shield, necklace_chain, rope, star_poly, star3d, jitter, cracks, speckle,
                    scales_pattern, paint_where, gem_like)

# ------------------------------------------------------------------ palette
GOLD = (222, 172, 60)
GOLD_D = (168, 120, 40)
GOLD_L = (245, 205, 110)
BONE = (218, 205, 176)
BONE_D = (160, 146, 120)
LEATHER = (96, 64, 42)
LEATHER_D = (62, 42, 30)
WOOD = (112, 76, 46)
OBSID = (36, 32, 34)
LAVA = (255, 112, 26)
LAVA_HOT = (255, 186, 64)
NECRO = (138, 133, 118)
NECRO_D = (92, 88, 78)
NECRO_G = (120, 240, 80)
CYAN = (90, 225, 225)
ICE = (120, 215, 228)
VOID = (38, 32, 56)
VOID_G = (160, 100, 255)
RUNE = (90, 190, 255)
WHITE = (238, 238, 242)
CLOTH_BLUE = (58, 84, 156)

ARMS, HAIR, JAW = 6, 8, 11
ITEMS = []


def item(code, name, slot, view=None, hides=None):
    def deco(fn):
        ITEMS.append(dict(code=code, name=name, slot=slot, build=fn, view=view or {},
                          hides=list(hides) if hides is not None else default_hides(slot)))
        return fn
    return deco


def default_hides(slot):
    return {'head': [HAIR, JAW]}.get(slot, [])


WEAPON_VIEW = dict(roll=-42, yaw=-18, pitch=10)
SHIELD_VIEW = dict(yaw=-28, pitch=12)
BOW_VIEW = dict(roll=-40, yaw=-14, pitch=8)
XBOW_VIEW = dict(yaw=-50, pitch=40)
NECK_VIEW = dict(yaw=-12, pitch=8)
CAPE_VIEW = dict(yaw=200, pitch=12)


# ------------------------------------------------------------ item helpers

def lava(m, seeds=18, seed=0, col=LAVA, subdiv=0):
    for _ in range(subdiv):
        m = m.subdivide()
    return cracks(m, seeds, col, True, seed)


def shards(surface, count, cols, size=(3, 5), length=(10, 18), seed=0, pred=None, lift=0.5, n=5):
    """Crystal shards growing out of a surface along its face normals."""
    rng = random.Random(seed)
    cs, ns = surface.centroids(), surface.normals()
    idx = [i for i in range(len(cs)) if pred is None or pred(cs[i], ns[i])]
    out = Mesh()
    if not idx:
        return out
    for _ in range(count):
        i = rng.choice(idx)
        d = ns[i] + np.array([0, lift, 0]) + np.array([rng.uniform(-0.3, 0.3) for _ in range(3)])
        g = gem(rng.uniform(*size), rng.uniform(*length), n, rng.choice(cols))
        _align_y_to(g, d / np.linalg.norm(d))
        out.add(g.move(*cs[i]))
    return out


def glyph(h, col, w=1.6, glow=True):
    """A rune: a vertical stroke with stacked chevrons and a diamond."""
    m = box(w, h, w, col)
    for k, y in enumerate((-h * 0.3, 0, h * 0.28)):
        L = h * (0.32 - 0.05 * k)
        for s in (1, -1):
            m.add(box(L, w, w, col).rot('z', s * 38).move(s * L * 0.38, y + L * 0.22, 0))
    m.add(box(h * 0.2, h * 0.2, w, col).rot('z', 45).move(0, -h * 0.5, 0))
    m.G = [glow] * len(m.F)
    return m


def grooves(col, seeds, seed):
    """Dark panel lines that split a surface into large plates."""
    return lambda m: cracks(m, seeds, col, False, seed, warp=0.15)


def crest_strip(col):
    """Vertical crest strip over the top of a helm, front to back."""
    pts = [(0, HEAD[1] + 25 * math.sin(math.radians(a)) * 1.05, HEAD[2] + 25.6 * math.cos(math.radians(a)) * 1.12)
           for a in range(10, 100, 15)]
    return tube(pts, 1.5, 4, col)


# ======================================================== B01 platebodies
@item('B01_1', 'Copper scale platebody', 'body')
def _():
    c = (188, 114, 70)
    return cuirass(c, studs_col=(236, 182, 128), breast_col=shade(c, 0.85), gorget_col=shade(c, 0.9),
                   finish=lambda m: jitter(m, 0.09, 11), pauldron_size=1.08)


@item('B01_2', 'Iron platebody', 'body')
def _():
    c = (110, 112, 118)
    return cuirass(c, breast_col=shade(c, 0.8), finish=lambda m: jitter(grooves((60, 61, 66), 9, 12)(m), 0.06, 12),
                   pauldron_size=1.1)


@item('B01_3', 'Steel platebody', 'body')
def _():
    c = (184, 187, 194)
    return cuirass(c, breast_col=shade(c, 0.8),
                   finish=lambda m: jitter(grooves((112, 114, 120), 12, 13)(m), 0.05, 13), pauldron_size=1.12)


@item('B01_4', 'Shadowsteel platebody', 'body')
def _():
    c = (46, 42, 56)

    def fin(m):
        m = cracks(m, 16, (28, 24, 34), False, 14, warp=0.15)
        speckle(m, 0.07, (96, 56, 150), False, 14)
        return jitter(m, 0.08, 14)
    return cuirass(c, breast_col=(34, 30, 42), finish=fin, pauldron_size=1.12, gorget_col=(30, 28, 36))


@item('B01_5', 'Silver filigree platebody', 'body')
def _():
    c = (202, 212, 224)

    def fin(m):
        m = cracks(m, 26, (140, 154, 178), False, 15, warp=0.6, width=1.6, where=lambda c: c[2] > 10)
        return jitter(m, 0.04, 15)
    m = cuirass(c, trim=(232, 236, 244), finish=fin, pauldron_size=1.1, lame_trim=True)
    for s in (1, -1):  # engraved leaf sprays either side of the ridge
        for k in range(4):
            lf = extrude([(0, 0), (5, 2.5), (9, 0), (5, -1.5)], 1.0, col=(150, 165, 188))
            out = body_pt(FRONT + s * (0.18 + 0.05 * k), 150 - k * 7, 1.0)
            m.add(lf.rot('z', s * (30 + k * 8)).scale(s, 1, 1).move(*out))
    return m


@item('B01_6', 'Jade crystal platebody', 'body')
def _():
    c = (44, 136, 100)
    m = cuirass(c, breast_col=(34, 110, 80), finish=lambda q: jitter(q, 0.2, 16), pauldron_size=1.1)
    surf = body_shell(c, 100, 162, 12, 1.0)
    m.add(shards(surf, 22, [(60, 170, 125), (40, 140, 100), (80, 190, 145)], (3.5, 6), (8, 14), 16,
                 pred=lambda cc, nn: cc[2] > 4, lift=0.2, n=4))
    for s in (1, -1):
        for k in range(3):
            g = gem(5, 16, 4, (70, 180, 135)).rot('z', -s * (25 + k * 22)).move(s * (32 + k * 3), 168 - k * 5, k * 4 - 4)
            m.add(g)
    return m


# ===================================================== B02 sapphire / crimson / magma tools
@item('B02_1', 'Royal sapphire platebody', 'body')
def _():
    c = (42, 74, 200)
    m = cuirass(c, trim=GOLD, lames=2, finish=lambda q: jitter(q, 0.16, 21), pauldron_size=1.15, subdiv=1,
                pauldron_layers=2, ridge=False, breast_col=c)
    for s in (1, -1):  # V-neckline trim
        m.add(body_strip(FRONT + s * 0.3, 140, 164, 2.6, GOLD, 0.8, 1.4))
    return m


@item('B02_2', 'Crimson dragonscale body', 'body')
def _():
    c = (178, 34, 44)
    m = cuirass(c, lames=3, finish=lambda q: jitter(scales_pattern(q, c, 6.0), 0.1, 22), pauldron_size=1.2, subdiv=1,
                breast_col=shade(c, 0.85), gorget_col=shade(c, 0.85), faulds_col=shade(c, 0.9), fauld_len=14,
                spikes=4, spike_col=(200, 46, 56))
    surf = body_shell(c, 98, 166, 12, 1.0)
    m.add(shards(surf, 48, [(196, 42, 54), (160, 28, 38), (214, 60, 70)], (2.2, 3.4), (5, 10), 22, lift=-0.4, n=4))
    for k in range(14):  # spiky collar
        t = 2 * math.pi * k / 14
        m.add(spike(body_pt(t, 168, 0), (math.cos(t), 1.2, -math.sin(t)), 11, 2.6, 4, (196, 42, 54)))
    return m


@item('B02_3', 'Crimson crystal scimitar', 'weapon', WEAPON_VIEW)
def _():
    red, dark = (204, 34, 48), (130, 18, 30)
    b = jitter(blade(68, 13, red, curve=1.35, thick=3.6, tip=0.22, edge_col=(236, 70, 84), base_y=2), 0.2, 23)
    g = crossguard(22, dark, 4.5, 6, flare=1.5, curl=5)
    for s in (1, -1):
        g.add(spike((s * 11, 5, 0), (s * 0.4, 1, 0), 6, 2, 4, red))
    hook = tube(bezier((0, -20, 0), (0, -27, 0), (8, -30, 0), (9, -24, 0), 6), 2.4, 5, red,
                taper=[1.2, 1.1, 1, 0.9, 0.7, 0.5, 0.3])
    return merge(b, g, grip(20, 2.8, dark, wrap=(90, 14, 22)), hook)


def pick_head(col, span=62, r=6.2, rise=10):
    pts = bezier((-span / 2, -rise * 0.6, 0), (-span / 4, rise * 0.9, 0), (span / 4, rise * 0.9, 0),
                 (span / 2, -rise * 0.6, 0), 10)
    tap = [0.15, 0.5, 0.8, 1.0, 1.15, 1.3, 1.15, 1.0, 0.8, 0.5, 0.15]
    return tube(pts, r, 6, col, taper=tap, up=(0, 0, 1))


@item('B02_4', 'Sapphire pickaxe', 'weapon', WEAPON_VIEW)
def _():
    blue = (40, 76, 214)
    h = wrapped_handle(66, 3.8, (30, 50, 150), wrap=(24, 38, 120), y0=-38, cap=GOLD, pommel=GOLD,
                       pommel_kind='gem')
    head = jitter(pick_head(blue).move(0, 30, 0), 0.14, 24)
    sock = lathe([(6, -6), (6.5, 0), (5.5, 6)], 6, col=GOLD).move(0, 29, 0)
    return merge(h, head, sock)


@item('B02_5', 'Magma pickaxe', 'weapon', WEAPON_VIEW)
def _():
    h = lava(wrapped_handle(64, 4.2, OBSID, y0=-36, cap=(66, 44, 30), pommel=GOLD_D, pommel_kind='gem'), 5, 25)
    head = lava(pick_head(OBSID, 64, 7.0, 12).move(0, 30, 0), 18, 26)
    return merge(h, jitter(head, 0.1, 26), lathe([(7, -7), (7.5, 0), (6.5, 7)], 6, col=(54, 40, 32)).move(0, 29, 0))


@item('B02_6', 'Magma hatchet', 'weapon', WEAPON_VIEW)
def _():
    h = lava(wrapped_handle(62, 4.4, OBSID, y0=-34, cap=(66, 44, 30), pommel=GOLD_D, pommel_kind='gem'), 5, 27)
    head = lava(axe_head(crescent(30, 18, 150, 10, 12), 8, OBSID, at=(2, 20, 0)), 14, 28)
    back = extrude([(0, -6), (-14, -1), (-16, 2), (0, 6)], 6, 1.6, 0.7, col=OBSID).move(-2, 20, 0)
    crown = merge(*[spike((x, 27, 0), (x * 0.05, 1, 0), 9 - abs(x) * 0.3, 2.6, 4, GOLD) for x in (-4, 0, 4)])
    collar_ = lathe([(5.5, -8), (6.5, 0), (5.5, 8)], 6, col=GOLD).move(0, 20, 0)
    return merge(h, head, lava(back, 4, 29), crown, collar_)


# ===================================================== B03 necrotic arsenal
def necro_skull(scale=1.0, eye=NECRO_G, col=BONE):
    s = lathe([(0.01, -6), (4.5, -5), (5.8, -1), (5.8, 3), (4.4, 6.5), (0.01, 7.5)], 8, col=col)
    jaw = extrude([(-4.5, 0), (4.5, 0), (3.5, -5), (-3.5, -5)], 6, 1.2, 0.8, col=shade(col, 0.85)).move(0, -4.5, 1.6)
    teeth = merge(*[box(1.0, 1.6, 1.0, col).move(x, -4.4, 4.8) for x in (-2.4, -0.8, 0.8, 2.4)])
    eyes = merge(*[sphere(1.6, 5, 2, col=eye).scale(1, 0.85, 0.5).move(x, 0.8, 5.3) for x in (-2.3, 2.3)])
    eyes.G = [True] * len(eyes.F)
    nose = extrude([(-0.8, 0), (0.8, 0), (0, 1.6)], 1, col=(30, 28, 26)).move(0, -2.3, 5.6)
    return merge(s.scale(1, 1, 1.05), jaw, teeth, eyes, nose).scale(scale)


def necro_handle(length, y0, r=3.6):
    return wrapped_handle(length, r, NECRO_D, wrap=(70, 66, 58), y0=y0, cap=NECRO, pommel=NECRO,
                          pommel_kind='spike', wrap_from=0.05, wrap_to=0.95)


def necro_stone(m, seed, seeds=10):
    m = jitter(m, 0.1, seed)
    return cracks(m, seeds, NECRO_G, True, seed, warp=0.5)


@item('B03_1', 'Necrotic battleaxe', 'weapon', WEAPON_VIEW)
def _():
    h = necro_handle(86, -46)
    a = necro_stone(axe_head(crescent(28, 18, 160, 10, 12), 6, NECRO, at=(3, 30, 0)), 31, 8)
    b = a.mirrored()
    sk = necro_skull(1.25).move(0, 31, 4.5)
    top = merge(spike((0, 40, 0), (0, 1, 0), 15, 3.4, 4, NECRO), spike((0, 36, 0), (1, 0.6, 0), 8, 2, 4, NECRO),
                spike((0, 36, 0), (-1, 0.6, 0), 8, 2, 4, NECRO))
    return merge(h, a, b, sk, top, box(8, 16, 8, NECRO_D).move(0, 30, 0))


@item('B03_2', 'Necrotic spear', 'weapon', WEAPON_VIEW)
def _():
    shaft = necro_handle(100, -60, 3.0)
    tip = necro_stone(blade(36, 11, NECRO, thick=3.4, base_y=40, tip=0.35, edge_col=(176, 170, 152)), 32, 4)
    barbs = Mesh()
    for k in range(5):
        for s in (1, -1):
            barbs.add(spike((s * 3, 14 + k * 6, 0), (s, 0.9, 0.2 * s), 7 - k * 0.6, 1.8, 4, NECRO))
    for k in range(3):
        for s in (1, -1):
            barbs.add(spike((s * 4, 44 + k * 8, 0), (s, 0.5, 0), 6, 1.6, 3, NECRO))
    return merge(shaft, tip, barbs, lathe([(4.6, 34), (5.2, 38), (4.2, 41)], 6, col=NECRO_D))


def spiked_ball(r, col, spikes=14, spike_col=None, glow=None, seed=0):
    b = jitter(sphere(r, 8, 5, col=col), 0.1, seed)
    if glow:
        b = cracks(b, 8, glow, True, seed)
    dirs = [(0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1),
            (0.7, 0.7, 0), (-0.7, 0.7, 0), (0, 0.7, 0.7), (0, 0.7, -0.7), (0.7, -0.7, 0),
            (-0.7, -0.7, 0), (0, -0.7, 0.7), (0, -0.7, -0.7), (0.6, 0, 0.6), (-0.6, 0, 0.6),
            (0.6, 0, -0.6), (-0.6, 0, -0.6)][:spikes]
    for d in dirs:
        d = np.array(d) / np.linalg.norm(d)
        b.add(spike(d * r * 0.85, d, r * 0.7, r * 0.28, 4, spike_col or col))
    return b


@item('B03_3', 'Necrotic flail', 'weapon', WEAPON_VIEW)
def _():
    h = necro_handle(44, -28)
    ring_ = torus(3.6, 1.3, 8, 4, NECRO).rot('y', 90).move(0, -33, 0)
    ch = chain(bezier((0, 18, 0), (6, 32, 0), (18, 38, 0), (28, 32, 0), 12), 5.2, (104, 102, 96), thick=0.3)
    ball = spiked_ball(12, NECRO, 18, (180, 174, 158), NECRO_G, 34).move(34, 24, 0)
    return merge(h, ring_, lathe([(5, 14), (5.5, 17), (2.5, 19)], 6, col=NECRO), ch, ball)


def maul(seed):
    h = necro_handle(56, -32, 3.8)
    head = necro_stone(box(30, 18, 18, NECRO).subdivide(), seed, 6)
    for s in (1, -1):
        cap = lathe([(9.5, 0), (10.5, 2.5), (8.5, 5)], 6, col=NECRO_D).rot('z', -90 * s).move(s * 15, 0, 0)
        head.add(cap)
        for k in range(3):
            a = 2 * math.pi * k / 3
            head.add(spike((s * 6, 9 * math.cos(a) * 0.9, 9 * math.sin(a) * 0.9),
                           (0, math.cos(a), math.sin(a)), 7, 2.4, 4, NECRO))
    return merge(h, head.move(0, 28, 0), spike((0, 37, 0), (0, 1, 0), 9, 3, 4, NECRO))


@item('B03_4', 'Necrotic twin mauls', 'weapon', dict(yaw=-12, pitch=12))
def _():
    return merge(maul(35).rot('z', 22).move(-16, 0, 0), maul(36).rot('z', -22).move(16, 0, 2))


@item('B03_5', 'Necrotic crossbow', 'weapon', XBOW_VIEW)
def _():
    m, pts = crossbow((150, 144, 128), BONE_D, trim=NECRO_D, limb_r=4.2, stock_w=11, recurve=0.6)
    for p in pts[1:-1]:  # vertebra knuckles along the limbs
        m.add(box(6, 6, 6, BONE).rot('y', 20).move(*p))
    for p in (pts[0], pts[-1]):
        m.add(spike(p, (np.sign(p[0]) * 0.6, 0, -1), 10, 2.4, 4, BONE))
    for z in (-20, 0, 18):
        for s in (1, -1):
            m.add(spike((s * 5, 2, z), (s, 0.7, 0), 6, 1.8, 4, BONE))
    m.add(necro_skull(0.8).move(0, 6, -26))
    return jitter(m, 0.08, 37)


@item('B03_6', 'Necrotic skull censer', 'weapon', WEAPON_VIEW)
def _():
    h = necro_handle(58, -34)
    hoop = jitter(torus(17, 3.2, 14, 5, NECRO), 0.12, 38).move(0, 46, 0)
    for k in range(12):
        a = 2 * math.pi * k / 12
        L = 10 if k % 2 else 7
        hoop.add(spike((19 * math.cos(a), 46 + 19 * math.sin(a), 0), (math.cos(a), math.sin(a), 0.2 * (k % 3 - 1)),
                       L, 2.4, 4, NECRO))
    sk = necro_skull(1.7).move(0, 46, 0)
    glow = sphere(7, 6, 3, col=NECRO_G).scale(1, 1, 0.4).move(0, 46, -3)
    glow.G = [True] * len(glow.F)
    chains = Mesh()
    for s in (1, -1):
        chains.add(chain([(s * 14, 34, 1), (s * 16, 10, 2)], 3.6, (104, 102, 96), thick=0.3))
        chains.add(lathe([(0.01, 0), (3, 2), (2.5, 5), (0.01, 7)], 5, col=NECRO).move(s * 16, 3, 2))
    return merge(h, hoop, sk, glow, chains, lathe([(5, 24), (6, 28), (4, 31)], 6, col=NECRO))


# =========================================================== B04 bloodbone
REAVER = (54, 42, 40)
REAVER_D = (34, 28, 28)
SMEAR = (130, 26, 30)


def reaver_finish(seed):
    def f(m):
        m = cracks(m, 18, REAVER_D, False, seed, warp=0.2, max_faces=560)
        speckle(m, 0.035, SMEAR, False, seed)
        return jitter(m, 0.1, seed)
    return f


@item('B04_1', 'Reaver platebody', 'body')
def _():
    m = cuirass(REAVER, finish=reaver_finish(41), studs_col=(120, 108, 96), spikes=3, spike_col=(96, 90, 84),
                pauldron_size=1.25, faulds_col=(110, 26, 30), fauld_len=22, belt_col=LEATHER_D,
                gorget_col=REAVER_D, breast_col=(120, 26, 32))
    for k in range(6):
        m.add(spike(body_pt(math.pi * 0.5 + (k - 2.5) * 0.25, 160, 0), (0, 0.4, -1), 9, 2.4, 4, (96, 90, 84)))
    m.add(faulds(REAVER, None, 6, 98, 13, 6))
    return m


@item('B04_2', 'Reaver platelegs', 'legs')
def _():
    m = platelegs(REAVER, None, finish=reaver_finish(42), belt_col=LEATHER_D, tasset_col=(110, 26, 30), tasset_len=34)
    m.add(faulds(REAVER, None, 6, 100, 20, 7))
    for s in (1, -1):
        m.add(spike((s * 13, 56, 12), (0, 0.3, 1), 9, 2.8, 4, (96, 90, 84)))
    return m


@item('B04_3', 'Reaver warboots', 'feet')
def _():
    out = Mesh()
    for s in (1, -1):
        out.add(reaver_finish(43 + s)(greave(REAVER, s, None, True, True, 40, 8, 11.5)))
        out.add(lathe([(8, 0), (9, 3), (7, 7)], 7, col=REAVER_D).scale(1, 1, 1.4).move(s * 13, 0, 6))
        for k in range(3):
            out.add(spike((s * 23, 12 + k * 10, 0), (s, 0.4, 0), 7, 2.2, 4, (96, 90, 84)))
    return out


@item('B04_4', 'Horned bone helm', 'head')
def _():
    h = helm(BONE, opening='eyes', r=23, sz=1.25, top=1.1, inner=(30, 18, 16))
    h = jitter(cracks(h, 12, (140, 30, 32), False, 44, warp=0.6, width=2.2), 0.07, 44)
    parts = [h]
    for s in (1, -1):
        parts.append(horn(s, (228, 216, 190), 40, 1.1, 5.2, (17, 200, -2), forward=8))
        parts.append(spike((s * 8, 175, 23), (s * 0.15, -1, 0.35), 13, 2.6, 4, BONE))  # tusks
        parts.append(spike((s * 21, 182, 8), (s * 0.4, -1, 0.1), 10, 2.4, 4, BONE_D))
        parts.append(extrude([(-6, 0), (6, 0), (4, 3)], 4, col=BONE_D).rot('z', -s * 12).move(s * 9, 194, 25))
    parts.append(extrude([(-2.5, -8), (2.5, -8), (1.6, 14), (-1.6, 14)], 4, col=BONE_D).move(0, 196, 26))
    return merge(*parts)


@item('B04_5', 'Ribcage platebody', 'body')
def _():
    flesh = (82, 22, 26)
    parts = [jitter(body_shell(flesh, 100, 170, 12, -1.0), 0.1, 45)]
    for k in range(7):
        y = 160 - k * 8.2
        for side in (1, -1):  # each rib curls from the spine around to the sternum
            pts = [body_pt(math.pi / 2 + side * a, y + 3 * math.sin(a), 1.2) for a in np.linspace(0.08, math.pi - 0.18, 9)]
            parts.append(tube(pts, 2.5, 5, BONE, taper=[1.1, 1, 1, 1, 1, 0.95, 0.9, 0.85, 0.8]))
    parts.append(tube([body_pt(FRONT, y, 2.0) for y in (108, 128, 150, 164)], 3.0, 6, BONE))
    parts.append(tube([body_pt(math.pi / 2, y, 1.0) for y in (100, 130, 168)], 3.4, 6, BONE_D))
    parts.append(ring_band(18, 13, 162, 172, BONE, 10, 0.8, inner_col=(40, 20, 20)))
    parts.append(faulds((126, 28, 34), None, 9, 101, 26, 7, jag=7, seed=45))
    for s in (1, -1):
        parts.append(pauldron(BONE, s, 1.05, 2, None, 2, BONE_D))
    return cracks(merge(*parts), 12, (120, 26, 30), False, 46, warp=0.5, width=2.2, max_faces=700)


@item('B04_6', 'Bone bracers', 'hands')
def _():
    out = Mesh()
    for s in (1, -1):
        g = gauntlet(BONE, s, None, 32, 10.5, 7, 1.2)
        out.add(jitter(cracks(g, 8, (130, 30, 34), False, 47 + s, warp=0.6, width=2.2), 0.07, 47))
        for k in range(3):
            out.add(spike((s * 51, 98 + k * 9, 7), (s, 0.5, 0), 9 - k, 2.4, 4, BONE))
        out.add(spike((s * 40, 125, 14), (0, 1, 0.5), 9, 2.6, 4, BONE))
        for y in (100, 110):
            out.add(torus(11.5, 0.9, 10, 3, (120, 26, 30)).rot('x', 90).rot('z', 18 * s).move(s * 40.5, y, 7))
    return out


# ============================================================ B05 knights
CRIMSON = (126, 26, 36)


def crown_band(col, r, y, sz=1.12, h=6, peaks=5):
    """Gold filigree band across the brow with upward points at the front."""
    m = ring_band(r + 1.2, r - 0.6, y - 2, y + 1.5, col, 16, sz, cz=HEAD[2])
    for k in range(peaks):
        t = FRONT + (k - (peaks - 1) / 2) * 0.32
        p = (r * 1.05 * math.cos(t), y, HEAD[2] - r * 1.05 * math.sin(t) * sz)
        m.add(spike(p, (math.cos(t) * 0.2, 1, -math.sin(t) * 0.2), h * (1.4 if k == peaks // 2 else 0.9), 1.6, 4, col))
    return m


@item('B05_1', 'Crimson knight helm', 'head')
def _():
    h = jitter(helm((86, 88, 96), opening='slit', point=1.0, top=1.1), 0.05, 51)
    h.add(crown_band(GOLD, 23.2, 194, peaks=5))
    h.add(crest_strip(GOLD))
    return merge(h, drape(CRIMSON, 174, 126, 21, 42, 14, jag=12, seed=51, folds=3))


@item('B05_2', 'Crimson chain hauberk', 'body')
def _():
    chain_c = (78, 80, 88)

    def mail(m):
        cs = m.centroids()
        for i, c in enumerate(cs):
            k = (int((c[1] + 200) / 2.6) + int((math.atan2(c[2], c[0]) + 4) * 12)) % 3
            m.C[i] = [chain_c, (52, 54, 60), (104, 106, 114)][k]
        return m
    m = cuirass(chain_c, trim=GOLD, lames=1, finish=mail, pauldron_col=(70, 72, 80), pauldron_size=1.18,
                gorget_col=(60, 62, 70), faulds_col=False, ridge=False, subdiv=1)
    m.add(extrude([(-12, 0), (12, 0), (13, -38), (0, -46), (-13, -38)], 2, col=CRIMSON).rot('x', -6).move(0, 108, 20))
    m.add(extrude([(-13, 0.5), (13, 0.5), (14, -39), (0, -48), (-14, -39)], 1.2, col=GOLD).rot('x', -6)
          .move(0, 108.4, 19.2))
    m.add(extrude([(-12, 0), (12, 0), (13, -38), (0, -46), (-13, -38)], 2, col=CRIMSON).rot('x', 6).move(0, 108, -20))
    m.add(plate_band(98, 104, LEATHER_D, 12, 2.6, 0.2))
    m.add(box(9, 7, 3, GOLD).move(0, 101, 19.5))
    m.add(faulds(CRIMSON, None, 10, 100, 22, 7, jag=6, seed=52))
    return m


@item('B05_3', 'Crimson knight tassets', 'legs')
def _():
    s = skirt(CRIMSON, 104, 44, 27, 42, 16, jag=12, points=True, waist=(54, 56, 62))
    plates = Mesh()
    for a in (-0.55, 0.55, -1.6, 1.6):
        t = FRONT + a
        p = extrude([(-9, 0), (9, 0), (10, -34), (0, -40), (-10, -34)], 2.4, 0.7, 0.85, col=(70, 72, 80))
        trim = extrude([(-10.2, 1), (10.2, 1), (11.2, -35), (0, -41.6), (-11.2, -35)], 1.2, col=GOLD).move(0, 0, -1)
        for q in (p, trim):
            q.rot('x', -12).rot('y', math.degrees(t) - 270)
            plates.add(q.move(*(body_pt(t, 100, 3.0) * [1.1, 1, 1.1])))
    emb = extrude(inset_poly([(-9, 8), (9, 8), (9, -8), (0, -16), (-9, -8)], 1), 3, 1, 0.8, col=(70, 72, 80))
    emb.add(extrude([(-10.5, 9.5), (10.5, 9.5), (10.5, -9), (0, -18), (-10.5, -9)], 1.5, col=GOLD).move(0, 0, -1))
    emb.add(sunburst(GOLD, 4, 2, 6, 2).move(0, 0, 1.8))
    plates.add(emb.rot('x', -8).move(0, 84, 26))
    for side in (1, -1):
        plates.add(leg((56, 56, 62), side, 9.5))
    return merge(s, plates)


@item('B05_4', 'Paladin full helm', 'head')
def _():
    h = jitter(helm(WHITE, opening='face', top=1.05), 0.04, 54)
    for x in (-8, -4, 0, 4, 8):  # gold grille bars across the face opening
        h.add(box(1.6, 22, 1.8, GOLD).move(x, 183, HEAD[2] + 21.5 * 1.12 - abs(x) * 0.25))
    h.add(box(20, 1.8, 1.8, GOLD).move(0, 189, HEAD[2] + 23.3))
    h.add(crown_band(GOLD, 23.2, 196, peaks=1, h=3))
    h.add(crest_strip(GOLD))
    h.add(ring_band(21.5, 19, 165, 169, GOLD, 16, 1.12, cz=HEAD[2]))
    return merge(h, drape(CLOTH_BLUE, 172, 132, 20, 40, 14, jag=8, seed=54, folds=3))


@item('B05_5', 'Paladin platebody', 'body')
def _():
    m = cuirass(WHITE, trim=GOLD, lames=2, finish=lambda q: jitter(q, 0.05, 55), pauldron_size=1.12,
                pauldron_layers=2, sleeves='short', sleeve_col=CLOTH_BLUE, ridge=False, breast_col=WHITE,
                faulds_col=WHITE)
    emb = merge(*[extrude([(0, 0), (s * 9, 6), (s * 5, -3), (0, -8)], 2, col=GOLD) for s in (1, -1)])
    emb.add(extrude([(-2, 6), (2, 6), (0, -12)], 2.4, col=GOLD))
    m.add(emb.move(0, 148, 22))
    for s in (1, -1):
        m.add(body_strip(FRONT + s * 0.32, 132, 164, 2.4, GOLD, 0.8, 1.4))
    return m


@item('B05_6', 'Paladin greaves', 'feet')
def _():
    out = Mesh()
    for s in (1, -1):
        out.add(jitter(greave(WHITE, s, GOLD, True, False, 50, 8, 12), 0.05, 56 + s))
        out.add(ring_band(10.5, 8.5, 2, 10, CLOTH_BLUE, 8, 1.0, cx=s * 13, cz=1))
    return out


# ============================================================ B06 magma set
def magma(seed, seeds=26):
    return lambda m: jitter(cracks(m, seeds, LAVA, True, seed), 0.08, seed)


@item('B06_1', 'Magma helm', 'head')
def _():
    return magma(61, 16)(helm(OBSID, opening='T', top=1.05, inner=(20, 10, 8)))


@item('B06_2', 'Magma platebody', 'body')
def _():
    return cuirass(OBSID, finish=magma(62, 28), lames=2, pauldron_size=1.12, pauldron_layers=2,
                   breast_col=(30, 26, 28), gorget_col=(30, 26, 28))


@item('B06_3', 'Magma gauntlets', 'hands')
def _():
    out = Mesh()
    for s in (1, -1):
        out.add(magma(63 + s, 10)(gauntlet(OBSID, s, None, 30, 10.5, 7, 1.18)))
        for k in range(3):
            out.add(box(3, 3, 9, OBSID).move(s * (37 + k * 2.4), 81, 9))
    return out


@item('B06_4', 'Magma dagger', 'weapon', WEAPON_VIEW)
def _():
    b = magma(64, 7)(blade(34, 11, OBSID, thick=3.6, tip=0.35, base_y=2).subdivide())
    g = crossguard(16, (54, 40, 32), 4.5, 6, flare=1, curl=2)
    return merge(b, g, grip(14, 2.8, OBSID, wrap=(70, 46, 30), pommel=(70, 46, 30), pommel_r=3.4))


@item('B06_5', 'Magma mace', 'weapon', WEAPON_VIEW)
def _():
    h = magma(65, 4)(wrapped_handle(44, 3.8, OBSID, y0=-24, cap=(54, 40, 32), pommel=(54, 40, 32)))
    rng = random.Random(66)
    head = sphere(15, 9, 6, 1.1, OBSID)
    head.V = head.V * (1 + np.array([[rng.uniform(-0.12, 0.12)] for _ in range(len(head.V))]))
    head = magma(66, 14)(head)
    return merge(h, head.move(0, 30, 0))


@item('B06_6', 'Magma kiteshield', 'shield', SHIELD_VIEW)
def _():
    return magma(68, 18)(shield(heater_poly(48, 62, 2), OBSID, 8, 6, rim=(44, 36, 34)))


# ============================================================ B07 rangers / valkyrie
def ranger_tunic(base, seed):
    dark = shade(base, 0.72)
    parts = [jitter(body_shell(base, 92, 170, 12, 0.8), 0.1, seed)]
    for s in (1, -1):
        parts.append(jitter(sleeve(base, s, 'long', 8.4, cuff=dark), 0.1, seed + s))
        parts.append(jitter(pauldron(base, s, 0.95, 2, None, n=6, flat=0.6), 0.1, seed))
        for y in (126, 112):  # bracer straps
            parts.append(ring_band(9.6, 8.0, y, y + 3, LEATHER, 7, 1.0, cx=s * 39.5, cz=3 + (126 - y) * 0.15))
    parts.append(faulds(base, None, 8, 95, 16, 4, jag=3, seed=seed))
    for a, b in ((-1, 1), (1, -1)):  # crossed bandoliers
        pts = [body_pt(FRONT + a * 0.95 * (1 - f) + b * 0.95 * f, 104 + 58 * f, 1.4) for f in np.linspace(0, 1, 8)]
        parts.append(tube(pts, 1.9, 4, LEATHER))
    parts.append(plate_band(97, 104, LEATHER, 12, 2.4, 0.2))
    parts.append(box(7, 6, 2.5, (176, 150, 90)).move(0, 100.5, 19.5))
    parts.append(hood(base, inner=(16, 14, 16), mask=dark, peak=4, lean=8, seed=seed, mantle_col=dark, jag=4))
    return merge(*parts)


@item('B07_1', 'Woodland ranger tunic', 'body', hides=[ARMS, HAIR, JAW])
def _():
    return ranger_tunic((92, 128, 60), 71)


@item('B07_2', 'Tidewalker ranger tunic', 'body', hides=[ARMS, HAIR, JAW])
def _():
    return ranger_tunic((56, 88, 162), 72)


@item('B07_3', 'Emberhide ranger tunic', 'body', hides=[ARMS, HAIR, JAW])
def _():
    return ranger_tunic((170, 56, 44), 73)


@item('B07_4', 'Nightstalker ranger tunic', 'body', hides=[ARMS, HAIR, JAW])
def _():
    return ranger_tunic((50, 50, 56), 74)


@item('B07_5', 'Valkyrie winged helm', 'head', hides=[HAIR])
def _():
    h = jitter(helm(WHITE, opening='face', top=1.05, inner=(24, 24, 30)), 0.05, 75)
    c = HEAD
    edge = []  # gold edging around the face opening
    for a, y in ([(-0.72, yy) for yy in (c[1] - 18, c[1] - 8, c[1] + 2)] + [(-0.36, c[1] + 6), (0, c[1] + 7.5),
                 (0.36, c[1] + 6)] + [(0.72, yy) for yy in (c[1] + 2, c[1] - 8, c[1] - 18)]):
        t = FRONT + a
        edge.append((23.6 * math.cos(t), y, c[2] - 23.6 * math.sin(t) * 1.12))
    h.add(tube(edge, 1.9, 4, GOLD))
    h.add(extrude([(-2, 0), (2, 0), (1.2, -12), (-1.2, -12)], 2, col=GOLD).move(0, c[1] + 7, c[2] + 26))
    h.add(crest_strip(GOLD))
    for s in (1, -1):
        h.add(wing(s, (62, 92, 176), (40, 64, 140), 1.75, at=(21, 198, -8), feathers=7, spread=10, base_col=GOLD))
        h.add(feather(14, 4, GOLD).rot('z', 35).rot('y', -20).scale(s, 1, 1).move(s * 20, 192, 2))
    return h


@item('B07_6', 'Valkyrie platebody', 'body')
def _():
    m = cuirass(WHITE, trim=GOLD, lames=2, finish=lambda q: jitter(q, 0.05, 76), pauldron_size=1.2,
                pauldron_layers=3, sleeves='short', sleeve_col=CLOTH_BLUE, ridge=False, faulds_col=CLOTH_BLUE,
                fauld_len=16, breast_col=WHITE)
    emb = merge(*[extrude([(0, 4), (s * 12, 9), (s * 4, -2), (0, -10)], 2, col=GOLD) for s in (1, -1)])
    m.add(emb.move(0, 146, 22))
    for s in (1, -1):
        m.add(wing(s, GOLD, GOLD_L, 0.6, at=(36, 168, 2), feathers=4, spread=14, base_col=GOLD))
    return m


# ============================================================ B08 seraph / solar / verdant
@item('B08_1', 'Seraph feather mantle', 'cape', dict(yaw=-25, pitch=14))
def _():
    out = Mesh()
    rng = random.Random(81)
    for row in range(4):
        n = 16 - row * 2
        for k in range(n):
            a = 2 * math.pi * k / n + row * 0.25
            L = 34 - row * 6 + rng.uniform(-4, 3)
            f = feather(L, 9 - row, mix((246, 243, 236), (226, 216, 194), row / 3), bevel=False).rot('z', -90)
            f.rot('x', -12 - row * 7).rot('y', -math.degrees(a) + 90)
            out.add(f.move((24 + row * 3) * math.cos(a), 170 - row * 8, -(17 + row * 2.5) * math.sin(a)))
    out.add(ring_band(19, 14, 166, 174, GOLD, 12, 0.8, inner_col=GOLD_D))
    for drop, w in ((22, 24), (36, 26)):
        out.add(chain(bezier((-w, 160, 14), (-w * 0.5, 160 - drop, 26), (w * 0.5, 160 - drop, 26), (w, 160, 14), 12),
                      3.6, GOLD, thick=0.32))
    for x, y in ((-14, 136), (0, 130), (14, 136)):  # drops hang from the lower chain
        out.add(gem(3.2, 11, 4, GOLD).scale(1, -1, 1).move(x, y - 3, 25))
    return out


@item('B08_2', 'Solar helm', 'head')
def _():
    h = helm(GOLD, opening='eyes', top=1.0, inner=(40, 26, 10)).subdivide()
    h = jitter(scales_pattern(h, GOLD, 5.0, 23), 0.06, 82)
    h.add(extrude([(-2.2, 8), (2.2, 8), (1.4, -14), (-1.4, -14)], 3, col=GOLD_L).move(0, HEAD[1], HEAD[2] + 25.5))
    rays = sunburst(GOLD_L, 14, 25, 54, 5, alt=0.62, bevel=0.45).move(0, 194, -8)
    return merge(h, rays)


@item('B08_3', 'Solar scale platebody', 'body', hides=[ARMS])
def _():
    m = cuirass(GOLD, lames=2, finish=lambda q: jitter(scales_pattern(q, GOLD, 5.0), 0.05, 83), pauldron_size=1.15, subdiv=1,
                pauldron_layers=3, sleeves='long', sleeve_col=(238, 230, 210), cuff_col=GOLD,
                faulds_col=(238, 232, 214), fauld_len=22, ridge=False, breast_col=GOLD_D)
    for s in (1, -1):
        m.add(ring_band(10.5, 8, 104, 118, GOLD, 7, 1.0, cx=s * 40, cz=5))
    m.add(merge(*[extrude([(0, 0), (4, 3), (8, 0), (4, -2)], 1.2, col=(110, 140, 60))
                  .rot('z', k * 30).move(*body_pt(FRONT + (k - 3) * 0.3, 100, 3.4)) for k in range(7)]))
    return m


@item('B08_4', 'Solar scale platelegs', 'legs')
def _():
    m = platelegs(GOLD, GOLD_D, finish=lambda q: jitter(scales_pattern(q, GOLD, 5.0), 0.05, 84),
                  thigh_col=(238, 232, 214), belt_col=GOLD_D)
    m.add(ring_band(27.6, 25, 99, 106, (120, 84, 44), 12, 0.66))
    return m


def verdant(m, seed):
    rng = random.Random(seed)
    for i in range(len(m.F)):
        m.C[i] = rng.choice([(94, 118, 52), (112, 124, 62), (80, 98, 46), (124, 100, 62), (104, 84, 52)])
    return m


def helm_face_restore(h, col=(24, 28, 14)):
    """Re-darken the recessed face opening after an all-over recolour."""
    cs = h.centroids()
    for i, c in enumerate(cs):
        r = math.hypot(c[0], (c[2] - HEAD[2]) / 1.12)
        if c[2] > 6 and r < 19 and HEAD[1] - 20 < c[1] < HEAD[1] + 6:
            h.C[i] = col
    return h


@item('B08_5', 'Verdant crystal helm', 'head')
def _():
    h = helm_face_restore(verdant(helm((96, 112, 54), opening='face', inner=(24, 28, 14), top=1.05).subdivide(), 85))
    cols = [(120, 228, 228), (90, 205, 220), (160, 240, 236)]
    crown = shards(h, 30, cols, (4, 7.5), (16, 32), 85, pred=lambda c, n: c[1] > 196 or c[2] < -6, lift=1.2)
    leaves = shards(h, 16, [(86, 110, 48), (110, 96, 58)], (2.5, 4), (6, 10), 86, lift=0.0, n=4)
    return merge(h, crown, leaves)


@item('B08_6', 'Verdant crystal body', 'body')
def _():
    m = cuirass((96, 112, 54), finish=lambda q: verdant(q, 86), pauldron_size=1.15, lames=2, subdiv=1)
    surf = body_shell((96, 112, 54), 100, 170, 12, 1.0)
    cols = [(120, 228, 228), (90, 205, 220), (160, 240, 236)]
    m.add(shards(surf, 34, cols, (3.5, 6), (12, 24), 86, lift=0.5))
    m.add(shards(surf, 22, [(86, 110, 48), (110, 96, 58)], (2.5, 4), (6, 10), 87, lift=-0.2, n=4))
    return m


# ============================================================ B09 bows
@item('B09_1', 'Bone longbow', 'weapon', BOW_VIEW)
def _():
    m, pts = bow_limbs(BONE, 118, 26, 4.6, grip_col=LEATHER, recurve=1.2, thick_mid=1.15)
    for i in (2, 4, 8, 10):  # knuckle joints
        m.add(lathe([(5.4, -2), (6.2, 0), (5.4, 2)], 6, col=(234, 224, 200)).move(*pts[i]))
    for i in (3, 9):
        m.add(star3d(4, 7, 3, 2.5, GOLD_L).rot('y', 90).move(*np.add(pts[i], (2, 0, 0))))
    for i in (0, 12):
        m.add(spike(pts[i], (1, np.sign(pts[i][1]) * 0.6, 0), 9, 3, 4, BONE))
    return jitter(m, 0.06, 91)


@item('B09_2', 'Shadowvine bow', 'weapon', BOW_VIEW)
def _():
    m, pts = bow_limbs((100, 60, 146), 112, 24, 4.6, grip_col=(76, 54, 42), recurve=1.6, thick_mid=1.15, n=5)
    for i in (2, 4, 8, 10):
        m.add(ring_band(5.4, 3.8, -1.5, 1.5, (88, 62, 44), 6, 1.0).move(*pts[i]))
    return jitter(m, 0.14, 92)


@item('B09_3', 'Dragonspine bow', 'weapon', BOW_VIEW)
def _():
    m, pts = bow_limbs(BONE_D, 122, 22, 3.4, grip_col=(90, 26, 30))
    P = np.array(pts)
    for i in range(1, len(P) - 1):
        m.add(box(8, 5, 7, BONE).move(*P[i]))
        m.add(spike(P[i], (-1, 0.25 * np.sign(P[i][1]), 0), 10, 2.8, 4, BONE))
        m.add(spike(P[i], (0.3, 0.2 * np.sign(P[i][1]), 1), 5, 1.8, 3, BONE_D))
    for s in (1, -1):  # bat-wing membranes on the belly side
        mem = extrude([(0, 0), (14, s * 6), (24, s * 16), (18, s * 28), (26, s * 38), (12, s * 50), (2, s * 52)],
                      1.4, col=(150, 26, 34))
        m.add(mem.move(-20, s * 4, -1))
        for k in range(3):
            m.add(tube([(-20, s * 6, 0), (-20 + 22 - k * 6, s * (16 + k * 14), 0)], 1.0, 3, (110, 22, 28)))
    for i in (0, 12):
        m.add(spike(pts[i], (1, np.sign(pts[i][1]) * 0.4, 0), 12, 3, 4, BONE))
    return m


@item('B09_4', 'Crystal-root bow', 'weapon', BOW_VIEW)
def _():
    m, pts = bow_limbs(WOOD, 114, 24, 4.6, grip_col=(84, 60, 36), thick_mid=1.15)
    m = jitter(m, 0.14, 94)
    rng = random.Random(94)
    for i in (0, 1, 5, 7, 11, 12):
        for k in range(3):
            g = gem(rng.uniform(3, 4.6), rng.uniform(12, 20), 5, rng.choice([ICE, (90, 205, 220), (160, 240, 236)]))
            g.rot('z', rng.uniform(-80, 80) + (180 if pts[i][1] < 0 else 0)).rot('x', rng.uniform(-30, 30))
            m.add(g.move(*pts[i]))
    for i in (3, 9):
        m.add(ring_band(5.8, 4, -1.6, 1.6, (150, 126, 90), 6, 1.0).move(*pts[i]))
    return m


@item('B09_5', 'Seraph crossbow', 'weapon', XBOW_VIEW)
def _():
    m, pts = crossbow((238, 232, 216), (240, 240, 244), trim=GOLD, limb_r=3.8, stock_w=11, recurve=0.8)
    for p in (pts[0], pts[-1]):
        s = np.sign(p[0])
        for k in range(5):  # feathers fan back from each limb tip
            f = feather(20 - k * 2.4, 5.5, (246, 244, 238), GOLD_L).rot('x', -90)
            f.rot('y', 180 + 40 + k * 16 if s > 0 else -(40 + k * 16))
            m.add(f.move(p[0] - s * 4, 0, p[2] - 4))
    m.add(extrude([(-6, 0), (6, 0), (0, 14)], 4, 1.2, 0.7, col=GOLD).rot('x', -90).move(0, 1, 40))
    for z in (-10, 12):
        m.add(spike((0, 4, z), (0, 1, 0.6), 7, 2.4, 4, GOLD))
    return m


@item('B09_6', 'Runic crossbow', 'weapon', XBOW_VIEW)
def _():
    m, pts = crossbow((58, 62, 68), (46, 50, 56), trim=(36, 40, 44), limb_r=4.4, stock_w=13)
    m = jitter(m, 0.08, 96)
    for z in (-30, -16, -2, 14, 28):
        m.add(glyph(7, (80, 230, 225)).rot('x', -90).rot('y', 90 * (z % 2)).move(0, 4.6, z))
    for x in (-26, -14, 14, 26):
        m.add(glyph(5, (80, 230, 225)).rot('x', -90).rot('z', 90).move(x, 4.2, 30 - abs(x) * 0.25))
    for p in (pts[0], pts[-1]):
        m.add(spike(p, (np.sign(p[0]), 0, 0.6), 8, 2.6, 4, (46, 50, 56)))
    return m


# ============================================================ B10 robes
ASTRAL = (50, 80, 176)
TRIM_S = (204, 208, 222)
WEAVE = (72, 58, 164)


def star_on(m_out, x, y, z, size, col=TRIM_S):
    m_out.add(star3d(4, size, size * 0.38, size * 0.35, col).move(x, y, z))
    return m_out


@item('B10_1', 'Astral wizard hat', 'head', hides=[HAIR])
def _():
    c = HEAD
    pts = bezier((0, c[1] + 4, 0), (0, c[1] + 30, -1), (2, c[1] + 50, -6), (14, c[1] + 54, -18), 10)
    tap = [1.0, 0.86, 0.72, 0.6, 0.48, 0.37, 0.27, 0.19, 0.12, 0.07, 0.03]
    cone = jitter(tube(pts, 21, 12, ASTRAL, taper=tap, up=(1, 0, 0)), 0.07, 101)
    brim = jitter(lathe([(18, c[1] + 3), (40, c[1] - 2), (41, c[1] + 0.5), (18, c[1] + 7)], 16, col=ASTRAL), 0.06, 102)
    brim.add(ring_band(41.4, 38.5, c[1] - 2.6, c[1] + 1.2, TRIM_S, 16, 1.0))
    band = ring_band(21.6, 18.5, c[1] + 4, c[1] + 11, TRIM_S, 12, 1.0)
    m = merge(cone, brim, band)
    star_on(m, 0, c[1] + 24, 18.5, 8.5)
    for a in (-0.9, -0.45, 0.45, 0.9):
        t = FRONT + a
        star_on(m, 22 * math.cos(t), c[1] + 7.5, -22 * math.sin(t), 2.4, ASTRAL)
    return m


@item('B10_2', 'Astral robe top', 'body', hides=[ARMS])
def _():
    m = robe_top(ASTRAL, TRIM_S, bell=1.55, hem_y=82, points=6, finish=lambda q: jitter(q, 0.07, 102))
    star_on(m, 0, 140, 22.5, 7)
    for x, y in ((-12, 152), (12, 152), (-13, 118), (13, 116), (-14, 92), (14, 92)):
        p = body_pt(FRONT - math.atan2(x, 24), y, 2.4)
        star_on(m, p[0], y, p[2], 3.6)
    return m


@item('B10_3', 'Astral robe bottom', 'legs')
def _():
    m = jitter(skirt(ASTRAL, 104, 8, 27, 44, 16, hem=TRIM_S, jag=10, points=True, waist=TRIM_S,
                     panels=(-0.7, 0.7, math.pi)), 0.06, 103)
    star_on(m, 0, 54, 25.5, 9)
    for a, y in ((-1.2, 40), (1.2, 40), (-0.35, 88), (0.35, 88)):
        t = FRONT + a
        r = 27 + (104 - y) / 96 * 17
        star_on(m, r * math.cos(t), y, -r * math.sin(t) * 0.68 + 0.6, 3.2)
    return m


@item('B10_4', 'Runeweaver hood', 'head', hides=[HAIR])
def _():
    h = hood(WEAVE, trim=TRIM_S, peak=12, lean=14, seed=104, finish=lambda q: jitter(q, 0.07, 104))
    return merge(h, glyph(18, RUNE, 1.8).rot('x', -24).move(0, 208, 23))


@item('B10_5', 'Runeweaver robe top', 'body', hides=[ARMS])
def _():
    m = robe_top(WEAVE, TRIM_S, bell=1.55, hem_y=80, points=7, finish=lambda q: jitter(q, 0.07, 105))
    m.add(glyph(26, RUNE, 2.0).move(0, 128, 22))
    for s in (1, -1):
        for y in (150, 120, 92):
            m.add(box(3.2, 3.2, 1.2, (40, 32, 100)).rot('z', 45).move(*body_pt(FRONT + s * 0.22, y, 2.6)))
    return m


@item('B10_6', 'Runeweaver robe skirt', 'legs')
def _():
    m = jitter(skirt(WEAVE, 104, 8, 27, 44, 16, hem=TRIM_S, jag=10, points=True, waist=TRIM_S,
                     panels=(-0.5, 0.5, -1.4, 1.4)), 0.06, 106)
    m.add(extrude([(-9, 0), (9, 0), (12, -84), (-12, -84)], 1.6, col=(60, 48, 140)).rot('x', -8.5).move(0, 98, 20.5))
    m.add(glyph(30, RUNE, 2.0).rot('x', -8).move(0, 58, 25.5))
    return m


# ============================================================ B11 void / staves
def void_finish(seed, seeds=26):
    def fin(q):
        q = cracks(q, seeds, VOID_G, True, seed, warp=0.3)
        return jitter(speckle(q, 0.05, (120, 90, 200), False, seed), 0.08, seed)
    return fin


@item('B11_1', 'Voidwoven hood', 'head', hides=[HAIR])
def _():
    return hood(VOID, inner=(8, 6, 12), peak=10, lean=10, seed=111, finish=void_finish(111, 12),
                mantle_col=(30, 26, 46), jag=8)


@item('B11_2', 'Voidwoven robe top', 'body', hides=[ARMS])
def _():
    m = robe_top(VOID, None, bell=1.45, hem_y=86, points=5, finish=void_finish(112, 22), lapels=False,
                 collar_col=(30, 26, 46), sash=(58, 46, 96), subdiv=0)
    m.add(box(8, 6, 4, (58, 46, 96)).move(0, 103, 20))
    return m


@item('B11_3', 'Voidwoven robe skirt', 'legs')
def _():
    m = void_finish(113, 16)(skirt(VOID, 104, 10, 27, 38, 16, jag=10, points=True, waist=(58, 46, 96)))
    for s in (1, -1):
        m.add(tube([(s * 3, 101, 19), (s * 6, 84, 22), (s * 5, 70, 22)], 2.2, 4, (58, 46, 96)))
    m.add(sphere(4.2, 6, 3, col=(58, 46, 96)).move(0, 101, 20))
    return m


@item('B11_4', 'Stormcaller staff', 'weapon', WEAPON_VIEW)
def _():
    L = 74
    top = 0.7 * L  # staff_shaft spans y = -0.3L .. 0.7L
    s = staff_shaft(L, (40, 34, 60), 3.6, (130, 90, 220), wrap=(54, 46, 80), pommel=(60, 50, 90))
    claw = Mesh()
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        p0 = np.array([0, top - 1, 0])
        pts = bezier(p0, p0 + [7 * math.cos(a), 6, 7 * math.sin(a)], p0 + [6 * math.cos(a), 16, 6 * math.sin(a)], None, 4)
        claw.add(tube(pts, 2.2, 4, (50, 44, 80), taper=[1, 0.9, 0.7, 0.5, 0.25]))
    rng = random.Random(114)
    core = Mesh()
    for k in range(7):
        g = gem(rng.uniform(3, 5), rng.uniform(14, 24), 5, rng.choice([(70, 150, 255), (110, 190, 255), (60, 120, 240)]))
        g.rot('z', rng.uniform(-30, 30)).rot('x', rng.uniform(-30, 30))
        core.add(g.move(rng.uniform(-3, 3), top + 9, rng.uniform(-3, 3)))
    core.G = [True] * len(core.F)
    bolts = Mesh()
    for k in range(6):
        a = 2 * math.pi * k / 6
        p = [0, top + 13, 0]
        pts = [tuple(p)]
        for j in range(4):
            p = [p[0] + 3.4 * math.cos(a) + rng.uniform(-2.5, 2.5), p[1] + 5 + rng.uniform(-1, 2),
                 p[2] + 3.4 * math.sin(a) + rng.uniform(-2, 2)]
            pts.append(tuple(p))
        b = tube(pts, 1.2, 3, (170, 220, 255), taper=[1, 0.85, 0.6, 0.4, 0.2])
        b.G = [True] * len(b.F)
        bolts.add(b)
    return merge(s, claw, core, bolts)


@item('B11_5', 'Solar sceptre', 'weapon', WEAPON_VIEW)
def _():
    L = 66
    top = 0.7 * L
    hy = top + 15
    s = staff_shaft(L, GOLD_D, 3.4, GOLD, pommel=GOLD)
    hoop = ring_band(16, 11, -3, 3, GOLD, 14, 1.0).rot('x', 90).move(0, hy, 0)
    inner = extrude([(math.cos(a) * 11, math.sin(a) * 11) for a in np.linspace(0, 2 * math.pi, 15)[:-1]],
                    3, col=(40, 34, 46)).move(0, hy, -0.5)
    rays = Mesh()
    for k in range(10):
        a = 2 * math.pi * k / 10 + math.pi / 2
        rays.add(spike((16 * math.cos(a), hy + 16 * math.sin(a), 0), (math.cos(a), math.sin(a), 0), 8, 2.8, 4, GOLD))
    orb = sphere(6.5, 8, 4, col=(250, 214, 96)).move(0, hy, 2)
    orb.G = [True] * len(orb.F)
    neck = lathe([(3.4, top - 9), (6.5, top - 3), (5, top + 1), (3, top + 3)], 8, col=GOLD)
    return merge(s, hoop, inner, rays, orb, neck)


@item('B11_6', 'Necrotic soulstaff', 'weapon', WEAPON_VIEW)
def _():
    L = 70
    top = 0.7 * L
    s = staff_shaft(L, (40, 38, 46), 3.4, (110, 90, 140), wrap=(56, 52, 64), pommel=(70, 64, 80))
    sk = jitter(necro_skull(1.8, eye=(200, 255, 160), col=(90, 210, 120)), 0.1, 116).move(0, top + 8, 0)
    flames = Mesh()
    rng = random.Random(116)
    for k in range(9):
        a = 2 * math.pi * k / 9
        flames.add(spike((6 * math.cos(a), top + 16, 5 * math.sin(a)), (math.cos(a) * 0.5, 1, math.sin(a) * 0.5),
                         rng.uniform(14, 24), 3.6, 4, rng.choice([(110, 230, 120), (70, 190, 100), (140, 245, 150)])))
    flames.G = [True] * len(flames.F)
    return merge(s, flames, sk, lathe([(3.4, top - 10), (7, top - 4), (6, top)], 6, col=(60, 56, 70)))


# ============================================================ B12 exotic weapons
@item('B12_1', 'Abyssal tidewhip', 'weapon', dict(yaw=-10, pitch=24))
def _():
    pts = bezier((0, 0, 0), (34, 26, 0), (-36, 52, 0), (6, 86, 4), 22)
    pts = np.vstack([pts, bezier(pts[-1], pts[-1] + [16, 8, 0], pts[-1] + [20, -4, 0], None, 4)[1:]])
    out = Mesh()
    teal = (82, 128, 124)
    for i in range(len(pts) - 1):  # chunky stone segments
        r = 7.0 * (1 - i / len(pts)) + 2.2
        out.add(tube([pts[i], pts[i] * 0.35 + pts[i + 1] * 0.65], r, 6, shade(teal, 1.0 + 0.1 * (i % 2))))
    out = jitter(cracks(out, 20, CYAN, True, 121, warp=0.5), 0.08, 121)
    h = wrapped_handle(24, 4.2, (54, 84, 82), wrap=(40, 64, 62), y0=-24, cap=(90, 150, 150), pommel=(90, 150, 150))
    return merge(out, h)


@item('B12_2', 'Seraph longsword', 'weapon', WEAPON_VIEW)
def _():
    b = blade(70, 16, (240, 240, 244), thick=3.6, edge_col=(212, 216, 224), base_y=3, taper_end=0.6, tip=0.2, belly=0.05)
    fuller = box(2.6, 44, 1.0, GOLD).move(0, 30, 1.9)
    guard = crossguard(16, GOLD, 5.5, 7, flare=0, curl=3)
    wings_ = Mesh()
    for s in (1, -1):
        for k in range(5):
            f = feather(20 - k * 2.4, 5, (246, 246, 248), GOLD_L).rot('z', 10 + k * 20)
            wings_.add((f if s > 0 else f.mirrored()).move(s * 6, 1, 0))
    gemc = gem_like(3.6, CYAN, 4).rot('x', 90).scale(1, 1, 0.6).move(0, 1, 3.4)
    gemc.add(ring_band(5, 3.6, -1, 1, GOLD, 4, 1.0).rot('x', 90).rot('z', 45).move(0, 1, 3))
    return merge(b, fuller, guard, wings_, gemc, grip(22, 2.8, (70, 46, 32), wrap=(40, 28, 20), pommel=GOLD,
                                                       pommel_r=4.2))


@item('B12_3', 'Bloodfang cleaver', 'weapon', WEAPON_VIEW)
def _():
    poly = [(-6, 0), (7, 0), (10, 10), (15, 14), (11, 18), (16, 26), (12, 30), (17, 38), (12, 42), (16, 52),
            (10, 58), (12, 68), (4, 82), (-4, 72), (-7, 62), (-11, 58), (-8, 48), (-12, 42), (-8, 32), (-11, 24), (-7, 14)]
    b = extrude(poly, 5, 1.6, 0.72, col=(66, 66, 70)).move(0, 3, 0).subdivide()
    b = jitter(cracks(b, 10, (170, 26, 30), False, 123, warp=0.7, width=2.6), 0.1, 123)
    paint_where(b, lambda c, n: abs(n[2]) < 0.6 and c[1] > 10, (150, 150, 156))
    g = crossguard(26, (40, 38, 42), 5, 8, flare=-3, curl=-6)
    for s in (1, -1):
        g.add(spike((s * 12, -5, 0), (s, -0.6, 0), 9, 2.4, 4, (40, 38, 42)))
        g.add(spike((s * 6, 2, 0), (s * 0.4, 1, 0), 7, 2, 4, (40, 38, 42)))
    return merge(b, g, grip(22, 3.0, (40, 30, 30), wrap=(160, 26, 32), pommel=(40, 38, 42), pommel_r=4,
                            pommel_kind='spike'))


@item('B12_4', 'Crimson rapier', 'weapon', WEAPON_VIEW)
def _():
    red, dark = (190, 36, 48), (130, 22, 32)
    b = blade(84, 4.6, red, thick=2.2, base_y=3, taper_end=0.55, tip=0.12)
    hilt = Mesh()
    for s in (1, -1):
        hilt.add(tube(bezier((0, 0, 0), (s * 10, -1, 0), (s * 15, 5, 0), (s * 11, 11, 0), 7), 1.6, 5, dark,
                      taper=[1.3, 1.2, 1.1, 1, 0.9, 0.8, 0.6, 0.4]))
        hilt.add(tube(bezier((0, 0, 0), (s * 6, -6, 0), (s * 10, -10, 0), None, 4), 1.2, 4, dark))
    jewel = gem_like(3.8, (230, 40, 54), 5).rot('x', 90).scale(1, 1, 0.7).move(0, 1, 2.4)
    drop = gem(2.6, 8, 4, (220, 36, 50)).scale(1, -1, 1).move(0, -6, 3)
    return merge(b, hilt, jewel, drop, grip(17, 2.2, dark, wrap=(90, 16, 26), pommel=red, pommel_r=3.2))


@item('B12_5', 'Gilded fang', 'weapon', WEAPON_VIEW)
def _():
    poly = [(-5, 0), (5, 0), (8, 14), (11, 18), (8, 22), (11, 28), (8, 32), (10, 40), (4, 50), (-6, 56), (-14, 58),
            (-6, 50), (-2, 40), (-4, 28), (-6, 14)]
    b = jitter(extrude(poly, 5, 1.8, 0.7, col=GOLD).move(0, 3, 0).subdivide(), 0.1, 125)
    paint_where(b, lambda c, n: abs(n[2]) < 0.55, GOLD_L)
    return merge(b, crossguard(13, GOLD_D, 5, 7), grip(18, 3.0, (60, 40, 26), wrap=(40, 28, 20), pommel=GOLD,
                                                      pommel_r=4))


@item('B12_6', 'Goblin knotclub', 'weapon', WEAPON_VIEW)
def _():
    shaft = jitter(lathe([(4.2, -30), (4.6, -10), (5.4, 0), (7.5, 26), (9.5, 40)], 8, col=(104, 112, 52)), 0.12, 126)
    for y in (-26, -20, 14, 22):
        shaft.add(ring_band(5.2 + (y > 0) * 2.4, 3.8, y, y + 2.4, (84, 92, 40), 8, 1.0))
    knobs = jitter(merge(sphere(12, 9, 6, col=(108, 162, 64)).move(3, 52, 0),
                         sphere(10, 9, 6, col=(100, 154, 58)).move(-9, 40, 4)), 0.1, 127)
    wrap = merge(*[feather(14, 4, (130, 70, 150)).rot('z', 90 + a).move(-4, 22, 6) for a in (-30, 10, 40)])
    sticks = merge(*[tube([(0, 30, 0), (x, 70, z)], 1.0, 4, (150, 108, 60)) for x, z in ((-8, 4), (-4, -4), (-12, 0))])
    rope_ = rope([(math.cos(a) * 8.4, 26 + a, math.sin(a) * 8.4) for a in np.linspace(0, 4 * math.pi, 16)],
                 1.1, (150, 120, 76), (120, 92, 56))
    return merge(shaft, knobs, wrap, sticks, rope_)


# ============================================================ B13 neck & cape
def rope_chain(col, alt, w=22, drop=44, r=1.9):
    pts = bezier((-w, drop, -2), (-w * 0.95, 6, 0), (w * 0.95, 6, 0), (w, drop, -2), 18)
    return rope(pts, r, col, alt, 5)


@item('B13_1', 'Amulet of the sun', 'neck', NECK_VIEW)
def _():
    c = rope_chain(GOLD, GOLD_D).move(0, 14, 0)
    bail = lathe([(2.4, 14), (3.2, 18), (2.4, 22)], 6, col=GOLD)
    star = extrude(star_poly(8, 18, 8), 5, 2.2, 0.5, col=GOLD)
    jewel = gem_like(6.5, (225, 36, 36), 8).rot('x', 90).scale(1, 1, 0.7).move(0, 0, 3.4)
    ring_ = ring_band(8, 6.2, -1, 1.2, GOLD_D, 10, 1.0).rot('x', 90).move(0, 0, 2.6)
    return merge(c, bail, star, jewel, ring_)


@item('B13_2', 'Crimson cord necklace', 'neck', NECK_VIEW)
def _():
    red, dark = (176, 34, 42), (128, 22, 30)
    loop = rope([(18 * math.cos(a), 30 + 22 * math.sin(a), 3 * math.sin(2 * a)) for a in np.linspace(-1.4, 4.54, 22)],
                2.8, red, dark, 5)
    out = merge(loop, sphere(5.2, 7, 4, col=red).move(0, 8, 2), sphere(4.4, 7, 4, col=dark).move(0, 1, 2))
    for s in (1, -1):
        out.add(rope([(0, 2, 2), (s * 3, -10, 3), (s * 5, -18, 3)], 2.0, red, dark, 4))
        out.add(sphere(2.4, 6, 3, col=(70, 70, 76)).move(s * 5, -20, 3))
        out.add(lathe([(0.01, -36), (4.4, -30), (3.6, -24), (2, -22)], 6, col=dark).move(s * 5, 0, 3))
    return out


@item('B13_3', 'Sapphire amulet', 'neck', NECK_VIEW)
def _():
    c = necklace_chain((120, 122, 130), 22, 42, 3.6).move(0, 18, 0)
    frame = extrude([(0, -24), (10, -12), (13, 4), (7, 18), (0, 22), (-7, 18), (-13, 4), (-10, -12)], 5, 1.6, 0.75,
                    col=GOLD)
    inner = extrude([(0, -18), (6, -8), (8, 4), (4, 14), (0, 16), (-4, 14), (-8, 4), (-6, -8)], 1, col=(30, 40, 70)) \
        .move(0, 0, 2.6)
    stone = jitter(gem(6.5, 30, 6, (44, 120, 236)).scale(1, 1, 0.55).move(0, -2, 3.4), 0.12, 133)
    for s in (1, -1):
        for k, (y, L) in enumerate(((10, 9), (-2, 11), (-14, 7))):
            frame.add(spike((s * 10, y, 0), (s, 0.4 - k * 0.3, 0), L, 2.2, 4, GOLD))
    bail = lathe([(2.6, 20), (3.4, 24), (2.4, 28)], 6, col=GOLD)
    drop = gem(2.6, 7, 4, (60, 160, 240)).scale(1, -1, 1).move(0, -27, 1)
    return merge(c, frame, inner, stone, bail, drop)


@item('B13_4', 'Verdant shard amulet', 'neck', NECK_VIEW)
def _():
    c = necklace_chain((84, 86, 92), 22, 40, 3.4).move(0, 14, 0)
    shard = jitter(extrude([(-18, 8), (18, 8), (0, -28)], 9, 3.4, 0.6, col=(96, 126, 56), dome=3).subdivide(), 0.14, 134)
    cap = lathe([(5, 6), (6, 10), (3, 14)], 4, col=(186, 190, 196)).rot('y', 45)
    return merge(c, shard, cap, gem_like(2.2, (90, 160, 80), 4).rot('x', 90).move(0, 10, 3.2))


@item('B13_5', 'Obsidian cape', 'cape', CAPE_VIEW)
def _():
    m = cracks(jitter(cape(OBSID, jag=18, seed=135, folds=5, points=True), 0.1, 135), 20, (220, 70, 30), True, 135)
    clasp = chain(bezier((-22, 166, -8), (-10, 160, 18), (10, 160, 18), (22, 166, -8), 10), 3.6, (90, 90, 96),
                  thick=0.3)
    return merge(m, ring_band(18, 14, 164, 170, (44, 40, 44), 12, 0.8), clasp)


@item('B13_6', 'Magma cape', 'cape', CAPE_VIEW)
def _():
    m = cracks(jitter(cape((160, 50, 22), jag=12, seed=136, folds=4), 0.15, 137), 26, LAVA_HOT, True, 136)
    clasp = merge(ring_band(7, 4.6, -2, 2, GOLD_D, 8, 1.0).rot('x', 90).move(-18, 166, 4),
                  lathe([(0.01, -3), (4, 0), (0.01, 3)], 6, col=GOLD).move(-18, 166, 6))
    return merge(m, ring_band(18, 14, 164, 170, (100, 34, 18), 12, 0.8), clasp)


# ============================================================ B14 shields
@item('B14_1', 'Dragonfire shield', 'shield', SHIELD_VIEW)
def _():
    s = jitter(shield(heater_poly(48, 60, 3), (58, 60, 66), 6, 4, rim=(120, 122, 130)), 0.1, 141)
    for x, y in ((-20, 24), (20, 24), (0, -30)):
        s.add(box(4, 4, 3, (150, 110, 60)).rot('z', 45).move(x, y, 4))
    d = (78, 80, 88)
    head = lathe([(10, -8), (11, 0), (8, 9), (5, 15), (2, 19)], 7, col=d).rot('x', 80).scale(1, 0.9, 1.1)
    head.add(extrude([(-7, 0), (7, 0), (5, -6), (-5, -6)], 12, 2, 0.8, col=shade(d, 0.85)).move(0, -5, 12))
    for sx in (1, -1):
        head.add(horn(sx, (110, 112, 118), 14, 0.9, 2.6, (6, 9, -3), forward=-10))
        head.add(sphere(1.8, 5, 2, col=(255, 150, 40)).move(sx * 5, 4, 15))
        for k in range(3):
            head.add(spike((sx * (4 + k * 3), 8 + k, -2 - k * 2), (sx * 0.4, 1, -0.4), 8, 2, 4, (96, 98, 104)))
    for k in range(4):
        head.add(spike((-3 + k * 2, -2, 18), (0, -1, 0.3), 3, 0.8, 3, BONE))
    head = jitter(head, 0.1, 142).scale(1.45).rot('z', 18).move(-7, 14, 6)
    fire = Mesh()
    rng = random.Random(141)
    for k in range(12):
        col = rng.choice([LAVA, LAVA_HOT, (255, 80, 20)])
        fire.add(spike((0, 0, 0), (-1, rng.uniform(-0.4, 0.4), rng.uniform(0, 0.6)), rng.uniform(8, 20),
                       rng.uniform(1.4, 3), 4, col).move(-12 + rng.uniform(-2, 2), rng.uniform(-3, 3), 22))
    fire.G = [True] * len(fire.F)
    return merge(s, head, fire.move(-6, 4, 0))


@item('B14_2', 'Glacial crystal shield', 'shield', SHIELD_VIEW)
def _():
    poly = [(0, -36), (14, -22), (22, 0), (20, 22), (8, 36), (0, 32), (-8, 36), (-20, 22), (-22, 0), (-14, -22)]
    s = jitter(shield(poly, (70, 190, 200), 9, 6).subdivide(), 0.2, 142)
    rng = random.Random(142)
    s.add(tube([(rng.uniform(-3, 3), y, 7.5) for y in np.linspace(-30, 30, 9)], 2.0, 4, (12, 30, 40)))
    for k in range(14):
        a = 2 * math.pi * k / 14
        g = gem(rng.uniform(3.5, 5.5), rng.uniform(12, 22), 5, rng.choice([ICE, (90, 200, 214), (160, 238, 240)]))
        s.add(g.rot('z', math.degrees(a) - 90).move(23 * math.cos(a), 33 * math.sin(a), rng.uniform(-2, 2)))
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        s.add(spike((25 * math.cos(a), 34 * math.sin(a), -2), (math.cos(a), math.sin(a), 0), 7, 2, 4, (160, 164, 172)))
    return s


@item('B14_3', 'Solar heater shield', 'shield', SHIELD_VIEW)
def _():
    s = jitter(shield(heater_poly(48, 60, 4), GOLD, 6, 3, rim=GOLD_D), 0.06, 143)
    sun = sunburst(GOLD_L, 16, 7, 18, 3.4, alt=0.55, bevel=0.5).move(0, 4, 5)
    core = gem_like(6.5, (250, 214, 100), 8).rot('x', 90).scale(1, 1, 0.7).move(0, 4, 7.5)
    return merge(s, sun, core)


@item('B14_4', 'Jade thorn shield', 'shield', SHIELD_VIEW)
def _():
    rng = random.Random(144)
    poly = []
    for k in range(28):
        a = 2 * math.pi * k / 28 + math.pi / 2
        r = 28 + (7 if k % 3 == 0 and k != 0 else 0) + rng.uniform(-2, 2)
        poly.append((r * math.cos(a) * 0.82, r * math.sin(a) * 1.1 - (6 if math.sin(a) < -0.5 else 0)))
    return jitter(shield(poly, (156, 206, 176), 8, 6).subdivide(), 0.12, 145)


@item('B14_5', 'Sapphire dragon kiteshield', 'shield', SHIELD_VIEW)
def _():
    s = jitter(shield(kite_poly(48, 64), (40, 72, 176), 6, 3, rim=(204, 208, 218)), 0.08, 146)
    emb = Mesh()
    body_ = [(0, -18), (6, -8), (9, 4), (5, 10), (10, 16), (3, 14), (0, 20), (-4, 12), (-9, 6), (-6, -6)]
    emb.add(extrude(body_, 3.4, 1.2, 0.6, col=(80, 150, 245)).subdivide())
    for sx in (1, -1):
        emb.add(extrude([(0, 0), (sx * 12, 10), (sx * 9, 2), (sx * 13, -2), (sx * 6, -4)], 2, col=(60, 120, 230))
                .move(sx * 3, 2, -0.4))
    emb = jitter(emb, 0.15, 147).move(0, 2, 4.6)
    emb.G = [True] * len(emb.F)
    out = merge(s, emb)
    for x, y in ((-14, 17), (14, 17), (-13, -8), (13, -8), (0, -26)):
        out.add(star3d(4, 4.4, 1.6, 1.8, (226, 230, 238)).move(x, y, 4.2))
    return out


@item('B14_6', 'Crimson spiked roundshield', 'shield', SHIELD_VIEW)
def _():
    s = jitter(shield(circle2d(29, 16), (156, 36, 44), 7, 6), 0.12, 148).subdivide()
    s.add(tube([(-14, 22, 4), (-6, 8, 7), (2, -4, 7), (10, -20, 4)], 2.2, 4, (180, 182, 188)))
    for k in range(12):
        a = 2 * math.pi * k / 12
        s.add(spike((30 * math.cos(a), 30 * math.sin(a), 0), (math.cos(a), math.sin(a), 0.25), 11, 3.2, 4,
                    (200, 202, 208)))
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        s.add(spike((15 * math.cos(a), 15 * math.sin(a), 5), (math.cos(a) * 0.4, math.sin(a) * 0.4, 1), 6, 2, 4,
                    (200, 202, 208)))
    return s
