#!/usr/bin/env python3
"""Build swap-ready models: each redesign fitted onto a real OSRS item.

  python3 tools/swap_build.py --cache <osrs cache dump> [--only B02] [--base-model-id 64000]
                              [--templates templates.json] [--out out_swap]

--cache is a folder of RuneLite flatcache files (<index>.flatcache: 0, 1, 2
and 7 are needed), e.g. github.com/abextm/osrs-cache at the server's revision
(rev 241 for OpenRune). Each redesign is swapped onto its template item
(rsgen/swap.py TEMPLATES, or --templates {code: item name or id}):

  out_swap/models/<id>.dat     new models (inventory, male and female worn
                               parts) at fresh ids - the originals stay
                               untouched, since OSRS reuses one model for many
                               items (e.g. all platebody tiers via recolours)
  out_swap/swaps.json          per redesign: template item, the item-definition
                               fields to set (model slots, recolours cleared)
                               and the checks below

Every written model is decoded again with RuneLite's ModelLoader and must
carry the vertex groups and face priorities that were transferred.
"""
import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tools'), os.path.join(ROOT, 'pipeline')]

from osrs.cache import FlatCache  # noqa: E402
from osrs.defs import items  # noqa: E402
from osrs.models import decode_many, from_cache, icon_extent, render_icon  # noqa: E402
from rsgen import rsformat  # noqa: E402
from rsgen.geom import Mesh  # noqa: E402
from rsgen.items import ITEMS  # noqa: E402
from rsgen.meshio import load_mesh  # noqa: E402
from collections import Counter  # noqa: E402
from osrs.anim import decode_framemap, default_body, kits as load_kits  # noqa: E402
from rsgen.swap import (AUTHORING_TO_RS, SLOT_TO_BODYPART, TEMPLATES, skeleton_plan,  # noqa: E402
                        swap_inventory, swap_worn)
from stage3_models_to_rs import convert  # noqa: E402

WORN_KEYS = (('male', ('maleModel0', 'maleModel1', 'maleModel2')),
             ('female', ('femaleModel0', 'femaleModel1', 'femaleModel2')))


def resolve(defs, key):
    if isinstance(key, int) or str(key).isdigit():
        return int(key)
    for i in sorted(defs):
        d = defs[i]
        if (d['name'] == key and d['maleModel0'] >= 0 and d['inventoryModel'] >= 0 and d['notedTemplate'] == -1
                and d['placeholderTemplateId'] == -1):
            return i
    raise SystemExit('template item %r not found in this cache' % key)


def separate_anchors(anchors, V_rs):
    """Anchors must not share a position with any other vertex: the client's
    merge would fuse them (keeping the first vertex's label). Move a clashing
    anchor one unit and move another anchor of the same label the opposite
    way, so the label's vertex sum - what the rotation centres depend on -
    stays exact."""
    taken = {tuple(int(x) for x in v) for v in V_rs}
    out = [(np.rint(np.asarray(p, float)).astype(int), g) for p, g in anchors]
    used = set()
    steps = [np.array(d) for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1))]

    def free(q):
        return tuple(q) not in taken and tuple(q) not in used
    for i, (p, g) in enumerate(out):
        if free(p):
            used.add(tuple(p))
            continue
        for d in steps:
            # a partner of the same label (not yet placed) takes the opposite step
            partner = next((j for j in range(i + 1, len(out)) if out[j][1] == g and free(out[j][0] - d)), None)
            if free(p + d) and partner is not None:
                out[i] = (p + d, g)
                out[partner] = (out[partner][0] - d, g)
                used.add(tuple(p + d))
                break
        else:
            # no partner to balance it: a lone 1-unit step still beats being fused
            d = next((d for d in steps if free(p + d)), None)
            out[i] = (p + d, g) if d is not None else (p, g)
            used.add(tuple(out[i][0]))
    return out


def encode_part(m, smooth=True):
    """RS-space part -> (bytes, faces) with groups/priorities, decoded back and checked."""
    auth = Mesh(np.asarray(m.V, float) * AUTHORING_TO_RS, m.F, m.C, L=m.layers())
    cm, groups, prio = rsformat.clean(auth, vattr=m.groups, fattr=m.prio)
    anchors = separate_anchors(getattr(m, 'anchors', []), np.asarray(cm.V) * AUTHORING_TO_RS)
    if anchors:  # zero-area anchor faces (see rsgen.swap): appended after clean(), which would drop them
        V = list(map(tuple, cm.V))
        F, C, L = [tuple(f) for f in cm.F], list(cm.C), cm.layers()
        for pos, g in anchors:
            V.append(tuple(np.asarray(pos, float) * AUTHORING_TO_RS))
            v = len(V) - 1
            F.append((v, v, v))
            C.append((0, 0, 0))
            L.append(0)
            groups = list(groups) + [g]
            prio = list(prio) + [min(prio)]
        cm = Mesh(np.array(V, float), F, C, L=L)
    data = rsformat.encode(cm, smooth=smooth, priorities=prio, vertex_groups=groups)
    return data, cm, groups, prio


class Fitter:
    """Everything needed to fit redesigns onto template items of one cache."""

    def __init__(self, cache):
        self.cache = cache
        self.defs = items(cache)
        self.skeleton = decode_framemap(cache.archive(1, 0))  # framemap 0: the player skeleton
        all_kits = load_kits(cache)
        self.bodies = {g: default_body(all_kits, g == 'female') for g in ('male', 'female')}
        self.kit_models = from_cache(cache, sorted({m for b in self.bodies.values() for d in b.values()
                                                    for m in d['models']}))

    def fit(self, it, tid, worn_auth):
        """Fit one redesign (worn placement, authoring axes) onto template item
        tid. Returns dict(template=def, worn={gender: (template model ids, our
        parts)}, inventory=mesh); genders whose template models are the same
        (unisex) share one fit."""
        t = self.defs[tid]
        hidden = {SLOT_TO_BODYPART.get(t[k]) for k in ('wearPos1', 'wearPos2', 'wearPos3')}
        worn, done = {}, {}
        for gender, keys in WORN_KEYS:
            ref_ids = [t[k] for k in keys if t[k] >= 0]
            if not ref_ids:
                continue
            if tuple(ref_ids) in done:
                worn[gender] = done[tuple(ref_ids)]
                continue
            refs = from_cache(self.cache, ref_ids)
            # vertices per label in the outfit this item is worn in: visible body kits + the original item
            body_counts = Counter()
            for bp, kit in self.bodies[gender].items():
                if bp not in hidden:
                    for km in kit['models']:
                        body_counts.update(self.kit_models[km]['vgroup'] or [])
            counts = Counter(body_counts)
            for i in ref_ids:
                counts.update(refs[i]['vgroup'] or [])
            plan = skeleton_plan(self.skeleton, counts, body_counts)
            parts = swap_worn(worn_auth, [refs[i] for i in ref_ids], it['slot'], plan)
            for p_, rid in zip(parts, ref_ids):
                p_.template_groups = sorted(set(refs[rid]['vgroup'] or []))
            worn[gender] = done[tuple(ref_ids)] = (ref_ids, parts)
        # inventory model: our male worn model laid down the way the template's is
        male_ids, male_parts = worn['male']
        refs = from_cache(self.cache, male_ids + [t['inventoryModel']])
        inv = swap_inventory(male_parts, [refs[i] for i in male_ids], refs[t['inventoryModel']])
        # match the icon's footprint to the original's: render both exactly as the
        # client does (same zoom2d/xan2d/yan2d) and rescale ours about its centre
        want = icon_extent(render_icon(self.cache.archive(7, t['inventoryModel']), t))
        for _ in range(2):
            data, cm, _, prio = encode_part(inv)
            have = icon_extent(render_icon(data, t))
            if not want or not have or abs(have - want) <= 1:
                break
            c = (inv.V.min(0) + inv.V.max(0)) / 2
            inv.V = np.rint((inv.V - c) * min(1.5, max(0.4, want / have)) + c)
        return dict(template=t, worn=worn, inventory=inv)


def merge_parts(parts):
    """One RS-space mesh from fitted parts (labels, priorities, anchors kept)."""
    parts = [p for p in parts if len(p.F)]
    m = Mesh()
    groups, prio, anchors = [], [], []
    for p in parts:
        m.add(Mesh(p.V, p.F, p.C, L=p.layers()))
        groups += list(p.groups)
        prio += list(p.prio)
        anchors += list(getattr(p, 'anchors', []))
    m.groups, m.prio, m.anchors = groups, prio, anchors
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', default=os.path.join(ROOT, 'data', 'osrs-rev241'),
                    help='flatcache dump (default: the rev 241 extract in data/)')
    ap.add_argument('--models', default=os.path.join(ROOT, 'pipeline_models'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'out_swap'))
    ap.add_argument('--only', default='')
    ap.add_argument('--templates', help='JSON {code: OSRS item name or id} overriding the defaults')
    ap.add_argument('--base-model-id', type=int, default=64000,
                    help='first new model id (must be unused in the server cache; rev 241 ends at 62050)')
    ap.add_argument('--max-faces', type=int, default=2400)
    a = ap.parse_args()

    cache = FlatCache(a.cache)
    fitter = Fitter(cache)
    last = max(cache.archive_ids(7))
    if a.base_model_id <= last:
        raise SystemExit('--base-model-id %d is inside the cache\'s models (last id %d)' % (a.base_model_id, last))
    templates = dict(TEMPLATES)
    if a.templates:
        with open(a.templates) as f:
            templates.update(json.load(f))
    os.makedirs(os.path.join(a.out, 'models'), exist_ok=True)

    next_id, report, written = a.base_model_id, [], {}

    def put(data):
        nonlocal next_id
        written[next_id] = data
        next_id += 1
        return next_id - 1
    for it in ITEMS:
        code = it['code']
        if not code.startswith(a.only):
            continue
        tid = resolve(fitter.defs, templates[code])
        src = load_mesh(os.path.join(a.models, code, 'model.obj'))
        worn_auth = convert(src, it['slot'], a.max_faces, from_design=True)  # player placement, authoring axes
        fit = fitter.fit(it, tid, worn_auth)
        t = fit['template']
        patch, parts_out, ids_by_sig = {}, [], {}
        data, cm, _, prio = encode_part(fit['inventory'])
        patch['inventoryModel'] = put(data)
        parts_out.append(dict(kind='inventory', model=patch['inventoryModel'], replaces=t['inventoryModel'],
                              faces=len(cm.F), priorities=sorted(set(prio))))
        for gender, keys in WORN_KEYS:
            for k in keys:
                patch[k] = -1
            if gender not in fit['worn']:
                continue
            ref_ids, parts = fit['worn'][gender]
            sig = tuple(ref_ids)
            if sig not in ids_by_sig:
                ids = []
                for key, ref_id, part in zip(keys, ref_ids, parts):
                    if not len(part.F):
                        ids.append(-1)  # nothing of ours landed on this part (e.g. no sleeves)
                        parts_out.append(dict(kind=key, model=-1, replaces=ref_id, faces=0))
                        continue
                    data, cm, groups, prio = encode_part(part)
                    ids.append(put(data))
                    parts_out.append(dict(kind=key, model=ids[-1], replaces=ref_id, faces=len(cm.F),
                                          anchors=len(getattr(part, 'anchors', [])), groups=sorted(set(groups)),
                                          template_groups=part.template_groups, priorities=sorted(set(prio))))
                ids_by_sig[sig] = ids
            for k, v in zip(keys, ids_by_sig[sig]):
                patch[k] = v
        patch.update(colorFind=[], colorReplace=[], textureFind=[], textureReplace=[])  # template recolours off
        report.append(dict(code=code, name=it['name'], slot=it['slot'], template_id=tid, template_name=t['name'],
                           template_models={k: t[k] for k in ('inventoryModel', 'maleModel0', 'maleModel1',
                                                              'maleModel2', 'femaleModel0', 'femaleModel1',
                                                              'femaleModel2')},
                           template_recolours=len(t['colorFind']), parts=parts_out, item_def_patch=patch))
        print('%-6s %-28s -> %5d %-24s %s' % (code, it['name'], tid, t['name'],
                                               ' '.join('%s:%d' % (p['kind'], p['model']) for p in parts_out)))

    # verify every written model with RuneLite's own loader
    dec = decode_many(written)
    for e in report:
        for p in e['parts']:
            if p['model'] < 0:
                continue
            d = dec[p['model']]
            p['decoded_faces'] = len(d['F'])
            assert len(d['F']) == p['faces'], (e['code'], p)
            if p['kind'] != 'inventory':
                assert d['vgroup'] is not None and sorted(set(d['vgroup'])) == p['groups'], (e['code'], p['kind'])
    for mid, data in written.items():
        with open(os.path.join(a.out, 'models', '%d.dat' % mid), 'wb') as f:
            f.write(data)
    with open(os.path.join(a.out, 'swaps.json'), 'w') as f:
        json.dump(dict(cache_last_model=last, base_model_id=a.base_model_id, models_written=len(written),
                       swaps=report), f, indent=1)
    print('swap: %d items, %d models (ids %d-%d) -> %s' % (len(report), len(written), a.base_model_id,
                                                          next_id - 1, a.out))


if __name__ == '__main__':
    main()
