#!/usr/bin/env python3
"""All-direction QA renders of the packaged models with the Hermes render lab.

  python3 tools/qa_render.py [--obj out/obj] [--out out/qa] [--blender .venv-blender/bin/python]
                             [--render-script ../hermes-dock/hermes_dock/blender_render.py] [--only B02]

Each worn model in out/obj is rendered from ten directions by Blender (Cycles, CPU):
front, back, left, right, top, bottom and the four upper diagonals. Writes:

  out/qa/<code>.png    the design next to the ten views
  out/qa/index.png     the front three-quarter view of every item
  out/qa/report.json   geometry facts and checks for each item
  out/qa/REPORT.md     the same as a table, failures first

Checks for each item:
  render      every view shows the model (no blank or clipped frame)
  size        dimensions plausible for the slot, in RS units (a player is ~200 tall)
  fragments   loose parts: a few are normal (straps, gems, trims); many mean the mesh broke up
  degenerate  zero-area faces in the OBJ (anchors are excluded from out/obj, so there should be none)
Non-manifold edges are reported but not failed: RS models are open shells, not closed solids.
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWS = ['front', 'back', 'left', 'right', 'top', 'bottom', 'three_quarter', 'three_quarter_left',
         'back_three_quarter', 'back_three_quarter_left']
# largest dimension, RS units: (min, max) per slot
SIZE = {'head': (25, 110), 'body': (40, 140), 'legs': (40, 140), 'hands': (10, 120), 'feet': (10, 110),
        'cape': (40, 200), 'neck': (8, 90), 'shield': (25, 150), 'weapon': (25, 260), '2h': (40, 300),
        'ring': (4, 60), 'ammo': (4, 80)}
MAX_LOOSE = 40


def read_obj(path):
    V, F = [], []
    with open(path) as f:
        for line in f:
            if line.startswith('v '):
                V.append([float(x) for x in line.split()[1:4]])
            elif line.startswith('f '):
                F.append([int(t.split('/')[0]) - 1 for t in line.split()[1:]])
    return np.array(V), F


def degenerate(V, F):
    n = 0
    for f in F:
        a, b, c = V[f[0]], V[f[1]], V[f[2]]
        n += np.linalg.norm(np.cross(b - a, c - a)) < 1e-9
    return int(n)


def coverage(png):
    """Fraction of the frame the model covers, and whether it touches the border (clipped)."""
    im = np.asarray(Image.open(png).convert('RGB')).astype(int)
    bg = im[0, 0]
    fg = np.abs(im - bg).sum(-1) > 12
    edge = fg[0].any() or fg[-1].any() or fg[:, 0].any() or fg[:, -1].any()
    return float(fg.mean()), bool(edge)


def render(blender, script, obj, out_dir, size, samples):
    r = subprocess.run([blender, script, obj, out_dir, 'all', str(size), str(samples)], capture_output=True,
                       text=True, timeout=600, env={'PATH': os.environ.get('PATH', ''), 'HOME': os.environ.get('HOME', '')})
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])
    with open(os.path.join(out_dir, 'stats.json')) as f:
        return json.load(f)


def sheet(code, name, design, views_dir, size, notes):
    W = size
    im = Image.new('RGB', (W * 6, W * 2 + 40), (22, 22, 26))
    dr = ImageDraw.Draw(im)
    dr.text((6, 4), '%s  %s' % (code, name), fill=(235, 235, 235))
    dr.text((6, 20), notes, fill=(170, 200, 170) if notes.startswith('PASS') else (240, 150, 120))
    if design and os.path.exists(design):
        d = Image.open(design).convert('RGB')
        d.thumbnail((W, 2 * W))
        im.paste(d, ((W - d.width) // 2, 40 + (2 * W - d.height) // 2))
        dr.text((4, 42), 'design', fill=(200, 200, 200))
    for i, v in enumerate(VIEWS):
        x, y = W * (1 + i % 5), 40 + W * (i // 5)
        im.paste(Image.open(os.path.join(views_dir, v + '.png')).convert('RGB').resize((W, W)), (x, y))
        dr.text((x + 4, y + 2), v.replace('_', ' '), fill=(220, 220, 220))
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--obj', default=os.path.join(ROOT, 'out', 'obj'))
    ap.add_argument('--manifest', default=os.path.join(ROOT, 'out', 'manifest.json'))
    ap.add_argument('--designs', default=os.path.join(ROOT, 'pipeline_out', '01_views'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'out', 'qa'))
    ap.add_argument('--blender', default=os.environ.get('HERMES_BLENDER_PYTHON',
                                                        os.path.join(ROOT, '.venv-blender', 'bin', 'python')))
    ap.add_argument('--render-script', default=os.path.join(os.path.dirname(ROOT), 'hermes-dock', 'hermes_dock',
                                                            'blender_render.py'))
    ap.add_argument('--size', type=int, default=256)
    ap.add_argument('--samples', type=int, default=16)
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    with open(a.manifest) as f:
        items = {m['code']: m for m in json.load(f)['items']}
    objs = sorted(p for p in glob.glob(os.path.join(a.obj, '*.obj')) if os.path.basename(p).startswith(a.only))
    os.makedirs(a.out, exist_ok=True)
    work = os.path.join(a.out, 'views')

    def one(obj):
        code = '_'.join(os.path.basename(obj).split('_')[:2])
        d = os.path.join(work, code)
        os.makedirs(d, exist_ok=True)
        return code, obj, render(a.blender, a.render_script, obj, d, a.size, a.samples)

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        done = list(ex.map(one, objs))
    report = []
    for code, obj, st in done:
        m = items.get(code, {})
        slot = m.get('slot', '')
        V, F = read_obj(obj)
        cov = {v: coverage(os.path.join(work, code, v + '.png')) for v in VIEWS}
        big = max(st['dimensions'])
        lo, hi = SIZE.get(slot, (4, 300))
        fails = []
        blank = [v for v, (c, _) in cov.items() if c < 0.002]
        clipped = [v for v, (_, e) in cov.items() if e]
        if blank or clipped:
            fails.append('render: %s' % ', '.join(['blank ' + v for v in blank] + ['clipped ' + v for v in clipped]))
        if not lo <= big <= hi:
            fails.append('size: %.0f outside %d-%d for %s' % (big, lo, hi, slot))
        if st['loose_parts'] > MAX_LOOSE:
            fails.append('fragments: %d loose parts' % st['loose_parts'])
        deg = degenerate(V, F)
        if deg:
            fails.append('degenerate: %d zero-area faces' % deg)
        r = dict(code=code, name=m.get('name', ''), slot=slot, triangles=st['triangles'],
                 vertices=len(V), dimensions=st['dimensions'], loose_parts=st['loose_parts'],
                 non_manifold_edges=st['non_manifold_edges'], degenerate_faces=deg, colours=len(st['materials']),
                 view_coverage={v: round(c, 3) for v, (c, _) in cov.items()}, fails=fails, ok=not fails)
        report.append(r)
        notes = ('PASS' if not fails else 'CHECK: ' + '; '.join(fails)) + \
            '   %d tris  %d loose parts  %d non-manifold edges  %s units' % (
                st['triangles'], st['loose_parts'], st['non_manifold_edges'],
                ' x '.join('%.0f' % x for x in st['dimensions']))
        sheet(code, m.get('name', ''), os.path.join(a.designs, code, 'color.png'), os.path.join(work, code),
              a.size, notes).save(os.path.join(a.out, code + '.png'))
    # index: three-quarter view of every item
    n, T = len(report), 160
    cols = 12
    idx = Image.new('RGB', (cols * T, ((n + cols - 1) // cols) * (T + 14)), (22, 22, 26))
    dr = ImageDraw.Draw(idx)
    for i, r in enumerate(report):
        x, y = (i % cols) * T, (i // cols) * (T + 14)
        idx.paste(Image.open(os.path.join(work, r['code'], 'three_quarter.png')).convert('RGB').resize((T, T)), (x, y))
        dr.text((x + 3, y + T), r['code'], fill=(220, 220, 220) if r['ok'] else (240, 140, 110))
    idx.save(os.path.join(a.out, 'index.png'))
    with open(os.path.join(a.out, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    lines = ['# All-direction QA (%d models, %d views each)' % (n, len(VIEWS)), '',
             '%d pass, %d to check. Sheets: `out/qa/<code>.png`, overview: `out/qa/index.png`.' % (
                 sum(r['ok'] for r in report), sum(not r['ok'] for r in report)), '',
             '| Item | Slot | Tris | Loose parts | Non-manifold edges | Size (units) | Result |', '|---|---|---|---|---|---|---|']
    for r in sorted(report, key=lambda r: (r['ok'], r['code'])):
        lines.append('| %s %s | %s | %d | %d | %d | %s | %s |' % (
            r['code'], r['name'], r['slot'], r['triangles'], r['loose_parts'], r['non_manifold_edges'],
            ' x '.join('%.0f' % x for x in r['dimensions']), 'pass' if r['ok'] else '; '.join(r['fails'])))
    with open(os.path.join(a.out, 'REPORT.md'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:3]))
    return 0 if all(r['ok'] for r in report) else 1


if __name__ == '__main__':
    sys.exit(main())
