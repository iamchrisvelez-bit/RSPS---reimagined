"""The 84 redesigns from the reference sheet (B01..B14, six per batch,
read left-to-right, top-to-bottom)."""
import math
import random

import numpy as np
from .geom import (Mesh, merge, lathe, prism, box, sphere, gem, spike, tube, bezier, torus, chain,
                   extrude, circle2d, shade, mix, _align_y_to)
from .parts import (HEAD, arm, axe_head, bands, belt, blade, bow_limbs, cape, collar, cracks, crossbow,
                    crossguard, drape, gauntlets, greaves, grip, handle, heater_poly, helm_shell, hood, horn,
                    jitter, kite_poly, leg, necklace_chain, pauldron, platebody, platelegs, rivets, robe_top,
                    shield, skirt, staff_shaft, star_poly, sunburst, tassets, torso, visor, wing)

# ------------------------------------------------------------------ palette
GOLD = (222, 172, 60)
GOLD_D = (160, 115, 35)
SILVER = (205, 208, 215)
STEEL_D = (70, 72, 78)
BONE = (214, 200, 170)
BONE_D = (150, 135, 110)
LEATHER = (92, 62, 40)
WOOD = (110, 74, 44)
OBSID = (34, 30, 32)
LAVA = (255, 116, 28)
LAVA_HOT = (255, 190, 70)
NECRO = (128, 124, 112)
NECRO_G = (130, 235, 80)
BLOOD = (150, 24, 30)
CYAN = (90, 220, 220)
ICE = (110, 210, 225)
VOID = (36, 28, 58)
VOID_G = (150, 90, 255)
RUNE_BLUE = (70, 170, 255)

ITEMS = []


def item(code, name, slot, view=None, desc=''):
    def deco(fn):
        ITEMS.append(dict(code=code, name=name, slot=slot, build=fn, view=view or {}, desc=desc))
        return fn
    return deco


WEAPON_VIEW = dict(roll=-42, yaw=-18, pitch=10)
SHIELD_VIEW = dict(yaw=-28, pitch=12)
BOW_VIEW = dict(roll=-38, yaw=-12, pitch=8)
XBOW_VIEW = dict(yaw=-55, pitch=38)
NECK_VIEW = dict(yaw=-10, pitch=8)


def lava(m, seeds=14, w=2.0, seed=0, col=LAVA, subdiv=2):
    for _ in range(subdiv):
        m = m.subdivide()
    return cracks(m, int(seeds * 1.6), w * 0.55, col, True, seed)


def glow_runes(m, col, seeds=18, w=1.4, seed=3, subdiv=1):
    for _ in range(subdiv):
        m = m.subdivide()
    return cracks(m, seeds, w * 0.6, col, True, seed)


# ======================================================== B01 platebodies
@item('B01_1', 'Copper scale platebody', 'body')
def _():
    m = platebody((186, 112, 70), trim=(128, 72, 42), pattern='scale', seed=11)
    return rivets(m, (225, 170, 120), 150, 7)


@item('B01_2', 'Iron platebody', 'body')
def _():
    return platebody((112, 113, 118), trim=(84, 85, 90), pattern='plates', seed=12, pauldron_layers=3)


@item('B01_3', 'Steel platebody', 'body')
def _():
    return platebody((178, 181, 188), trim=(140, 143, 150), pattern='plates', seed=13, pauldron_layers=3,
                     pauldron_size=1.08)


@item('B01_4', 'Shadowsteel platebody', 'body')
def _():
    return platebody((44, 40, 54), dark=(28, 26, 34), trim=(58, 52, 72), pattern='veins',
                     accent=(140, 70, 225), seed=14, pauldron_layers=3)


@item('B01_5', 'Silver filigree platebody', 'body')
def _():
    return platebody((200, 210, 222), trim=(232, 236, 242), pattern='filigree', accent=(140, 156, 178),
                     seed=15, pauldron_layers=3, sleeve_col=(150, 160, 175))


@item('B01_6', 'Jade crystal platebody', 'body')
def _():
    m = platebody((44, 134, 98), dark=(26, 84, 60), trim=(70, 170, 125), pattern='crystal', seed=16,
                  pauldron_layers=2)
    for s in (1, -1):
        for k in range(3):
            m.add(gem(4.5, 13, 5, (80, 190, 140)).rot('z', -s * (35 + k * 18)).move(s * (34 + k * 2), 166 - k * 4, k * 3 - 3))
    return m


# ===================================================== B02 sapphire / crimson / magma tools
@item('B02_1', 'Royal sapphire platebody', 'body')
def _():
    m = platebody((44, 74, 196), dark=(26, 40, 120), trim=GOLD, pattern='crystal', seed=21,
                  pauldron_layers=2, pauldron_size=1.1)
    return m


@item('B02_2', 'Crimson dragonscale body', 'body')
def _():
    m = platebody((176, 32, 42), dark=(110, 18, 26), trim=(130, 20, 28), pattern='crystal', seed=22,
                  spikes=4, accent=(205, 50, 58), arms=False)
    for k in range(18):
        a = 2 * math.pi * k / 18
        m.add(spike((29 * math.cos(a), 130 + (k % 3) * 12, -19 * math.sin(a)),
                    (math.cos(a), 0.6, -math.sin(a)), 9, 3, 4, (190, 40, 50)))
    return m


@item('B02_3', 'Crimson crystal scimitar', 'weapon', WEAPON_VIEW)
def _():
    b = blade(64, 10, (200, 30, 44), curve=1.0, edge_col=(240, 70, 80), thick=3.0)
    jitter(b, 0.18, 23)
    return merge(b, crossguard(16, (150, 20, 30), 4, 5, flare=2, curl=3),
                 grip(16, 2.4, (110, 18, 26), wrap=(70, 12, 18)), sphere(3.2, 6, 3, col=(200, 30, 44)).move(0, -18, 0))


def pick_head(col, edge=None, span=58, r=4.2):
    pts = bezier((-span / 2, -6, 0), (-span / 4, 6, 0), (span / 4, 6, 0), (span / 2, -6, 0), 8)
    tap = [0.3, 0.7, 0.95, 1.1, 1.25, 1.1, 0.95, 0.7, 0.3]
    m = tube(pts, r, 5, col, taper=tap, up=(0, 0, 1))
    return m


@item('B02_4', 'Sapphire pickaxe', 'weapon', WEAPON_VIEW)
def _():
    h = handle(70, 2.8, (34, 52, 140), cap=GOLD, y0=-40)
    head = pick_head((40, 76, 210)).move(0, 30, 0)
    jitter(head, 0.12, 24)
    return merge(h, head, box(8, 9, 8, GOLD).move(0, 29, 0))


@item('B02_5', 'Magma pickaxe', 'weapon', WEAPON_VIEW)
def _():
    h = lava(handle(70, 3.0, OBSID, cap=(70, 40, 30), y0=-40), 10, 1.6, 25)
    head = lava(pick_head(OBSID, span=60, r=4.6).move(0, 30, 0), 14, 1.6, 26, subdiv=1)
    return merge(h, head, box(9, 10, 9, (60, 34, 26)).move(0, 29, 0))


@item('B02_6', 'Magma hatchet', 'weapon', WEAPON_VIEW)
def _():
    h = lava(handle(66, 3.2, OBSID, cap=(70, 40, 30), y0=-38), 10, 1.6, 27)
    head = axe_head([(0, -10), (14, -16), (24, -20), (26, 0), (24, 18), (14, 13), (0, 8)], 7, OBSID,
                    at=(1, 22, 0))
    head = lava(head, 12, 1.8, 28, subdiv=1)
    spikeb = extrude([(0, -4), (-12, 2), (0, 5)], 4, col=OBSID).move(-2, 22, 0)
    return merge(h, head, spikeb, box(7, 13, 8, (70, 40, 30)).move(0, 22, 0))


# ===================================================== B03 necrotic arsenal
def necro_skull(scale=1.0, eye=NECRO_G):
    s = sphere(5.5, 7, 4, 1.05, BONE).scale(1, 1, 1.05)
    jaw = box(6.5, 3, 5, BONE_D).move(0, -5, 1.2)
    eyes = merge(*[sphere(1.4, 5, 2, col=eye).move(x, 0.6, 4.8) for x in (-2.1, 2.1)])
    eyes.G = [True] * len(eyes.F)
    return merge(s, jaw, eyes).scale(scale)


@item('B03_1', 'Necrotic battleaxe', 'weapon', WEAPON_VIEW)
def _():
    h = glow_runes(handle(84, 3.0, (70, 68, 62), cap=NECRO, y0=-46), NECRO_G, 8, 1.2, 31)
    blade_poly = [(4, -6), (14, -14), (24, -22), (30, -10), (31, 0), (30, 10), (24, 22), (14, 14), (4, 6)]
    a = axe_head(blade_poly, 5, NECRO, edge=(190, 185, 170), at=(0, 30, 0))
    b = a.mirrored()
    for m in (a, b):
        cracks(m, 10, 1.4, NECRO_G, True, 32)
    sk = necro_skull(1.1).move(0, 30, 4)
    return merge(h, a, b, sk, spike((0, 38, 0), (0, 1, 0), 14, 3, 4, NECRO))


@item('B03_2', 'Necrotic spear', 'weapon', WEAPON_VIEW)
def _():
    shaft = glow_runes(handle(100, 2.4, (70, 68, 62), cap=NECRO, y0=-60), NECRO_G, 8, 1.1, 33)
    tipb = blade(30, 9, NECRO, thick=3.0, edge_col=(190, 185, 170), base_y=40)
    barbs = merge(*[spike((s * 3, 44 + k * 6, 0), (s * 0.8, -0.6, 0), 8, 1.6, 3, NECRO)
                    for s in (1, -1) for k in range(3)])
    collar_ = prism(4, 3.4, 8, 6, 34, col=(160, 155, 140))
    return merge(shaft, tipb, barbs, collar_)


def spiked_ball(r, col, spikes=10, spike_col=None, glow=None, seed=0):
    b = sphere(r, 8, 5, col=col)
    if glow:
        b = b.subdivide()
        cracks(b, 8, 1.4, glow, True, seed)
    dirs = [(0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1),
            (0.7, 0.7, 0), (-0.7, 0.7, 0), (0, 0.7, 0.7), (0, 0.7, -0.7), (0.7, -0.7, 0),
            (-0.7, -0.7, 0), (0, -0.7, 0.7), (0, -0.7, -0.7)][:spikes]
    for d in dirs:
        d = np.array(d) / np.linalg.norm(d)
        b.add(spike(d * r * 0.85, d, r * 0.75, r * 0.3, 4, spike_col or col))
    return b


@item('B03_3', 'Necrotic flail', 'weapon', WEAPON_VIEW)
def _():
    h = handle(46, 3.0, (70, 68, 62), cap=NECRO, y0=-30)
    ch = chain(bezier((0, 18, 0), (8, 30, 0), (18, 34, 0), (26, 28, 0), 10), 3.6, (110, 110, 105))
    ball = spiked_ball(9, NECRO, 14, (175, 170, 155), NECRO_G, 34).move(30, 22, 0)
    return merge(h, prism(4, 4, 4, 6, 16, col=NECRO), ch, ball)


def hammer(col, glow=None, seed=0):
    h = handle(54, 2.8, (70, 68, 62), cap=col, y0=-30)
    head = box(26, 14, 14, col).subdivide()
    jitter(head, 0.1, seed)
    if glow:
        cracks(head, 8, 1.4, glow, True, seed)
    for s in (1, -1):
        head.add(prism(8, 8.5, 4, 6, -2, col=shade(col, 0.8)).rot('z', -90 * s).move(s * 13, 0, 0))
    return merge(h, head.move(0, 26, 0), spike((0, 33, 0), (0, 1, 0), 9, 2.6, 4, col))


@item('B03_4', 'Necrotic twin mauls', 'weapon', dict(yaw=-15, pitch=10))
def _():
    a = hammer(NECRO, NECRO_G, 35).rot('z', 24).move(-14, 0, 0)
    b = hammer(NECRO, NECRO_G, 36).rot('z', -24).move(14, 0, 0)
    return merge(a, b)


@item('B03_5', 'Necrotic crossbow', 'weapon', XBOW_VIEW)
def _():
    m, pts = crossbow((150, 144, 128), BONE, trim=NECRO_G)
    m.add(necro_skull(0.8).move(0, 6, 4))
    for p in (pts[0], pts[-1]):
        m.add(spike(p, (np.sign(p[0]), 0, -0.4), 8, 2, 4, BONE))
    return glow_runes(m, NECRO_G, 10, 1.2, 37, 0)


@item('B03_6', 'Necrotic skull censer', 'weapon', WEAPON_VIEW)
def _():
    h = handle(60, 2.8, (70, 68, 62), cap=NECRO, y0=-34)
    hoop = torus(16, 2.4, 12, 4, NECRO).move(0, 44, 0)
    for k in range(10):
        a = 2 * math.pi * k / 10
        hoop.add(spike((18 * math.cos(a), 44 + 18 * math.sin(a), 0), (math.cos(a), math.sin(a), 0), 8, 2, 3, NECRO))
    sk = necro_skull(1.5).move(0, 44, 0)
    chains = merge(chain([(-12, 30, 0), (-14, 14, 0)], 2.6, (110, 110, 105)),
                   chain([(12, 30, 0), (14, 14, 0)], 2.6, (110, 110, 105)))
    return merge(h, hoop, sk, chains, prism(4, 4, 5, 6, 24, col=NECRO))


# =========================================================== B04 bloodbone
RED_D = (96, 26, 28)
BRN = (60, 36, 30)


def reaver_body():
    m = platebody(BRN, dark=(40, 26, 22), trim=RED_D, pattern='veins', accent=(170, 30, 36),
                  seed=41, spikes=4, pauldron_layers=3, pauldron_size=1.15, skirt=True, skirt_col=(76, 34, 30))
    for k in range(5):
        m.add(spike((-15 + k * 7.5, 168, -10), (0, 0.5, -1), 9, 2.4, 4, BONE_D))
    return m


@item('B04_1', 'Reaver platebody', 'body')
def _():
    return reaver_body()


@item('B04_2', 'Reaver platelegs', 'legs')
def _():
    m = platelegs(BRN, RED_D, pattern='plates', seed=42)
    m.add(tassets((76, 34, 30), RED_D, 7, 104, 34, jag=True))
    for s in (1, -1):
        m.add(spike((s * 13, 56, 10), (0, 0.4, 1), 8, 2.6, 4, BONE_D))
    return glow_runes(m, (165, 28, 34), 18, 1.2, 43, 0)


@item('B04_3', 'Reaver warboots', 'feet')
def _():
    m = greaves(BRN, RED_D, 44)
    for s in (1, -1):
        for k in range(3):
            m.add(spike((s * 21, 12 + k * 12, 0), (s, 0.3, 0), 7, 2.2, 4, BONE_D))
    return m


@item('B04_4', 'Horned bone helm', 'head')
def _():
    h = helm_shell(BONE, 22.5, 1.15)
    visor(h, (30, 18, 16), 'face', z_min=14)
    cracks(h, 14, 1.3, (150, 30, 30), False, 44)
    jitter(h, 0.06, 45)
    parts = [h]
    for s in (1, -1):
        parts.append(horn(s, (226, 214, 186), 38, 1.0, 4.8, (15, 204, 0)))
        parts.append(spike((s * 10, 186, 22), (s * 0.3, -1, 0.4), 12, 2.6, 4, BONE))  # fangs
    parts.append(box(3, 16, 4, BONE_D).move(0, 196, 24))  # nasal ridge
    return merge(*parts)


@item('B04_5', 'Ribcage platebody', 'body')
def _():
    sp = tube([(0, 100, -16), (0, 135, -19), (0, 168, -14)], 3.4, 6, BONE_D)
    parts = [sp, torso((70, 18, 20), 10, bulk=0.9)]
    parts.append(box(5, 50, 4, BONE).move(0, 136, 19))  # sternum
    for k in range(7):
        y = 160 - k * 8.5
        w = 31 - abs(k - 2.5) * 1.6
        # one rib arcs around the front of the chest from side to side
        pts = [(w * math.cos(a), y + 4 * math.sin(a), 19.5 * math.sin(a))
               for a in np.linspace(math.pi * 0.05, math.pi * 0.95, 9)]
        parts.append(tube(pts, 2.6, 5, BONE))
    for s in (1, -1):
        parts.append(pauldron(BONE, s, 1.05, 2, (130, 26, 30), 2, BONE_D))
        parts.append(arm((70, 18, 20), s, 7, cuff=BONE))
    m = merge(*parts)
    return m


@item('B04_6', 'Bone bracers', 'hands')
def _():
    m = gauntlets(BONE, (130, 26, 30), claws=BONE_D, seed=46, spikes=True)
    return cracks(m.subdivide(), 10, 1.3, (140, 28, 30), False, 47)


# ============================================================ B05 knights
@item('B05_1', 'Crimson knight helm', 'head')
def _():
    h = helm_shell((84, 86, 92), 22.5, 1.12, top=1.15)
    visor(h, (12, 12, 14), 'slit', 191)
    h.add(box(3, 30, 3, GOLD).move(0, 200, 24.5))
    h.add(torus(23, 1.5, 12, 3, GOLD).rot('x', 90).scale(1, 1, 1.12).move(0, 181, 2))
    return merge(h, drape((120, 22, 30), 176, 132, 20, 38, 12, jag=8, seed=51))


@item('B05_2', 'Crimson chain hauberk', 'body')
def _():
    m = platebody((92, 94, 100), dark=(60, 62, 68), trim=GOLD, pattern='chain', seed=52,
                  pauldron_layers=2, sleeve_col=(80, 82, 88), collar_col=(30, 30, 34))
    m.add(extrude([(-13, 0), (13, 0), (15, -46), (0, -54), (-15, -46)], 2, col=(130, 24, 32))
          .rot('x', -4).move(0, 116, 21))  # tabard
    m.add(tassets((120, 22, 30), GOLD, 7, 101, 26, jag=True))
    return m


@item('B05_3', 'Crimson knight tassets', 'legs')
def _():
    s = skirt((124, 24, 32), 106, 46, 28, 41, 12, hem=GOLD_D, jag=10, seed=53, trim=(50, 46, 44),
              front_panel=(150, 30, 40))
    s.add(sunburst(GOLD, 6, 3, 6, 2).move(0, 90, 25))
    for side in (1, -1):
        s.add(leg((60, 60, 66), side, 9.5))
    return s


@item('B05_4', 'Paladin full helm', 'head')
def _():
    h = helm_shell((235, 235, 238), 22.5, 1.12, top=1.1)
    visor(h, (20, 22, 30), 'grille', z_min=12)
    h.add(box(3, 34, 3, GOLD).move(0, 198, 24.5))
    h.add(torus(23, 1.6, 12, 3, GOLD).rot('x', 90).scale(1, 1, 1.12).move(0, 172, 2))
    return merge(h, drape((50, 74, 150), 175, 136, 20, 36, 12, jag=6, seed=54))


@item('B05_5', 'Paladin platebody', 'body')
def _():
    m = platebody((236, 236, 240), dark=(200, 200, 208), trim=GOLD, pattern='plates', seed=55,
                  pauldron_layers=2, sleeve_col=(60, 84, 150))
    m.add(sunburst(GOLD, 5, 3, 6.5, 2).move(0, 145, 21))
    return m


@item('B05_6', 'Paladin greaves', 'feet')
def _():
    return greaves((236, 236, 240), GOLD, 56)


# ============================================================ B06 magma set
@item('B06_1', 'Magma helm', 'head')
def _():
    h = helm_shell(OBSID, 22.5, 1.12, top=1.05)
    visor(h, (8, 6, 6), 'T', z_min=12)
    return lava(h, 22, 1.6, 61, subdiv=1)


@item('B06_2', 'Magma platebody', 'body')
def _():
    return platebody(OBSID, dark=(24, 20, 22), trim=(50, 36, 30), pattern='lava', glow_col=LAVA, seed=62,
                     pauldron_layers=2)


@item('B06_3', 'Magma gauntlets', 'hands')
def _():
    return gauntlets(OBSID, (50, 36, 30), glow=LAVA, seed=63)


@item('B06_4', 'Magma dagger', 'weapon', WEAPON_VIEW)
def _():
    b = lava(blade(30, 8, OBSID, thick=3, tip=0.3), 8, 1.5, 64, subdiv=1)
    return merge(b, crossguard(12, (50, 36, 30), 4, 5), grip(13, 2.4, OBSID, wrap=(60, 40, 30),
                                                                  pommel=(70, 40, 30), pommel_r=3))


@item('B06_5', 'Magma mace', 'weapon', WEAPON_VIEW)
def _():
    h = lava(handle(46, 3.2, OBSID, cap=(50, 36, 30), y0=-26), 6, 1.4, 65)
    head = lava(sphere(13, 8, 5, 1.1, OBSID).move(0, 28, 0), 18, 2.2, 66, subdiv=2)
    jitter(head, 0.1, 67)
    return merge(h, head)


@item('B06_6', 'Magma kiteshield', 'shield', SHIELD_VIEW)
def _():
    s = shield(kite_poly(46, 62), OBSID, 7, 5, rim=(44, 32, 28))
    return lava(s, 22, 2.2, 68)


# ============================================================ B07 rangers / valkyrie
def ranger_tunic(base, seed):
    dark = shade(base, 0.7)
    t = torso(base, 12, bulk=1.04).subdivide()
    jitter(t, 0.08, seed)
    parts = [t]
    for s in (1, -1):
        parts.append(jitter(arm(base, s, 8.2, cuff=dark).subdivide(), 0.08, seed + s))
        parts.append(pauldron(dark, s, 0.9, 1))
    parts.append(belt(LEATHER, 102, 6, (150, 120, 70)))
    strap = tube([(-26, 108, 18), (0, 135, 22), (22, 165, 12)], 2.2, 4, LEATHER)
    parts.append(strap)
    parts.append(hood(base, (12, 10, 12), mantle=True, peak=6, seed=seed))
    return merge(*parts)


@item('B07_1', 'Woodland ranger tunic', 'body')
def _():
    return ranger_tunic((86, 122, 56), 71)


@item('B07_2', 'Tidewalker ranger tunic', 'body')
def _():
    return ranger_tunic((52, 84, 156), 72)


@item('B07_3', 'Emberhide ranger tunic', 'body')
def _():
    return ranger_tunic((164, 52, 42), 73)


@item('B07_4', 'Nightstalker ranger tunic', 'body')
def _():
    return ranger_tunic((46, 46, 52), 74)


@item('B07_5', 'Valkyrie winged helm', 'head')
def _():
    h = helm_shell((236, 236, 240), 22.5, 1.12)
    visor(h, (20, 22, 30), 'face', z_min=15)
    h.add(box(3, 26, 3, GOLD).move(0, 202, 24))
    for s in (1, -1):
        h.add(wing(s, (60, 90, 170), GOLD, 1.15))
    return h


@item('B07_6', 'Valkyrie platebody', 'body')
def _():
    m = platebody((236, 236, 240), dark=(190, 192, 200), trim=GOLD, pattern='plates', seed=76,
                  pauldron_layers=3, pauldron_size=1.15, sleeve_col=(52, 80, 160))
    m.add(extrude([(-12, 6), (12, 6), (0, -14)], 3, col=GOLD).move(0, 148, 21))
    for s in (1, -1):
        m.add(wing(s, (240, 240, 244), GOLD, 0.6, at=(34, 172, -2), feathers=4))
    return m


# ============================================================ B08 seraph / solar / verdant
@item('B08_1', 'Seraph feather mantle', 'cape')
def _():
    out = Mesh()
    for row in range(3):
        n = 14 - row * 2
        for k in range(n):
            a = 2 * math.pi * k / n + row * 0.2
            L = 30 - row * 7
            f = extrude([(-4, 0), (4, 0), (2.5, -L), (0, -L - 5), (-2.5, -L)], 2, col=mix((245, 242, 235), (225, 215, 190), row / 2))
            f.rot('x', -14 - row * 6).rot('y', -math.degrees(a) + 90).move(
                (22 + row * 4) * math.cos(a), 168 - row * 9, -(16 + row * 3) * math.sin(a))
            out.add(f)
    out.add(collar(GOLD, 16, 166, 6))
    out.add(necklace_chain(GOLD, 26, 30, 3.0).scale(1, -1, 1).move(0, 172, 18))
    for x in (-10, 10):
        out.add(gem(2.6, 6, 4, GOLD).move(x, 140, 22))
    return out


@item('B08_2', 'Solar helm', 'head')
def _():
    h = helm_shell(GOLD, 22.5, 1.12)
    visor(h, (40, 26, 10), 'T', z_min=12)
    jitter(h, 0.08, 82)
    rays = sunburst((240, 196, 80), 12, 22, 40, 4, alt=0.6).move(0, 193, -6)
    return merge(h, rays)


@item('B08_3', 'Solar scale platebody', 'body')
def _():
    return platebody(GOLD, dark=GOLD_D, trim=(240, 205, 110), pattern='scale', seed=83,
                     pauldron_layers=3, skirt=True, skirt_col=GOLD, sleeve_col=(236, 226, 196))


@item('B08_4', 'Solar scale platelegs', 'legs')
def _():
    return platelegs(GOLD, (240, 205, 110), pattern='scale', seed=84)


def verdant(m, seed, shards=10, region=None):
    m = m.subdivide()
    cs = m.centroids()
    rng = random.Random(seed)
    for i in range(len(m.F)):
        m.C[i] = rng.choice([(90, 112, 50), (110, 120, 60), (78, 96, 44), (120, 96, 60)])
    out = merge(m)
    idx = [rng.randrange(len(cs)) for _ in range(shards)]
    ns = m.normals()
    for i in idx:
        d = ns[i] + np.array([0, 0.6, 0])
        g = gem(rng.uniform(3, 5), rng.uniform(12, 20), 5, rng.choice([(110, 225, 225), (80, 200, 215), (150, 240, 235)]))
        _align_y_to(g, d / np.linalg.norm(d))
        out.add(g.move(*cs[i]))
    return out


@item('B08_5', 'Verdant crystal helm', 'head')
def _():
    h = helm_shell((96, 112, 54), 23, 1.12)
    visor(h, (20, 24, 12), 'face', z_min=15)
    m = verdant(h, 85, 14)
    return visor(m, (20, 24, 12), 'face', z_min=15)


@item('B08_6', 'Verdant crystal body', 'body')
def _():
    m = platebody((96, 112, 54), trim=(80, 90, 44), pattern='plates', seed=86, pauldron_layers=2)
    return verdant(m, 86, 26)


# ============================================================ B09 bows
@item('B09_1', 'Bone longbow', 'weapon', BOW_VIEW)
def _():
    m, pts = bow_limbs(BONE, 116, 24, 3.6, grip_col=LEATHER, recurve=1.0)
    for p in pts[1:-1:2]:
        m.add(sphere(4.2, 6, 3, col=(232, 222, 196)).move(*p))
    return m


@item('B09_2', 'Shadowvine bow', 'weapon', BOW_VIEW)
def _():
    m, pts = bow_limbs((96, 58, 140), 110, 22, 3.4, grip_col=(70, 50, 40), recurve=1.4)
    jitter(m, 0.12, 92)
    return m


@item('B09_3', 'Dragonspine bow', 'weapon', BOW_VIEW)
def _():
    m, pts = bow_limbs(BONE_D, 120, 22, 3.0, grip_col=(80, 30, 30))
    for k, p in enumerate(pts[1:-1]):
        m.add(spike(p, (-1, 0.15 * np.sign(p[1]), 0), 9, 2.8, 4, BONE))
        m.add(box(6, 4, 6, BONE).move(*p))
    for s in (1, -1):
        mem = extrude([(0, 0), (16, s * 10), (18, s * 32), (8, s * 46), (2, s * 50)], 1.4, col=(150, 26, 34))
        m.add(mem.move(-18, s * 4, 0))
    return m


@item('B09_4', 'Crystal-root bow', 'weapon', BOW_VIEW)
def _():
    m, pts = bow_limbs(WOOD, 112, 22, 3.6, grip_col=(70, 50, 30))
    jitter(m, 0.12, 94)
    for p in pts[::2]:
        for k in range(2):
            m.add(gem(3.2, 13, 5, ICE).rot('z', 70 + k * 40).move(*p))
    return m


@item('B09_5', 'Seraph crossbow', 'weapon', XBOW_VIEW)
def _():
    m, pts = crossbow((236, 230, 214), (236, 236, 240), trim=GOLD)
    for p in (pts[0], pts[-1]):
        s = np.sign(p[0])
        m.add(wing(s, (245, 245, 248), GOLD, 0.55, at=(abs(p[0]) - 4, 0, p[2]), feathers=4).rot('x', -90, about=p))
    return m


@item('B09_6', 'Runic crossbow', 'weapon', XBOW_VIEW)
def _():
    m, pts = crossbow((54, 58, 64), (44, 48, 54), trim=(40, 200, 200))
    return glow_runes(m, (60, 220, 215), 14, 1.4, 96, 1)


# ============================================================ B10 robes
@item('B10_1', 'Astral wizard hat', 'head')
def _():
    blue = (48, 76, 170)
    c = HEAD
    pts = bezier((0, c[1] + 2, 0), (0, c[1] + 26, -2), (4, c[1] + 44, -8), (12, c[1] + 50, -16), 8)
    cone = tube(pts, 20, 10, blue, taper=[1.0, 0.82, 0.64, 0.48, 0.34, 0.22, 0.12, 0.05, 0.02], up=(1, 0, 0))
    brim = lathe([(16, c[1] + 2), (38, c[1] - 1), (38, c[1] + 1.5), (16, c[1] + 6)], 14, col=blue)
    band = prism(20.5, 19.5, 6, 12, c[1] + 4, col=(200, 205, 220))
    jitter(cone, 0.05, 101)
    m = merge(cone, brim, band)
    for k, (x, y) in enumerate([(0, 18), (-10, 28), (8, 32)]):
        m.add(extrude(star_poly(4, 4.5, 1.6), 1.2, col=(220, 225, 235)).move(x, c[1] + y, 16 - k * 2))
    return m


@item('B10_2', 'Astral robe top', 'body')
def _():
    m = robe_top((48, 76, 170), (200, 205, 220), 1.3, seed=102)
    for x, y in ((-12, 140), (12, 125), (-12, 95), (12, 82)):
        m.add(extrude(star_poly(4, 5, 1.8), 1.2, col=(220, 225, 235)).move(x, y, 21 if y > 100 else 20))
    return m


@item('B10_3', 'Astral robe bottom', 'legs')
def _():
    m = skirt((48, 76, 170), 106, 4, 28, 40, 14, hem=(200, 205, 220), seed=103, trim=(200, 205, 220))
    for k, y in enumerate((70, 40, 22)):
        a = math.pi / 2 + (k - 1) * 0.6
        r = 28 + (106 - y) / 102 * 12
        m.add(extrude(star_poly(4, 5, 1.8), 1.2, col=(220, 225, 235)).move(r * math.cos(a) * 0.95, y, r * 0.68 * math.sin(a) + 1))
    return m


@item('B10_4', 'Runeweaver hood', 'head')
def _():
    h = hood((70, 56, 160), (12, 10, 18), trim=(200, 205, 220), mantle=True, peak=6, seed=104)
    return glow_runes(h, RUNE_BLUE, 12, 1.2, 104, 0)


@item('B10_5', 'Runeweaver robe top', 'body')
def _():
    m = robe_top((70, 56, 160), (200, 205, 220), 1.3, seed=105)
    m.add(glow_runes(box(12, 40, 1.5, (60, 48, 140)).move(0, 130, 21), RUNE_BLUE, 6, 1.4, 105, 2))
    return m


@item('B10_6', 'Runeweaver robe skirt', 'legs')
def _():
    m = skirt((70, 56, 160), 106, 4, 28, 40, 14, hem=(200, 205, 220), seed=106, trim=(200, 205, 220))
    m.add(glow_runes(extrude([(-7, 0), (7, 0), (8, -70), (-8, -70)], 1.5, col=(60, 48, 140))
                     .rot('x', -7).move(0, 98, 24), RUNE_BLUE, 8, 1.4, 106, 2))
    return m


# ============================================================ B11 void / staves
@item('B11_1', 'Voidwoven hood', 'head')
def _():
    return glow_runes(hood(VOID, (6, 4, 10), mantle=True, peak=5, seed=111), VOID_G, 12, 1.0, 111, 0)


@item('B11_2', 'Voidwoven robe top', 'body')
def _():
    m = robe_top(VOID, (58, 44, 92), 1.2, seed=112)
    return glow_runes(m, VOID_G, 30, 1.0, 112, 1)


@item('B11_3', 'Voidwoven robe skirt', 'legs')
def _():
    m = skirt(VOID, 106, 4, 28, 38, 14, jag=8, seed=113, trim=(58, 44, 92))
    return glow_runes(m, VOID_G, 20, 1.2, 113, 1)


def claw_head(col, at, prongs=4, r=8, h=16):
    out = Mesh()
    for k in range(prongs):
        a = 2 * math.pi * k / prongs
        p0 = np.array(at) + [r * 0.4 * math.cos(a), 0, r * 0.4 * math.sin(a)]
        pts = bezier(p0, p0 + [r * math.cos(a), h * 0.4, r * math.sin(a)],
                     p0 + [r * 0.8 * math.cos(a), h, r * 0.8 * math.sin(a)], None, 4)
        out.add(tube(pts, 1.8, 4, col, taper=[1, 0.9, 0.7, 0.5, 0.25]))
    return out


@item('B11_4', 'Stormcaller staff', 'weapon', WEAPON_VIEW)
def _():
    s = staff_shaft(110, (40, 34, 60), 2.8, (110, 80, 200))
    head = claw_head((50, 44, 80), (0, 82, 0), 4, 7, 16)
    orb = sphere(6.5, 8, 4, col=(80, 170, 255)).move(0, 92, 0)
    orb.G = [True] * len(orb.F)
    bolts = Mesh()
    rng = random.Random(114)
    for k in range(7):
        a = 2 * math.pi * k / 7
        p = [0, 92, 0]
        pts = [tuple(p)]
        for j in range(3):
            p = [p[0] + 5 * math.cos(a) + rng.uniform(-2, 2), p[1] + 4 + rng.uniform(-1, 3), p[2] + 5 * math.sin(a)]
            pts.append(tuple(p))
        b = tube(pts, 1.1, 3, (150, 210, 255), taper=[1, 0.8, 0.5, 0.2])
        b.G = [True] * len(b.F)
        bolts.add(b)
    return merge(s, head, orb, bolts)


@item('B11_5', 'Solar sceptre', 'weapon', WEAPON_VIEW)
def _():
    s = staff_shaft(96, GOLD_D, 2.6, GOLD)
    sun = sunburst(GOLD, 10, 9, 17, 4, alt=0.7).move(0, 82, 0)
    core = sphere(6, 8, 4, col=(250, 210, 90)).move(0, 82, 2.5)
    core.G = [True] * len(core.F)
    return merge(s, sun, core, prism(4, 6, 6, 8, 64, col=GOLD))


@item('B11_6', 'Necrotic soulstaff', 'weapon', WEAPON_VIEW)
def _():
    s = staff_shaft(104, (40, 38, 46), 2.6, (90, 120, 70))
    sk = necro_skull(1.4).move(0, 84, 0)
    flames = Mesh()
    for k in range(7):
        a = 2 * math.pi * k / 7
        f = spike((5 * math.cos(a), 88, 5 * math.sin(a)), (math.cos(a) * 0.4, 1, math.sin(a) * 0.4), 16 + (k % 3) * 4, 3.5, 4, NECRO_G)
        flames.add(f)
    flames.G = [True] * len(flames.F)
    return merge(s, flames, sk, claw_head((60, 58, 66), (0, 72, 0), 4, 6, 12))


# ============================================================ B12 exotic weapons
@item('B12_1', 'Abyssal tidewhip', 'weapon', dict(yaw=-15, pitch=20))
def _():
    pts = bezier((0, 0, 0), (40, 30, 0), (-30, 60, 0), (10, 80, 6), 16)
    w = tube(pts, 3.2, 5, (40, 110, 110), taper=np.linspace(1.2, 0.3, len(pts)))
    w = glow_runes(w, CYAN, 18, 1.4, 121, 2)
    h = handle(26, 3.6, (40, 70, 70), cap=(60, 140, 140), y0=-26)
    return merge(w, h)


@item('B12_2', 'Seraph longsword', 'weapon', WEAPON_VIEW)
def _():
    b = blade(72, 11, (238, 238, 242), thick=3, edge_col=(210, 214, 222), base_y=2)
    g = crossguard(14, GOLD, 5, 6)
    wings = merge(wing(1, (245, 245, 248), GOLD, 0.55, at=(5, 2, 0), feathers=4),
                  wing(-1, (245, 245, 248), GOLD, 0.55, at=(5, 2, 0), feathers=4))
    gemc = gem(2.6, 6, 4, CYAN).rot('x', 90).move(0, 2, 3.5)
    return merge(b, g, wings, gemc, grip(20, 2.4, (90, 60, 40), wrap=(60, 40, 26), pommel=GOLD, pommel_r=3.5))


@item('B12_3', 'Bloodfang cleaver', 'weapon', WEAPON_VIEW)
def _():
    poly = [(-5, 0), (6, 0), (9, 14), (13, 18), (10, 22), (14, 32), (10, 36), (13, 46), (9, 50), (11, 60), (4, 76),
            (-2, 70), (-6, 56), (-9, 52), (-6, 40), (-10, 34), (-6, 24), (-9, 16)]
    b = extrude(poly, 4, 1.2, 0.8, col=(60, 22, 24)).move(0, 2, 0).subdivide().subdivide()
    cracks(b, 16, 1.8, (190, 30, 34), False, 123)
    g = crossguard(18, (40, 24, 24), 4, 6, curl=-4)
    return merge(b, g, grip(18, 2.6, (50, 30, 26), wrap=(110, 20, 26), pommel=(60, 22, 24), pommel_r=3))


@item('B12_4', 'Crimson rapier', 'weapon', WEAPON_VIEW)
def _():
    b = blade(80, 3.4, (200, 40, 50), thick=1.8, base_y=2, taper_end=0.6, tip=0.08)
    hilt = merge(torus(7, 1.0, 10, 3, (170, 26, 36)).rot('y', 90).move(0, -2, 0),
                 crossguard(16, (170, 26, 36), 3, 3, curl=5), gem(2.6, 6, 4, (230, 40, 50)).move(0, 1, 2.5))
    return merge(b, hilt, grip(16, 2.0, (110, 18, 26), wrap=(70, 12, 18), pommel=(200, 40, 50), pommel_r=2.8))


@item('B12_5', 'Gilded fang', 'weapon', WEAPON_VIEW)
def _():
    b = blade(46, 12, GOLD, curve=-1.6, thick=3.2, tip=0.35, edge_col=(250, 220, 120), base_y=2)
    jitter(b, 0.1, 125)
    return merge(b, crossguard(10, GOLD_D, 4, 6), grip(16, 2.6, (80, 52, 28), wrap=(150, 110, 40),
                                                       pommel=GOLD, pommel_r=3.2))


@item('B12_6', 'Goblin knotclub', 'weapon', WEAPON_VIEW)
def _():
    shaft = lathe([(3.2, -26), (3.6, 0), (5.5, 30), (7, 46)], 7, col=(92, 112, 46))
    jitter(shaft, 0.12, 126)
    knobs = merge(*[sphere(r, 7, 4, col=c).move(*p) for r, c, p in
                    ((9, (100, 150, 60), (2, 52, 0)), (7, (110, 160, 66), (-7, 46, 3)), (6.5, (92, 140, 56), (6, 44, -3)))])
    jitter(knobs, 0.12, 127)
    wrap = merge(*[prism(3.9, 3.9, 2, 6, y, col=(130, 60, 140)) for y in (-14, -9)])
    sticks = merge(*[tube([(0, 44, 0), (x, 70, z)], 0.8, 3, (150, 110, 60)) for x, z in ((4, 2), (-3, -2), (1, -4))])
    return merge(shaft, knobs, wrap, sticks)


# ============================================================ B13 neck & cape
@item('B13_1', 'Amulet of the sun', 'neck', NECK_VIEW)
def _():
    c = necklace_chain(GOLD, 22, 40, 3.0)
    star = extrude(star_poly(8, 16, 7), 4, 1.2, 0.7, col=GOLD).move(0, 0, 0)
    jewel = sphere(5, 8, 4, col=(220, 30, 30)).scale(1, 1, 0.6).move(0, 0, 2.5)
    return merge(c.move(0, 10, 0), star, jewel, torus(6, 1.2, 10, 3, GOLD_D).move(0, 0, 2.2))


@item('B13_2', 'Crimson cord necklace', 'neck', NECK_VIEW)
def _():
    pts = bezier((-22, 48, -2), (-24, 6, 2), (24, 6, 2), (22, 48, -2), 14)
    cord = tube(pts, 2.6, 5, (170, 34, 40))
    cord = cord.subdivide()
    bands(cord, 0, 3.5, [(170, 34, 40), (130, 22, 30)])
    knot = sphere(4.5, 7, 4, col=(150, 28, 34)).move(0, 6, 2)
    tails = merge(tube([(0, 6, 2), (-4, -16, 3)], 1.8, 4, (160, 30, 36)), tube([(0, 6, 2), (4, -16, 3)], 1.8, 4, (160, 30, 36)))
    tassels = merge(*[lathe([(0.1, -26), (3, -22), (2, -16)], 6, col=(120, 20, 28)).move(x, 0, 3) for x in (-4, 4)])
    return merge(cord, knot, tails, tassels)


@item('B13_3', 'Sapphire amulet', 'neck', NECK_VIEW)
def _():
    c = necklace_chain((140, 142, 150), 22, 40, 3.0).move(0, 12, 0)
    frame = extrude([(0, -22), (9, -10), (12, 4), (6, 16), (0, 20), (-6, 16), (-12, 4), (-9, -10)], 4, 1.2, 0.8, col=GOLD)
    stone = gem(7, 30, 6, (40, 120, 230)).rot('x', 90).scale(1, 1, 0.5).move(0, -1, 3)
    for s in (1, -1):
        frame.add(spike((s * 11, 2, 0), (s, 0.3, 0), 7, 2, 4, GOLD))
    return merge(c, frame, stone, sphere(2.2, 6, 3, col=CYAN).move(0, -18, 2.5))


@item('B13_4', 'Verdant shard amulet', 'neck', NECK_VIEW)
def _():
    c = necklace_chain((90, 92, 96), 22, 40, 3.0).move(0, 12, 0)
    shard = extrude([(-16, 10), (16, 10), (0, -22)], 6, 2, 0.75, col=(92, 120, 52)).subdivide()
    jitter(shard, 0.14, 134)
    return merge(c, shard, prism(2.4, 2.4, 3, 6, 10, col=(90, 92, 96)))


@item('B13_5', 'Obsidian cape', 'cape', dict(yaw=160, pitch=10))
def _():
    m = cape(OBSID, jag=16, seed=135)
    m = m.subdivide()
    cracks(m, 40, 0.9, (200, 50, 30), True, 135)
    return merge(m, collar((40, 30, 30), 15, 166, 6))


@item('B13_6', 'Magma cape', 'cape', dict(yaw=160, pitch=10))
def _():
    m = cape((150, 46, 20), jag=10, seed=136).subdivide()
    cracks(m, 44, 0.8, LAVA_HOT, True, 136, base=None)
    jitter(m, 0.15, 137)
    return merge(m, collar((90, 30, 18), 15, 166, 6), torus(4, 1.5, 8, 3, GOLD_D).move(0, 166, 14))


# ============================================================ B14 shields
@item('B14_1', 'Dragonfire shield', 'shield', SHIELD_VIEW)
def _():
    s = shield(heater_poly(46, 58), (52, 54, 60), 6, 3, rim=(110, 112, 118))
    jitter(s, 0.08, 141)
    head = lathe([(9, -6), (10, 2), (7, 10), (4, 16), (1, 19)], 7, col=(120, 122, 130)).rot('x', 80).move(0, 4, 4)
    head.add(box(10, 5, 14, (56, 58, 64)).move(0, -4, 12))  # jaw
    for s_ in (1, -1):
        head.add(horn(s_, (90, 90, 96), 22, 1.2, 2.6, (6, 12, 2)).rot('x', -20))
        head.add(sphere(1.6, 5, 2, col=(255, 140, 40)).move(s_ * 5, 4, 14))
    fire = Mesh()
    for k in range(6):
        fire.add(spike((-4, 0, 18), (-1, 0.2 + 0.15 * (k - 3) * 0.3, 0.6), 10 + k * 2, 3 - k * 0.3, 4,
                       [LAVA, LAVA_HOT, (255, 80, 20)][k % 3]))
    fire.G = [True] * len(fire.F)
    for k in range(5):
        s.add(spike((-20 + k * 10, 26, -1), (0, 1, 0), 9, 2.4, 4, (80, 82, 88)))
    return merge(s, head, fire.move(-6, -2, 0))


@item('B14_2', 'Glacial crystal shield', 'shield', SHIELD_VIEW)
def _():
    poly = [(0, -34), (14, -20), (22, 0), (20, 20), (8, 34), (0, 30), (-8, 34), (-20, 20), (-22, 0), (-14, -20)]
    s = shield(poly, (70, 190, 200), 8, 5)
    s = s.subdivide()
    jitter(s, 0.18, 142)
    cs = s.centroids()
    for i, c in enumerate(cs):
        if abs(c[0] + 0.2 * c[1]) < 2.2 and c[2] > 0:
            s.C[i] = (15, 40, 50)
    for k in range(8):
        a = 2 * math.pi * k / 8
        s.add(gem(4, 14, 5, ICE).rot('z', math.degrees(a) - 90).move(24 * math.cos(a), 30 * math.sin(a), 0))
    return s


@item('B14_3', 'Solar heater shield', 'shield', SHIELD_VIEW)
def _():
    s = shield(heater_poly(46, 58), GOLD, 6, 4, rim=GOLD_D)
    jitter(s, 0.06, 143)
    sun = sunburst((245, 200, 90), 12, 7, 14, 3, alt=0.6).move(0, 4, 5)
    core = sphere(5, 8, 4, col=(250, 210, 90)).scale(1, 1, 0.6).move(0, 4, 7)
    return merge(s, sun, core)


@item('B14_4', 'Jade thorn shield', 'shield', SHIELD_VIEW)
def _():
    rng = random.Random(144)
    poly = []
    for k in range(20):
        a = 2 * math.pi * k / 20
        r = (26 if k % 2 else 31) + rng.uniform(-2, 2)
        poly.append((r * math.cos(a) * 0.8, r * math.sin(a)))
    s = shield(poly, (150, 200, 170), 7, 6)
    s = s.subdivide()
    jitter(s, 0.12, 145)
    return s


@item('B14_5', 'Sapphire dragon kiteshield', 'shield', SHIELD_VIEW)
def _():
    s = shield(kite_poly(46, 62), (40, 70, 170), 6, 3, rim=(200, 204, 214))
    emb = extrude([(0, -16), (7, -6), (10, 6), (4, 12), (8, 18), (0, 14), (-6, 18), (-4, 8), (-10, 2), (-6, -8)],
                  2.5, 0.8, 0.7, col=(80, 150, 240)).move(0, 2, 4.5)
    emb.G = [True] * len(emb.F)
    stars = merge(*[extrude(star_poly(4, 4, 1.5), 1.2, col=(225, 228, 235)).move(x, y, 4) for x, y in
                    ((-13, 16), (13, 16), (-11, -10), (11, -10))])
    return merge(s, emb, stars)


@item('B14_6', 'Crimson spiked roundshield', 'shield', SHIELD_VIEW)
def _():
    s = shield(circle2d(28, 14), (150, 34, 40), 6, 5, rim=(70, 70, 76))
    jitter(s, 0.1, 146)
    for k in range(10):
        a = 2 * math.pi * k / 10
        s.add(spike((29 * math.cos(a), 29 * math.sin(a), 0), (math.cos(a), math.sin(a), 0.2), 10, 3, 4, (200, 200, 205)))
    s.add(spike((0, 0, 6), (0, 0, 1), 10, 5, 6, (200, 200, 205)))
    return s
