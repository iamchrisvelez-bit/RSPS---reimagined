#!/usr/bin/env python3
"""Stage 3 - any 3D model -> RuneScape model files.

Input: a stage-2 output folder (default), or any .obj/.ply/.glb file or a
folder of them (from Blender, an AI image-to-3D tool, ...).

Per model:
  1. load (OBJ+MTL/textures, PLY, GLB with textures), reorient to y-up/+z-front
  2. fit into the equipment slot's box on the standard player (head, body,
     legs, feet, hands, cape) or centre it in item space (weapon, shield,
     neck)
  3. decimate to the face budget (vertex clustering keeps the low-poly look)
  4. snap to the integer grid, drop degenerate faces, map colours to the RS
     HSL palette, encode (classic model format, readable by 317 and OSRS)
  5. decode again and require an exact match, then write .dat/.gz, an OBJ of
     the result, a preview render and a 36x32 inventory sprite

  python3 pipeline/stage3_models_to_rs.py [--in pipeline_out/02_models] [--out pipeline_out/03_rs]
  python3 pipeline/stage3_models_to_rs.py --in sword.glb --slot weapon --up z --forward -y
"""
import argparse
import glob
import gzip
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from rsgen import rsformat, render  # noqa: E402
from rsgen.fit import SLOT_BOX, WORN_SLOTS, decimate, fit_to_slot, reorient  # noqa: E402
from rsgen.meshio import load_mesh  # noqa: E402

VIEW = {'weapon': dict(yaw=-18, pitch=10), 'shield': dict(yaw=-28, pitch=12),
        'neck': dict(yaw=-12, pitch=8), 'cape': dict(yaw=200, pitch=12)}


def collect(inp):
    """[(code, path, meta)] from a file, a folder of meshes or a stage-2 folder."""
    if os.path.isfile(inp):
        code = os.path.splitext(os.path.basename(inp))[0]
        return [(code, inp, {'code': code, 'name': code})]
    out = []
    for mj in sorted(glob.glob(os.path.join(inp, '*', 'meta.json'))):
        with open(mj) as f:
            meta = json.load(f)
        out.append((meta['code'], os.path.join(os.path.dirname(mj), meta.get('model', 'model.obj')), meta))
    if not out:
        for p in sorted(glob.glob(os.path.join(inp, '*'))):
            if os.path.splitext(p)[1].lower() in ('.obj', '.ply', '.glb'):
                code = os.path.splitext(os.path.basename(p))[0]
                out.append((code, p, {'code': code, 'name': code}))
    return out


def rot_z(V, deg):
    a = np.radians(deg)
    return V @ np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]]).T


def convert(mesh, slot, max_faces, up='y', forward='z', fill=1.0):
    m = reorient(mesh, up, forward)
    m = fit_to_slot(m, slot, fill)
    m = decimate(m, max_faces)
    return rsformat.clean(m)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--in', dest='inp', default=os.path.join(ROOT, 'pipeline_out', '02_models'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'pipeline_out', '03_rs'))
    ap.add_argument('--slot', choices=sorted(SLOT_BOX), help='override the slot from stage-1 metadata')
    ap.add_argument('--up', default='y', help="source up axis: x, y, z, -x, -y, -z (Blender exports: 'z')")
    ap.add_argument('--forward', default='z', help="source axis the item's front faces (Blender: '-y')")
    ap.add_argument('--max-faces', type=int, default=2400)
    ap.add_argument('--fill', type=float, default=1.0, help='fraction of the slot box to fill')
    ap.add_argument('--base-model-id', type=int, default=61000)
    ap.add_argument('--only', default='')
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    report, tiles = [], []
    for k, (code, path, meta) in enumerate(collect(a.inp)):
        if not code.startswith(a.only):
            continue
        slot = a.slot or meta.get('slot') or 'weapon'
        src = load_mesh(path)
        m = convert(src, slot, a.max_faces, a.up, a.forward, a.fill)
        data = rsformat.encode(m)
        dec = rsformat.decode(data)
        V = dec['V'] * np.array([1, -1, -1])
        if not (np.array_equal(V, m.V) and np.array_equal(dec['F'], m.F)
                and dec['colors'] == rsformat.rgb_to_hsl16(m.C)):
            raise AssertionError('%s: decoded model differs from the encoded mesh' % code)
        mid = a.base_model_id + k
        d = os.path.join(a.out, code)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, '%d.dat' % mid), 'wb') as f:
            f.write(data)
        with gzip.GzipFile(os.path.join(d, '%d.gz' % mid), 'wb', 9, mtime=0) as f:
            f.write(data)
        rsformat.write_obj(m, os.path.join(d, 'rs_model.obj'), code)
        cols = [rsformat.hsl16_to_rgb(h) for h in dec['colors']]
        v = VIEW.get(slot, dict(yaw=-32, pitch=16))
        Vr = rot_z(V, v.get('roll', 0))
        img = render.render(Vr, dec['F'], cols, None, size=360, yaw=v['yaw'], pitch=v['pitch'])
        img.save(os.path.join(d, 'preview.png'))
        render.item_sprite(render.render_rgba(Vr, dec['F'], cols, 256, v['yaw'], v['pitch'])).save(
            os.path.join(d, 'sprite.png'))
        tiles.append(render.label(img.copy(), code, meta.get('name', code)))
        lo, hi = m.bounds()
        report.append(dict(code=code, name=meta.get('name', code), slot=slot, model_id=mid,
                           worn_placement='on_body' if slot in WORN_SLOTS else 'item_space',
                           source=os.path.relpath(path, ROOT) if path.startswith(ROOT) else path,
                           source_faces=int(len(src.F)), faces=int(len(m.F)), vertices=int(len(m.V)),
                           bytes=len(data), bounds_min=[int(x) for x in lo], bounds_max=[int(x) for x in hi]))
        print('%-6s %-28s %-6s id=%d faces %d -> %d' % (code, meta.get('name', code), slot, mid, len(src.F),
                                                        len(m.F)))
    with open(os.path.join(a.out, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    if tiles:
        render.sheet(tiles, 12, 240).save(os.path.join(a.out, 'SHEET.png'))
    print('stage 3: %d RS models -> %s' % (len(report), a.out))


if __name__ == '__main__':
    main()
