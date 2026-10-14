#!/usr/bin/env python3
"""Check swapped models the way the client uses them, against the originals.

  python3 tools/swap_verify.py --cache <osrs cache dump> [--swap out_swap] [--only B02]

For every swap in out_swap/swaps.json:

  animation   the default player body (the game's own kits) wearing the
              original item, then wearing ours, merged into one model like the
              client does, posed through real sequences (idle 808, walk 819,
              run 824, slash 390). Reported per item:
                body_drift  how far the player's own body vertices move
                            differently because ours is worn instead of the
                            original (transform pivots are averaged over every
                            vertex in a group, item included) - should be ~0
                follow      how far our item lands from where it would be if
                            wearing it didn't shift any rotation centre: ours
                            posed with its own (shifted) pivots vs ours posed
                            with the pivots of the original outfit
  icon        both inventory models rendered with the item's own icon
              settings (zoom2d, xan2d, yan2d, ...) by RuneLite's port of the
              client's sprite code; reports how much of the icon each fills
              and how well the silhouettes overlap

Writes out_swap/verify/<code>.png (pose strip: original | ours per pose, and
the two icons) and out_swap/verify.json; prints a table.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tools')]

from osrs.anim import Animator, decode_kit, default_body, load_sequence  # noqa: E402
from osrs.cache import FlatCache  # noqa: E402
from osrs.defs import items  # noqa: E402
from osrs.models import decode_many, from_cache, render_icon as icon  # noqa: E402
from rsgen import render, rsformat  # noqa: E402
from rsgen.swap import SLOT_TO_BODYPART  # noqa: E402

SEQUENCES = {'idle': 808, 'walk': 819, 'run': 824, 'slash': 390}
POSES = [('idle', 0), ('walk', 2), ('walk', 6), ('run', 3), ('slash', 4)]


def merged(parts):
    """The client's player-model merge (ModelData(ModelData[], int), deob
    method3928): vertices are copied through faces only - a vertex no face
    uses is dropped - and a vertex at exactly the position of one already
    merged (from any model) is shared, keeping the first one's label. Parts
    are merged in the order given (body kits first, then items).
    Returns (V, F, colours, labels, owner per vertex, face priorities)."""
    index, V, L, own, F, C, P = {}, [], [], [], [], [], []
    for tag, m in parts:
        lab = m['vgroup'] if m['vgroup'] is not None else [0] * len(m['V'])
        prio = m.get('prio') or [m.get('priority', 0) or 0] * len(m['F'])
        for f, col, pr in zip(np.asarray(m['F']), m['col'], prio):
            tri = []
            for v in f:
                key = tuple(int(x) for x in m['V'][v])
                if key not in index:
                    index[key] = len(V)
                    V.append(key)
                    L.append(int(lab[v]))
                    own.append(tag)
                tri.append(index[key])
            F.append(tri)
            C.append(rsformat.hsl16_to_rgb(col))
            P.append(int(pr))
    return np.array(V), np.array(F), C, np.array(L), np.array(own), P


def view(V, F, C, P=None, size=220, yaw=-28):
    return render.render(V * np.array([1, -1, -1]), F, C, size=size, yaw=yaw, pitch=10, smooth=True, priorities=P)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', default=os.path.join(ROOT, 'data', 'osrs-rev241'),
                    help='flatcache dump (default: the rev 241 extract in data/)')
    ap.add_argument('--swap', default=os.path.join(ROOT, 'out_swap'))
    ap.add_argument('--only', default='')
    ap.add_argument('--manifest', help='check a new-item package instead (out/manifest.json): each item against '
                                       'its template, models read from next to the manifest')
    a = ap.parse_args()
    cache = FlatCache(a.cache)
    defs = items(cache)
    kits = {i: decode_kit(i, b) for i, b in cache.files(2, 3).items()}
    bodies = {g: default_body(kits, g == 'female') for g in ('male', 'female')}
    body_models = from_cache(cache, sorted({m for b in bodies.values() for d in b.values() for m in d['models']}))
    seqs = {k: load_sequence(cache, s) for k, s in SEQUENCES.items()}
    if a.manifest:  # same shape as swaps.json, from a build.py manifest
        a.swap = os.path.dirname(os.path.abspath(a.manifest))
        with open(a.manifest) as f:
            man = json.load(f)
        swaps = [dict(code=m['code'], name=m['name'], template_id=m['template']['item_id'],
                      template_name=m['template']['name'],
                      parts=[dict(kind='inventory', model=m['inventory_model']),
                             dict(kind='maleModel0', model=m['worn_model']),
                             dict(kind='femaleModel0', model=m['worn_model_female'])])
                 for m in man['items'] if m.get('worn_placement') == 'template']
    else:
        with open(os.path.join(a.swap, 'swaps.json')) as f:
            swaps = json.load(f)['swaps']
    out_dir = os.path.join(a.swap, 'verify')
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for e in swaps:
        if not e['code'].startswith(a.only):
            continue
        t = defs[e['template_id']]
        hidden = {SLOT_TO_BODYPART.get(t[k]) for k in ('wearPos1', 'wearPos2', 'wearPos3')}
        drift, follow, tiles = [], [], []
        for gender in ('male', 'female'):
            keys = ['%sModel%d' % (gender, i) for i in range(3)]
            orig_ids = [t[k] for k in keys if t[k] >= 0]
            our_ids = [p['model'] for p in e['parts'] if p['kind'] in keys and p['model'] >= 0]
            if gender == 'female' and not our_ids:  # unisex template: the male models are reused
                our_ids = [p['model'] for p in e['parts'] if p['kind'].startswith('male') and p['model'] >= 0]
            if not orig_ids or not our_ids:
                continue
            kit_parts = [('body', body_models[m]) for bp, d in sorted(bodies[gender].items()) if bp not in hidden
                         for m in d['models']]
            orig = from_cache(cache, orig_ids)
            ours = decode_many({i: open(os.path.join(a.swap, 'models', '%d.dat' % i), 'rb').read() for i in our_ids})
            Vo, Fo, Co, Lo, Oo, Po_ = merged(kit_parts + [('item', orig[i]) for i in orig_ids])
            Vn, Fn, Cn, Ln, On, Pn_ = merged(kit_parts + [('item', ours[i]) for i in our_ids])
            ao, an = Animator(Vo, Lo), Animator(Vn, Ln)
            body_o, body_n = Oo == 'body', On == 'body'
            item_n = np.where(On == 'item')[0]
            for name, fi in POSES:
                seq = seqs[name]
                fm, fr = seq[min(fi, len(seq) - 1)]
                piv = []
                Po = ao.pose(fm, fr, record=piv)
                Pn = an.pose(fm, fr)
                Pi = an.pose(fm, fr, pivots=piv)  # ours, with the original outfit's rotation centres
                drift.append(float(np.linalg.norm((Po[body_o] - Pn[body_n]).astype(float), axis=1).max())
                             if body_o.any() else 0.0)
                follow.append(float(np.percentile(np.linalg.norm((Pn[item_n] - Pi[item_n]).astype(float), axis=1),
                                                  95)))
                if gender == 'male':
                    tiles.append((view(Po, Fo, Co, Po_), view(Pn, Fn, Cn, Pn_), '%s %d' % (name, fi)))
        inv_new = next(p['model'] for p in e['parts'] if p['kind'] == 'inventory')
        io = icon(cache.archive(7, t['inventoryModel']), t)
        inn = icon(open(os.path.join(a.swap, 'models', '%d.dat' % inv_new), 'rb').read(), t)
        mo, mn = np.asarray(io)[..., 3] > 0, np.asarray(inn)[..., 3] > 0
        iou = float((mo & mn).sum() / max(1, (mo | mn).sum()))
        res = dict(code=e['code'], template=e['template_name'], body_drift_max=round(max(drift), 2),
                   follow_p95_max=round(max(follow), 2), icon_fill_original=round(float(mo.mean()), 3),
                   icon_fill_ours=round(float(mn.mean()), 3), icon_silhouette_iou=round(iou, 3))
        results.append(res)
        # pose strip + icons
        W = 220
        sheet = Image.new('RGB', (W * len(tiles) + 160, 2 * W + 30), (16, 16, 20))
        dr = ImageDraw.Draw(sheet)
        dr.text((6, 2), '%s %s  on  %s (original top, ours bottom)' % (e['code'], e['name'], e['template_name']),
                fill=(230, 230, 230))
        for k, (to, tn, cap) in enumerate(tiles):
            sheet.paste(to, (k * W, 16))
            sheet.paste(tn, (k * W, 16 + W))
            dr.text((k * W + 4, 18), cap, fill=(200, 200, 200))
        x0 = W * len(tiles) + 8
        for j, im in enumerate((io, inn)):
            bg = Image.new('RGBA', (36, 32), (62, 53, 41, 255))
            bg.alpha_composite(im)
            sheet.paste(bg.resize((144, 128), Image.NEAREST).convert('RGB'), (x0, 30 + j * 220))
        sheet.save(os.path.join(out_dir, '%s.png' % e['code']))
        print('%-6s %-24s drift %5.2f  follow %5.2f  icon fill %.2f/%.2f iou %.2f' % (
            e['code'], e['template_name'], res['body_drift_max'], res['follow_p95_max'], res['icon_fill_original'],
            res['icon_fill_ours'], iou))
    with open(os.path.join(a.swap, 'verify.json'), 'w') as f:
        json.dump(results, f, indent=1)


if __name__ == '__main__':
    main()
