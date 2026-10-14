"""Swap a redesign onto a real OSRS item ("template"), so the game can show
our model where it showed the original, with the same animations, placement
and icon framing.

What the client needs from a swapped-in model, all taken from the template
item's own models:

  placement      worn models sit on the player exactly where the original
                 did (armour wraps the same body volume; weapons and shields
                 sit in the same hand, same orientation)
  vertex groups  every worn-model vertex carries the label of the nearest
                 original vertex, so the player's animations move it with
                 the same body part (without labels a worn item stays rigid
                 while the player walks or attacks)
  model split    items whose original is split over several models (a
                 platebody's torso + arms) are split the same way, vertex by
                 vertex, so the item definition's model slots keep working
  priorities     each face takes the draw priority of the nearest original
                 face; detail-line strips one above it (max 11)
  inventory      the inventory model is aligned and scaled onto the
                 original's, so the item's zoom2d/xan2d/yan2d icon framing
                 keeps working

Coordinates here are RS model space (y down, the player faces -z, his left
is +x), integer after rounding.
"""
import itertools

import numpy as np

from .geom import Mesh

AUTHORING_TO_RS = np.array([1, -1, -1])  # a rotation (det +1): face winding is kept

# player kit body parts hidden/replaced by equipment slots (wearPos values)
SLOT_TO_BODYPART = {8: 0, 11: 1, 4: 2, 6: 3, 9: 4, 7: 5, 10: 6}

# OSRS template item (by name, rev 241) for every redesign; override freely
TEMPLATES = {
    'B01_1': 'Bronze platebody', 'B01_2': 'Iron platebody', 'B01_3': 'Steel platebody',
    'B01_4': 'Black platebody', 'B01_5': 'Mithril platebody', 'B01_6': 'Adamant platebody',
    'B02_1': 'Rune platebody', 'B02_2': "Red d'hide body", 'B02_3': 'Dragon scimitar',
    'B02_4': 'Rune pickaxe', 'B02_5': 'Dragon pickaxe', 'B02_6': 'Dragon axe',
    'B03_1': 'Dragon battleaxe', 'B03_2': 'Dragon spear', 'B03_3': "Verac's flail",
    'B03_4': 'Granite maul', 'B03_5': 'Rune crossbow', 'B03_6': 'Dragon mace',
    'B04_1': 'Dragon platebody', 'B04_2': 'Dragon platelegs', 'B04_3': 'Dragon boots',
    'B04_4': 'Rune full helm', 'B04_5': "Torag's platebody", 'B04_6': 'Barrows gloves',
    'B05_1': 'Rune full helm', 'B05_2': 'Rune chainbody', 'B05_3': 'Bandos tassets',
    'B05_4': 'Adamant full helm', 'B05_5': 'Adamant platebody', 'B05_6': 'Rune boots',
    'B06_1': 'Dragon full helm', 'B06_2': 'Dragon platebody', 'B06_3': 'Barrows gloves',
    'B06_4': 'Dragon dagger', 'B06_5': 'Dragon mace', 'B06_6': 'Dragon kiteshield',
    'B07_1': "Green d'hide body", 'B07_2': "Blue d'hide body", 'B07_3': "Red d'hide body",
    'B07_4': "Black d'hide body", 'B07_5': 'Adamant full helm', 'B07_6': 'Rune platebody',
    'B08_1': 'Fire cape', 'B08_2': 'Armadyl helmet', 'B08_3': 'Armadyl chestplate',
    'B08_4': 'Rune platelegs', 'B08_5': 'Crystal helm', 'B08_6': 'Crystal body',
    'B09_1': 'Magic longbow', 'B09_2': 'Dark bow', 'B09_3': 'Twisted bow',
    'B09_4': 'Crystal bow', 'B09_5': 'Armadyl crossbow', 'B09_6': 'Rune crossbow',
    'B10_1': 'Wizard hat', 'B10_2': 'Mystic robe top', 'B10_3': 'Mystic robe bottom',
    'B10_4': "Ahrim's hood", 'B10_5': "Ahrim's robetop", 'B10_6': "Ahrim's robeskirt",
    'B11_1': 'Ancestral hat', 'B11_2': 'Ancestral robe top', 'B11_3': 'Ancestral robe bottom',
    'B11_4': 'Mystic air staff', 'B11_5': 'Master wand', 'B11_6': 'Mystic air staff',
    'B12_1': 'Abyssal whip', 'B12_2': 'Dragon longsword', 'B12_3': 'Dragon scimitar',
    'B12_4': 'Ghrazi rapier', 'B12_5': "Osmumten's fang", 'B12_6': 'Rune mace',
    'B13_1': 'Amulet of glory', 'B13_2': 'Amulet of power', 'B13_3': 'Sapphire amulet',
    'B13_4': 'Amulet of fury', 'B13_5': 'Obsidian cape', 'B13_6': 'Infernal cape',
    'B14_1': 'Dragonfire shield', 'B14_2': 'Crystal shield', 'B14_3': 'Rune sq shield',
    'B14_4': 'Adamant kiteshield', 'B14_5': 'Rune kiteshield', 'B14_6': 'Toktz-ket-xil',
}

RIGID_SLOTS = ('weapon', 'shield')  # aligned by principal axes, not stretched to a bounding box


# --------------------------------------------------------------- geometry

def area_samples(V, F):
    """Face centroids and areas (for area-weighted statistics)."""
    T = np.asarray(V, float)[np.asarray(F)]
    c = T.mean(1)
    a = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
    return c, np.maximum(a, 1e-9)


def principal_axes(V, F):
    """(centre, axes 3x3 rows sorted longest first, extents along them)."""
    c, a = area_samples(V, F)
    mu = (c * a[:, None]).sum(0) / a.sum()
    X = np.asarray(V, float) - mu
    cov = ((c - mu).T * a) @ (c - mu) / a.sum()
    w, vec = np.linalg.eigh(cov)
    axes = vec[:, np.argsort(-w)].T
    ext = np.ptp(X @ axes.T, axis=0)
    return mu, axes, np.maximum(ext, 1e-6)


def chamfer(P, Q):
    d = ((P[:, None, :] - Q[None, :, :]) ** 2).sum(-1)
    return float(np.sqrt(d.min(1)).mean() + np.sqrt(d.min(0)).mean())


def _sample(V, F, n=400, seed=0):
    rng = np.random.default_rng(seed)
    V = np.asarray(V, float)
    F = np.asarray(F)
    c, a = area_samples(V, F)
    idx = rng.choice(len(F), size=min(n, 4 * len(F)), p=a / a.sum())
    r = rng.random((len(idx), 2))
    flip = r.sum(1) > 1
    r[flip] = 1 - r[flip]
    T = V[F[idx]]
    return T[:, 0] + r[:, :1] * (T[:, 1] - T[:, 0]) + r[:, 1:] * (T[:, 2] - T[:, 0])


def fit_bbox(V, ref_V, sheet=None):
    """Per-axis scale + translate V's bounding box onto ref_V's (armour: our
    piece covers exactly the body volume the original covered).

    sheet: 'back' (capes) or 'front' (amulets) - thin pieces that hang off the
    body: their depth is scaled like their width and height (not stretched
    through the body to the original's full depth, which for a cape includes
    the part wrapping over the shoulders) and laid against the original's back
    (RS +z) or front (RS -z) face."""
    lo, hi = V.min(0), V.max(0)
    rlo, rhi = ref_V.min(0), ref_V.max(0)
    k = (rhi - rlo) / np.maximum(hi - lo, 1e-6)
    out = (V - lo) * k + rlo
    if sheet:
        kz = min(k[2], float(np.sqrt(k[0] * k[1])))
        z = (V[:, 2] - lo[2]) * kz
        out[:, 2] = z + (rhi[2] - z.max() if sheet == 'back' else rlo[2])
    return out


def rigid_params(V, F, ref_V, ref_F, front_out=None):
    """(mu, M, s, rmu) such that ((V - mu) @ M.T) * s + rmu lays V onto the
    reference: principal axes and length matched, proper rotation only; of
    the four candidate orientations the one whose surface lies closest to the
    reference (chamfer distance), so an axe head lands where the axe head was.
    front_out: optional RS direction the model's own front (RS -z) must face
    (a shield faces away from the body)."""
    mu, ax, ext = principal_axes(V, F)
    rmu, rax, rext = principal_axes(ref_V, ref_F)
    # length matched to the original, but never much wider than it where it is
    # thick (a pair of crossed mauls must not come out three times the size)
    s = min(rext[0] / ext[0], 1.25 * rext[1] / ext[1])
    P = _sample(V, F)
    Q = _sample(ref_V, ref_F, seed=1)
    best = None
    for s0, s1, s2 in itertools.product((1, -1), repeat=3):
        R_to = np.array([rax[0] * s0, rax[1] * s1, rax[2] * s2])
        M = R_to.T @ ax  # maps our principal axes onto the reference's
        if np.linalg.det(M) < 0:  # a mirror would turn the model inside out
            continue
        cost = chamfer(((P - mu) @ M.T) * s + rmu, Q)
        if front_out is not None:
            front = M @ np.array([0.0, 0.0, -1.0])
            cost -= 1e6 * float(front @ front_out)  # hard preference, chamfer breaks ties
        if best is None or cost < best[0]:
            best = (cost, M)
    return mu, best[1], s, rmu


def fit_rigid(V, F, ref_V, ref_F, front_out=None):
    mu, M, s, rmu = rigid_params(V, F, ref_V, ref_F, front_out)
    return ((np.asarray(V, float) - mu) @ M.T) * s + rmu


# --------------------------------------------------------------- transfer

def skeleton_plan(framemap, counts=None, body_counts=None):
    """How the player skeleton constrains our vertex labels.

    Labels the skeleton moves identically (same membership in every
    move/rotate/scale transform) form a class: a vertex can carry any label
    of its class and move exactly the same. What differs is the rotation
    centres (type-0 transforms): the client finds each one by averaging every
    vertex carrying its labels across the merged player model - item
    included - so a redesign, which has far more vertices than the original,
    pulls them (and the player's limbs) off unless its labels are chosen
    with care; see swap_worn.

    counts: {label: vertices the visible body kits + the original item put
    there}; body_counts: the body kits' share alone.
    Returns dict(cls={label: class id}, members={class id: [labels]},
    centres=[set of labels per type-0 transform], counts, body_counts)."""
    from collections import defaultdict
    sig, centres = defaultdict(set), []
    for i, (t, labels) in enumerate(zip(framemap['types'], framemap['maps'])):
        if t == 0:
            centres.append(frozenset(labels))
        elif t in (1, 2, 3):
            for g in labels:
                sig[g].add(i)
    classes = defaultdict(list)
    for g, s_ in sig.items():
        classes[frozenset(s_)].append(g)
    cls, members = {}, {}
    for cid, labels in enumerate(classes.values()):
        members[cid] = sorted(labels)
        for g in labels:
            cls[g] = cid
    return dict(cls=cls, members=members, centres=sorted(set(centres), key=sorted),
                counts=dict(counts or {}), body_counts=dict(body_counts or {}))


def _sink(plan, h, orig_labels):
    """A label whose own single-label centre we can keep exact at any vertex
    count: the original uses it and no body vertex carries it, so that centre
    is the centroid of the item's vertices there - anchors fix the centroid."""
    return h in orig_labels and plan['body_counts'].get(h, 0) == 0


def _label_cost(plan, h, n, orig_labels):
    """How much putting n of our vertices on label h moves the rotation
    centres containing h: sum over those centres of our share of the
    vertices averaged (n / (vertices already there + n)). Single-label
    centres of sink labels cost nothing (anchors keep their centroid)."""
    cost = 0.0
    for U in plan['centres']:
        if h not in U:
            continue
        if len(U) == 1 and _sink(plan, h, orig_labels):
            continue
        there = sum(plan['counts'].get(x, 0) for x in U)
        cost += n / (there + n)
    return cost


def spread_points(total, k):
    """k distinct integer points whose sum is exactly `total`. The client
    merges vertices at identical positions, so anchors must never share one.
    Points sit on a lattice of spacing 2 around total / k (offsets in +/-
    pairs, so they cancel), and the integer remainder is added as +1 steps,
    which can't make two points meet."""
    total = np.rint(np.asarray(total, float)).astype(int)
    offs = [np.zeros(3, int)] if k % 2 else []
    r = 1
    while len(offs) < k:
        shell = [np.array(o) for o in itertools.product(range(-r, r + 1), repeat=3)
                 if max(abs(x) for x in o) == r]
        shell = [o for o in shell if tuple(o) > tuple(-o)]  # one of each +/- pair
        shell.sort(key=lambda o: (np.abs(o).sum(), tuple(o)))
        for o in shell:
            if len(offs) + 2 > k:
                break
            offs += [2 * o, -2 * o]
        r += 1
    P = np.floor(total / k).astype(int) + np.array(offs[:k])
    rest = total - P.sum(0)
    for a in range(3):
        P[:rest[a], a] += 1  # 0 <= rest < k
    assert len({tuple(p) for p in P}) == k and np.array_equal(P.sum(0), total)
    return P


def nearest(P, Q):
    """Index of the nearest Q point for every P point."""
    out = np.empty(len(P), int)
    for i in range(0, len(P), 512):
        d = ((P[i:i + 512, None, :] - Q[None, :, :]) ** 2).sum(-1)
        out[i:i + 512] = d.argmin(1)
    return out


def merge_refs(refs):
    """Concatenate reference models: (V, F, labels, face priorities, source
    model index per vertex / per face)."""
    V, F, L, P, src_v, src_f, off = [], [], [], [], [], [], 0
    for k, r in enumerate(refs):
        n = len(r['V'])
        V.append(r['V'])
        F.append(np.asarray(r['F']) + off)
        L.append(r['vgroup'] if r.get('vgroup') is not None else [0] * n)
        P.append(r['prio'] if r.get('prio') is not None else [r.get('priority', 0) or 0] * len(r['F']))
        src_v += [k] * n
        src_f += [k] * len(r['F'])
        off += n
    return (np.vstack(V).astype(float), np.vstack(F), np.concatenate(L).astype(int), np.concatenate(P).astype(int),
            np.array(src_v), np.array(src_f))


def swap_worn(mesh, refs, slot, plan=None):
    """Fit a worn-placement mesh (authoring coordinates, see stage 3) onto the
    template's worn models (refs: decoded dicts, RS coordinates) and transfer
    labels, split and priorities (plan: see skeleton_plan). Returns a list of Meshes in RS coordinates,
    one per reference model (some may be empty), each with .groups (vertex
    labels) and .prio (face priorities)."""
    RV, RF, RL, RP, rsrc_v, rsrc_f = merge_refs(refs)
    V = np.asarray(mesh.V, float) * AUTHORING_TO_RS
    F = np.asarray(mesh.F)
    if slot in RIGID_SLOTS:
        out_dir = None
        if slot == 'shield':  # face away from the body, along the reference's own offset
            c = RV.mean(0)
            out_dir = np.array([np.sign(c[0]) or 1.0, 0.0, 0.0])
        V = fit_rigid(V, F, RV, RF, out_dir)
    else:
        V = fit_bbox(V, RV, {'cape': 'back', 'neck': 'front'}.get(slot))
    V = np.rint(V)
    vn = nearest(V, RV)
    labels = RL[vn].copy()
    anchors = []
    if plan:
        # Rotation centres average every vertex with their labels across the
        # merged player model, and all vertices of a label transform alike. Per
        # skeleton class (labels the skeleton moves identically) our vertices
        # go to the one member label that moves the centres least (see
        # _label_cost); every label the original uses then gets back exactly
        # what it had: if we left it, the original's own vertices as anchors
        # (same count and positions); if our vertices sit on it, extra anchors
        # pull its centroid onto the original's. An anchor is a vertex on a
        # zero-area face (all three corners the same vertex): the client keeps
        # it when merging the player model (it copies vertices through faces)
        # but never draws it (zero area fails the visibility test).
        orig_labels = set(int(g) for g in np.unique(RL))
        kept = set()
        cls = np.array([plan['cls'].get(int(g), -1) for g in labels])
        for cid in np.unique(cls):
            if cid < 0:
                continue  # label outside the player skeleton: keep as is
            idx = np.where(cls == cid)[0]
            # ties: prefer a label the original doesn't use (it then keeps exact copies)
            target = min(plan['members'][cid],
                         key=lambda h: (round(_label_cost(plan, h, len(idx), orig_labels), 6), h in orig_labels, h))
            labels[idx] = target
            kept.add(int(target))
        for g in sorted(orig_labels):
            if g not in plan['cls']:
                continue
            src_part = int(np.bincount(rsrc_v[RL == g]).argmax())
            target = RV[RL == g].mean(0)
            if g not in kept:
                for o in np.where(RL == g)[0]:  # exact copies of the original's vertices
                    anchors.append((src_part, RV[o].copy(), g))
                continue
            # our vertices sit on g: anchors pull the centroid onto the original's
            mine = np.where(labels == g)[0]
            n = len(mine)
            miss = target * n - V[mine].sum(0)
            if np.linalg.norm(miss) < 0.5 * max(n, 1):
                continue
            # the anchors' own centroid may sit up to `reach` from the target,
            # inside our model's bounds: the farther, the fewer anchors
            lo, hi = V.min(0), V.max(0)
            d = miss / np.linalg.norm(miss)
            reach = min([((hi[a] if d[a] > 0 else lo[a]) - target[a]) / d[a] for a in range(3)
                         if abs(d[a]) > 1e-6] + [40.0])
            reach = float(np.clip(reach - 4, 6, 40))
            k = int(np.ceil(np.linalg.norm(miss) / reach))
            for pos in spread_points(target * (n + k) - V[mine].sum(0), k):
                anchors.append((src_part, pos, g))
    owner_v = rsrc_v[vn]
    # each face goes to the reference model most of its vertices are nearest to
    owner_f = np.array([np.bincount(owner_v[f], minlength=len(refs)).argmax() for f in F])
    cen = V[F].mean(1)
    rcen = RV[RF].mean(1)
    T, RT = V[F], RV[RF]
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    rnrm = np.cross(RT[:, 1] - RT[:, 0], RT[:, 2] - RT[:, 0])
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    rnrm /= np.maximum(np.linalg.norm(rnrm, axis=1, keepdims=True), 1e-9)
    layers = np.asarray(mesh.layers())
    out = []
    for k in range(len(refs)):
        sel = np.where(owner_f == k)[0]
        rsel = np.where(rsrc_f == k)[0]
        used = np.unique(F[sel]) if len(sel) else np.zeros(0, int)
        remap = {v: i for i, v in enumerate(used)}
        m = Mesh(V[used], [[remap[v] for v in f] for f in F[sel]], [mesh.C[i] for i in sel],
                 L=[int(layers[i]) for i in sel])
        m.groups = [int(x) for x in labels[used]]
        m.anchors = [(pos, g) for part, pos, g in anchors if part == k]
        if len(sel) and len(rsel):
            # each face takes the priority of the nearest original face that faces
            # the same way: the client draws by priority first (painter's
            # algorithm), so e.g. a cape's inward side must keep the original's
            # low priority or it would draw over the player's back... and chest
            base = np.empty(len(sel), int)
            same = (nrm[sel] @ rnrm[rsel].T) > 0
            for j, i in enumerate(sel):
                cand = rsel[same[j]] if same[j].any() else rsel
                base[j] = RP[cand[((rcen[cand] - cen[i]) ** 2).sum(1).argmin()]]
        else:
            base = np.full(len(sel), 10)
        m.prio = [int(min(11, b + 1)) if ly else int(b) for b, ly in zip(base, layers[sel])]
        out.append(m)
    return out


def swap_inventory(worn_parts, ref_worn, ref_inv):
    """Inventory model from our fitted worn model, through the template's own
    worn -> inventory transform: Jagex's inventory model is the worn model
    turned and scaled for the icon camera (xan2d/yan2d/zoom2d were set for
    that pose), so the same transform lays ours down the same way, front to
    the camera. Falls back to a direct rigid fit when the template's worn and
    inventory models don't correspond (rare: e.g. a different-shaped icon).
    worn_parts: our RS-space worn parts (from swap_worn); ref_worn: the
    template's worn models (decoded); ref_inv: its inventory model."""
    from .geom import Mesh
    parts = [p for p in worn_parts if len(p.F)]
    V = np.vstack([p.V for p in parts]).astype(float)
    F = np.vstack([np.asarray(p.F) + off for p, off in zip(parts, np.cumsum([0] + [len(p.V) for p in parts])[:-1])])
    C = [c for p in parts for c in p.C]
    L = [x for p in parts for x in p.layers()]
    RV = np.vstack([r['V'] for r in ref_worn]).astype(float)
    RF = np.vstack([np.asarray(r['F']) + off for r, off in
                    zip(ref_worn, np.cumsum([0] + [len(r['V']) for r in ref_worn])[:-1])])
    IV, IF = np.asarray(ref_inv['V'], float), np.asarray(ref_inv['F'])
    mu, M, s, rmu = rigid_params(RV, RF, IV, IF)
    mapped = ((RV - mu) @ M.T) * s + rmu
    if chamfer(_sample(mapped, RF), _sample(IV, IF, seed=1)) > 0.08 * float(np.ptp(IV, axis=0).max()):
        Vi = fit_rigid(V, F, IV, IF)  # template inventory isn't its worn model re-posed
    else:
        Vi = ((V - mu) @ M.T) * s + rmu
    m = Mesh(np.rint(Vi), F, C, L=L)
    base = int(np.median(ref_inv['prio'])) if ref_inv.get('prio') is not None else int(ref_inv.get('priority', 0) or 0)
    m.prio = [min(11, base + ly) for ly in m.layers()]
    m.groups = None
    return m
