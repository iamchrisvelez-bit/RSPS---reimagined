#!/usr/bin/env python3
"""Build every redesign into game-ready assets.

  python3 build.py [--source pipeline|handbuilt] [--base-model-id 60000] [--base-item-id 30000] [--only B06]

Sources:
  pipeline   (default) the models refined from the design sheet
             (pipeline_models/<code>/model.obj, made by
             pipeline/refine_to_match.py): true design colours with shadows
             and texture, detail-line strips drawn over the surface (higher
             face priority), smooth (Gouraud) shading
  handbuilt  the procedural models in rsgen/items.py (flat shading)

For each item this writes:
  out/models/<id>.dat  (+ .gz)  RS classic-format models: an inventory model
                                (centred on the origin) and a worn model
  out/sprites/<item_id>.png     36x32 client-style inventory sprite
  out/obj/, out/renders/        OBJ/MTL source and 480px preview
  out/defs/                     item definitions (JSON, RuneLite field names,
                                317 Java snippet)
  out/manifest.json             everything above, machine readable

Every model is decoded again right after encoding and must match the cleaned
mesh exactly; previews and sprites are rendered from that decoded data.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rsgen import rsformat, render  # noqa: E402
from rsgen.items import ITEMS  # noqa: E402
from rsgen.requirements import requirements  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'out')
PIPELINE_MODELS = os.path.join(ROOT, 'pipeline_models')
MAX_FACES = 2400  # per model; tests/test_assets.py allows up to 3000

# OSRS / 317 equipment slot indices
SLOT_ID = {'head': 0, 'cape': 1, 'neck': 2, 'weapon': 3, 'body': 4, 'shield': 5, 'legs': 7,
           'hands': 9, 'feet': 10}

# Icon camera angles (RS angle units: 2048 = 360 degrees) per slot.
ICON_ANGLES = {
    'body': (500, 0), 'legs': (500, 0), 'head': (100, 0), 'hands': (420, 828), 'feet': (164, 156),
    'cape': (380, 1024), 'neck': (424, 68), 'shield': (344, 1104), 'weapon': (498, 484),
}


def slug(name):
    return ''.join(c if c.isalnum() else '_' for c in name.lower()).strip('_')


def rot_z(V, deg):
    a = math.radians(deg)
    R = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    return V @ R.T


def hidden_kits(it):
    """Player kit parts to hide while worn (wearPos2/3), declared per item."""
    return list(it['hides'])


def pipeline_build(code, slot, models_dir=PIPELINE_MODELS):
    """Worn-placement mesh for a pipeline model (same fitting as stage 3)."""
    sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
    from rsgen.meshio import load_mesh
    from stage3_models_to_rs import convert
    path = os.path.join(models_dir, code, 'model.obj')
    if not os.path.exists(path):
        raise SystemExit('no pipeline model %s - run pipeline/refine_to_match.py --out pipeline_models '
                         '(or build with --source handbuilt)' % path)
    return convert(load_mesh(path), slot, MAX_FACES, from_design=True)


def write_model(mesh, model_id, smooth=False):
    """Encode, verify by decoding, write .dat/.gz. Returns (decoded, bytes)."""
    data = rsformat.encode(mesh, smooth=smooth)
    dec = rsformat.decode(data)
    V = dec['V'] * np.array([1, -1, -1])
    prio = dec['priorities']
    if not (np.array_equal(dec['F'], mesh.F) and np.array_equal(V, mesh.V)
            and dec['colors'] == rsformat.rgb_to_hsl16(mesh.C)
            and dec['render_types'] == [0 if smooth else 1] * len(mesh.F)
            and [p - min(prio, default=0) for p in prio] == mesh.layers()):
        raise AssertionError('round-trip mismatch for model %d' % model_id)
    with open(os.path.join(OUT, 'models', '%d.dat' % model_id), 'wb') as f:
        f.write(data)
    with gzip.GzipFile(os.path.join(OUT, 'models', '%d.gz' % model_id), 'wb', 9, mtime=0) as f:
        f.write(data)
    return dec, data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base-model-id', type=int, default=60000,
                    help='first model id; each item uses two consecutive ids (inventory, worn)')
    ap.add_argument('--base-item-id', type=int, default=30000, help='first item id')
    ap.add_argument('--only', default='', help='build only codes starting with this prefix (no manifest)')
    ap.add_argument('--size', type=int, default=480, help='preview render size')
    ap.add_argument('--source', choices=['pipeline', 'handbuilt'], default='pipeline',
                    help='which models to package (see above)')
    ap.add_argument('--models', default=PIPELINE_MODELS, help='pipeline models folder')
    a = ap.parse_args()
    smooth = a.source == 'pipeline'


    if not a.only and os.path.isdir(OUT):
        shutil.rmtree(OUT)  # never leave stale ids from an older numbering behind
    for d in ('models', 'obj', 'renders', 'sheets', 'sprites', 'defs'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    manifest, tiles, by_batch = [], [], {}
    for idx, it in enumerate(ITEMS):
        if not it['code'].startswith(a.only):
            continue
        if a.source == 'pipeline':
            worn = pipeline_build(it['code'], it['slot'], a.models)
        else:
            worn = rsformat.clean(it['build']())
        lo, hi = worn.bounds()
        centre = np.rint((lo + hi) / 2)
        inv = worn.copy().move(*(-centre))
        inv_id, worn_id = a.base_model_id + 2 * idx, a.base_model_id + 2 * idx + 1
        item_id = a.base_item_id + idx
        dec_inv, data_inv = write_model(inv, inv_id, smooth)
        dec_worn, data_worn = write_model(worn, worn_id, smooth)

        base = '%s_%s' % (it['code'], slug(it['name']))
        rsformat.write_obj(worn, os.path.join(OUT, 'obj', base + '.obj'), base)

        v = it['view']
        Vr = rot_z(dec_inv['V'] * np.array([1, -1, -1]), v.get('roll', 0))
        cols = [rsformat.hsl16_to_rgb(h) for h in dec_inv['colors']]
        yaw, pitch = v.get('yaw', -32), v.get('pitch', 16)
        look = dict(smooth=smooth, layers=inv.layers())
        img = render.render(Vr, dec_inv['F'], cols, inv.G, size=a.size, yaw=yaw, pitch=pitch, **look)
        img.save(os.path.join(OUT, 'renders', base + '.png'))
        sprite = render.item_sprite(render.render_rgba(Vr, dec_inv['F'], cols, 256, yaw, pitch, **look))
        sprite.save(os.path.join(OUT, 'sprites', '%d.png' % item_id))
        tile = render.label(img.copy(), it['code'], it['name'])
        tiles.append(tile)
        by_batch.setdefault(it['code'][:3], []).append(tile)

        extent = float((hi - lo).max())
        xan, yan = ICON_ANGLES[it['slot']]
        hide = hidden_kits(it)
        action = 'Wield' if it['slot'] in ('weapon', 'shield') else 'Wear'
        manifest.append(dict(
            code=it['code'], name=it['name'], slot=it['slot'], equip_slot=SLOT_ID[it['slot']],
            item_id=item_id, inventory_model=inv_id, worn_model=worn_id,
            worn_placement='on_body' if it['slot'] in ('head', 'body', 'legs', 'hands', 'feet', 'cape')
            else 'item_space_needs_offset',
            hide_kits=hide, action=action,
            requirements=[dict(skill=n, skill_id=i, level=lv) for n, i, lv in requirements(it['code'])],
            icon=dict(zoom2d=int(round(extent * 12.5)), xan2d=xan, yan2d=yan, zan2d=0, xOffset2d=0, yOffset2d=0),
            files=dict(inventory_dat='models/%d.dat' % inv_id, inventory_gz='models/%d.gz' % inv_id,
                       worn_dat='models/%d.dat' % worn_id, worn_gz='models/%d.gz' % worn_id,
                       sprite='sprites/%d.png' % item_id, obj='obj/%s.obj' % base,
                       render='renders/%s.png' % base),
            sha1=dict(inventory=hashlib.sha1(data_inv).hexdigest(), worn=hashlib.sha1(data_worn).hexdigest()),
            vertices=int(len(worn.V)), faces=int(len(worn.F)),
            worn_bounds_min=[int(x) for x in lo], worn_bounds_max=[int(x) for x in hi],
            colors_hsl=sorted(set(dec_worn['colors'])),
        ))
        print('%-6s %-28s %-6s item=%d inv=%d worn=%d v=%d f=%d' % (
            it['code'], it['name'], it['slot'], item_id, inv_id, worn_id, len(worn.V), len(worn.F)))

    for b, ts in by_batch.items():
        render.sheet(ts, 3, 360, b).save(os.path.join(OUT, 'sheets', '%s.png' % b))
    if a.only:
        print('partial build: manifest and defs not written')
        return
    render.sheet(tiles, 12, 240).save(os.path.join(OUT, 'sheets', 'ALL.png'))
    sheet = render.Image.new('RGBA', (36 * 12, 32 * 7), (62, 53, 41, 255))  # inventory brown
    for i, m in enumerate(manifest):
        with render.Image.open(os.path.join(OUT, m['files']['sprite'])) as s:
            sheet.alpha_composite(s, ((i % 12) * 36, (i // 12) * 32))
    sheet.resize((sheet.width * 3, sheet.height * 3), render.Image.NEAREST).save(
        os.path.join(OUT, 'sheets', 'SPRITES_x3.png'))

    with open(os.path.join(OUT, 'manifest.json'), 'w') as f:
        json.dump(dict(format='rs-classic-model', source=a.source, shading='smooth' if smooth else 'flat',
                       base_model_id=a.base_model_id,
                       base_item_id=a.base_item_id, count=len(manifest), items=manifest), f, indent=1)
    write_defs(manifest)
    print('built %d items, %d models' % (len(manifest), 2 * len(manifest)))


def write_defs(manifest):
    # RuneLite cache ItemDefinition field names (OSRS-revision servers / cache editors)
    osrs = []
    for m in manifest:
        ic = m['icon']
        d = dict(id=m['item_id'], name=m['name'], inventoryModel=m['inventory_model'],
                 zoom2d=ic['zoom2d'], xan2d=ic['xan2d'], yan2d=ic['yan2d'], zan2d=ic['zan2d'],
                 xOffset2d=0, yOffset2d=0, cost=1, stackable=0, members=True, tradeable=True,
                 interfaceOptions=[None, m['action'], None, None, 'Drop'],
                 maleModel0=m['worn_model'], femaleModel0=m['worn_model'],
                 wearPos1=m['equip_slot'],
                 wearPos2=m['hide_kits'][0] if len(m['hide_kits']) > 0 else -1,
                 wearPos3=m['hide_kits'][1] if len(m['hide_kits']) > 1 else -1)
        osrs.append(d)
    with open(os.path.join(OUT, 'defs', 'osrs_item_definitions.json'), 'w') as f:
        json.dump(osrs, f, indent=1)

    # 317 client snippet (deob field names; rename to your base's ItemDef fields)
    lines = ['// Generated by build.py -- paste inside ItemDef.forID(int id) after the item is read.',
             '// Field names follow the common 317 deob; rename if your base differs (see HANDOFF.md).',
             'switch (id) {']
    for m in manifest:
        ic = m['icon']
        lines += ['case %d: // %s %s' % (m['item_id'], m['code'], m['name']),
                  '    itemDef.name = "%s";' % m['name'],
                  '    itemDef.description = "A redesigned %s.".getBytes();' % m['name'].lower(),
                  '    itemDef.modelID = %d;' % m['inventory_model'],
                  '    itemDef.modelZoom = %d;' % ic['zoom2d'],
                  '    itemDef.modelRotation1 = %d;' % ic['xan2d'],
                  '    itemDef.modelRotation2 = %d;' % ic['yan2d'],
                  '    itemDef.modelOffset1 = 0;',
                  '    itemDef.modelOffset2 = 0;',
                  '    itemDef.maleEquip1 = %d;' % m['worn_model'],
                  '    itemDef.femaleEquip1 = %d;' % m['worn_model'],
                  '    itemDef.actions = new String[] {null, "%s", null, null, "Drop"};' % m['action'],
                  '    itemDef.stackable = false;',
                  '    break;']
    lines.append('}')
    with open(os.path.join(OUT, 'defs', 'ItemDef317_snippet.java'), 'w') as f:
        f.write('\n'.join(lines) + '\n')

    # Server-side equip requirements (skill levels), generic
    with open(os.path.join(OUT, 'defs', 'requirements.json'), 'w') as f:
        json.dump([dict(item_id=m['item_id'], name=m['name'], requirements=m['requirements']) for m in manifest],
                  f, indent=1)

    # Server-side equipment table (slot + hidden kits), generic
    with open(os.path.join(OUT, 'defs', 'equipment.json'), 'w') as f:
        json.dump([dict(item_id=m['item_id'], name=m['name'], equip_slot=m['equip_slot'],
                        slot=m['slot'], hide_kits=m['hide_kits'],
                        two_handed=m['code'] in ('B03_4', 'B03_5', 'B09_1', 'B09_2', 'B09_3', 'B09_4',
                                                 'B09_5', 'B09_6', 'B11_4', 'B11_6', 'B03_2'))
                   for m in manifest], f, indent=1)


if __name__ == '__main__':
    main()
