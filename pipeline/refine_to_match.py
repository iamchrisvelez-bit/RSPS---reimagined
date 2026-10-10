#!/usr/bin/env python3
"""Stage 2 (refine backend) - iterate renders, adding faces until the model
matches the design image.

For every stage-1 item:

  1. start    a coarse model: simplified silhouette + a few interior points
  2. render   the model's front view at the design's resolution (an exact
              orthographic, pixel-aligned render of every facet's flat colour)
  3. compare  against the design: silhouette IoU and colour accuracy (the
              share of design pixels whose facet has the right palette colour)
  4. refine   add points exactly where the error is - silhouette misses snap
              to the true outline, colour misses go inside - then rebuild the
              triangles
  5. repeat   until the score reaches --target, the next round would pass the
              RS face budget (--max-faces, front + back), or extra faces stop
              helping (best score up less than --min-gain over 3 rounds)

Writes pipeline_out/02_models/<code>/model.obj (+ .mtl, meta.json with the
score history) - the same layout as every stage-2 backend, so stage 3 converts
it - plus refine.png (design | rounds | final) for review.

  python3 pipeline/refine_to_match.py [--only B14] [--target 0.97] [--max-faces 2400]
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))

from rsgen.lowpoly import (_components, boundary_pixels, rasterize_labels, simplify,  # noqa: E402
                           trace_outline, triangulate_points)
from rsgen.meshio import write_obj_rgb  # noqa: E402
from rsgen.render import render  # noqa: E402
from stage2_images_to_models import THICKNESS, blur, delit, mesh_from_triangles, palette_labels  # noqa: E402


def outline_rings(mask, eps):
    """Simplified outline ring (y, x pixel-corner coords) of each sizeable blob."""
    lab, comps = _components(mask)
    rings = []
    for k, n in comps:
        if n < 30:
            continue
        ring = simplify(trace_outline(lab == k), eps)
        if len(ring) >= 3:
            rings.append(np.asarray(ring, float))
    return rings


def score(R, mask, L):
    """(combined, silhouette IoU, colour accuracy) of a label render R."""
    cov = R >= 0
    iou = (cov & mask).sum() / max(1, (cov | mask).sum())
    acc = ((R == L) & mask).sum() / max(1, mask.sum())
    return 0.5 * iou + 0.5 * acc, float(iou), float(acc)


def error_map(R, mask, L, r):
    """Where the render disagrees with the design, blurred so isolated stray
    pixels count less than solid wrong areas. Silhouette errors weigh double:
    they change the outline you see in game."""
    cov = R >= 0
    err = ((cov ^ mask) * 2.0 + ((R != L) & mask & cov) * 1.0).astype(np.float64)
    return blur(err, r) if r >= 1 else err


class Refiner:
    def __init__(self, mask, labels, start_points=60, seed=0):
        self.m, self.L = mask, labels
        h, w = mask.shape
        size = max(h, w)
        # the exact outline (every pixel corner that matters) is the pool new
        # silhouette points are snapped to; start from a coarse version of it
        self.fine = np.vstack(outline_rings(mask, 0.5))
        coarse = outline_rings(mask, max(1.5, size / 45))
        self.edge = [tuple(p) for ring in coarse for p in ring]
        self.used = {tuple(p) for p in self.edge}
        self.near_edge = boundary_pixels(mask) | boundary_pixels(~mask)
        inner = mask & ~boundary_pixels(mask)
        self.inner = inner & ~boundary_pixels(inner)
        self.interior = []
        rng = np.random.default_rng(seed)
        cand = np.argwhere(self.inner)
        if len(cand):
            pick = rng.choice(len(cand), min(start_points, len(cand)), replace=False)
            self.interior = [(y + 0.5, x + 0.5) for y, x in cand[pick]]
        self.spacing = max(1.5, size / 90)
        # colour-region borders: points placed on them make triangle edges
        # follow the design's colour shapes instead of cutting across them
        b = np.zeros_like(mask)
        b[:-1] |= (labels[:-1] != labels[1:]) & mask[:-1] & mask[1:]
        b[:, :-1] |= (labels[:, :-1] != labels[:, 1:]) & mask[:, :-1] & mask[:, 1:]
        self.border = b & self.inner
        self.tabu = np.zeros_like(mask)  # spots whose points made a round worse
        self.last_added = []
        self.banned = set()  # outline points that made a round worse
        self.build()

    def snapshot(self):
        return (list(self.edge), list(self.interior), set(self.used), self.P, self.T, self.lab, self.rim, self.R)

    def restore(self, snap, ban_last=True):
        """Go back to a snapshot; ban_last keeps the points just added (which
        made things worse) from being tried at the same spots again."""
        if ban_last:
            for y, x in self.last_added:
                self.tabu[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = True
            self.banned |= set(self.edge) - set(snap[0])
        (edge, interior, used, self.P, self.T, self.lab, self.rim, self.R) = snap
        self.edge, self.interior, self.used = list(edge), list(interior), set(used)

    def points(self):
        return np.array(self.edge + self.interior, float)

    def build(self):
        P = self.points()
        T, lab, rim = triangulate_points(self.m, self.L, P, len(self.edge))
        self.P, self.T, self.lab, self.rim = P, T, lab, rim
        self.R = rasterize_labels(P, T, lab, self.m.shape)
        return self

    def faces(self):
        return 2 * len(self.T)  # front + back

    def snap(self, y, x, taken):
        """Nearest free colour-border pixel within a couple of spacings, else (y, x)."""
        h, w = self.m.shape
        r = int(np.ceil(self.spacing * 2))
        y0, y1, x0, x1 = max(0, y - r), min(h, y + r + 1), max(0, x - r), min(w, x + r + 1)
        cand = np.argwhere(self.border[y0:y1, x0:x1] & ~taken[y0:y1, x0:x1])
        if not len(cand):
            return y, x
        j = np.argmin((cand[:, 0] + y0 - y) ** 2 + (cand[:, 1] + x0 - x) ** 2)
        return int(cand[j, 0] + y0), int(cand[j, 1] + x0)

    def add(self, k):
        """Add up to k points at the worst-matching places; returns how many."""
        h, w = self.m.shape
        err = error_map(self.R, self.m, self.L, self.spacing * 0.6)
        taken = self.tabu.copy()
        self.last_added = []
        rr = int(np.ceil(self.spacing))
        yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
        disc = (yy ** 2 + xx ** 2) <= self.spacing ** 2

        def stamp(y, x):
            y, x = int(y), int(x)
            y0, y1, x0, x1 = max(0, y - rr), min(h, y + rr + 1), max(0, x - rr), min(w, x + rr + 1)
            taken[y0:y1, x0:x1] |= disc[y0 - y + rr:y1 - y + rr, x0 - x + rr:x1 - x + rr]
        for y, x in self.P:
            stamp(min(h - 1, y), min(w - 1, x))
        order = np.argsort(-err, axis=None)
        added = 0
        for idx in order:
            y, x = divmod(int(idx), w)
            if err[y, x] <= 0.05 or added >= k:
                break
            if taken[y, x]:
                continue
            if self.near_edge[y, x] or not self.m[y, x]:
                # silhouette error: insert the nearest true-outline corner
                d = (self.fine[:, 0] - (y + 0.5)) ** 2 + (self.fine[:, 1] - (x + 0.5)) ** 2
                for j in np.argsort(d)[:6]:
                    p = tuple(self.fine[j])
                    if p not in self.used and p not in self.banned:
                        self.edge.append(p)
                        self.used.add(p)
                        self.last_added.append((y, x))
                        added += 1
                        break
                stamp(y, x)
            elif self.inner[y, x]:
                y, x = self.snap(y, x, taken)
                self.interior.append((y + 0.5, x + 0.5))
                self.last_added.append((y, x))
                added += 1
                stamp(y, x)
            else:
                stamp(y, x)
        return added


def flat_image(R, pal):
    img = np.full(R.shape + (3,), 24, np.uint8)
    img[R >= 0] = np.asarray(pal, np.uint8)[R[R >= 0]]
    return Image.fromarray(img)


def refine_item(color, mask, depth, thickness=0.6, max_faces=2400, target=0.97, min_gain=0.004, patience=3,
                step=0.12, start_points=60, colors=8, delight=0.75, depth_gain=1.0, max_rounds=40, seed=0,
                smooth=3, log=None):
    """Returns (mesh, history, snapshots). history: one dict per round."""
    m = np.asarray(mask.convert('L')) > 127
    rgb = delit(color, delight)
    # the target is the design reduced to flat colour shapes (speckle and
    # shading noise smoothed away): what a low-poly RS model can show
    L, pal = palette_labels(rgb, m, colors, smooth=smooth)
    ref = Refiner(m, L, start_points, seed)
    history, snaps = [], []
    best, trail = None, []  # trail: best score after each round
    for rnd in range(max_rounds + 1):
        s, iou, acc = score(ref.R, m, L)
        history.append({'round': rnd, 'points': len(ref.P), 'faces': ref.faces(), 'score': round(float(s), 4),
                        'iou': round(iou, 4), 'colour': round(acc, 4)})
        snaps.append((flat_image(ref.R, pal), history[-1]))
        if log:
            log('  round %2d  faces %4d  score %.3f  (silhouette %.3f, colour %.3f)'
                % (rnd, ref.faces(), s, iou, acc))
        if best is None or s >= best[0]:
            best = (s, ref.snapshot())
        elif s < best[0] - 0.001:
            # this round's new points made the match worse (e.g. a Delaunay
            # edge now cuts across a concave outline): undo it and try elsewhere
            history[-1]['rolled_back'] = True
            ref.restore(best[1])
        if s >= target:
            history[-1]['stop'] = 'target'
            break
        # patience in productive rounds (undone rounds don't count); twice as
        # patient while less than half the face budget is used
        if not history[-1].get('rolled_back'):
            trail.append(best[0])
        wait = patience * (2 if ref.faces() < max_faces / 2 else 1)
        if len(trail) > wait and trail[-1] - trail[-1 - wait] < min_gain:
            history[-1]['stop'] = 'plateau'
            break
        if rnd == max_rounds:
            history[-1]['stop'] = 'rounds'
            break
        # roughly: faces ~ 2 * 2 * points, so k new points cost ~4k faces
        room = (max_faces - ref.faces()) // 4
        k = int(min(max(12, len(ref.P) * step), room))
        if k <= 0 or not ref.add(k):
            history[-1]['stop'] = 'budget' if k <= 0 else 'no error left to fix'
            break
        prev = ref.snapshot()
        ref.build()
        if ref.faces() > max_faces:  # overshot: keep the last model that fit
            ref.restore(prev, ban_last=False)
            history[-1]['stop'] = 'budget'
            break
    _, (_, _, _, P, T, lab, rim, _) = best
    mesh = mesh_from_triangles(P, T, lab, rim, pal, m, depth, thickness, depth_gain)
    return mesh, history, snaps


def progress_sheet(color, snaps, mesh, title, tile=200):
    """design | selected rounds (flat front render + score) | lit 3D render."""
    pick = snaps if len(snaps) <= 5 else [snaps[i] for i in np.linspace(0, len(snaps) - 1, 5).round().astype(int)]
    tiles = [(color.convert('RGBA'), 'design')]
    tiles += [(im, 'r%d  %d faces  %.3f' % (hh['round'], hh['faces'], hh['score'])) for im, hh in pick]
    lit = render(mesh.V, mesh.F, mesh.C, size=tile, yaw=-20, pitch=8)
    tiles.append((lit, '3D'))
    sheet = Image.new('RGB', (tile * len(tiles), tile + 34), (18, 18, 22))
    dr = ImageDraw.Draw(sheet)
    dr.text((6, 2), title, fill=(230, 230, 230))
    for i, (im, cap) in enumerate(tiles):
        im = im.copy()
        im.thumbnail((tile - 8, tile - 8), Image.NEAREST)
        bg = Image.new('RGB', im.size, (24, 24, 24))
        bg.paste(im, mask=im.split()[-1] if im.mode == 'RGBA' else None)
        sheet.paste(bg, (i * tile + (tile - im.width) // 2, 16 + (tile - im.height) // 2))
        dr.text((i * tile + 6, tile + 18), cap, fill=(200, 200, 200))
    return sheet


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', default=os.path.join(ROOT, 'pipeline_out', '01_views'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'pipeline_out', '02_models'))
    ap.add_argument('--only', default='')
    ap.add_argument('--target', type=float, default=0.97, help='stop at this match score (0..1)')
    ap.add_argument('--max-faces', type=int, default=2400, help='RS face budget (front + back)')
    ap.add_argument('--min-gain', type=float, default=0.004,
                    help='plateau: stop when the best score rose less than this over the last 3 rounds')
    ap.add_argument('--start-points', type=int, default=60)
    ap.add_argument('--colors', type=int, default=8)
    ap.add_argument('--delight', type=float, default=0.75)
    ap.add_argument('--depth-gain', type=float, default=1.0)
    a = ap.parse_args()
    n, summary = 0, []
    for mj in sorted(glob.glob(os.path.join(a.views, '*', 'meta.json'))):
        d = os.path.dirname(mj)
        with open(mj) as f:
            meta = json.load(f)
        if not meta['code'].startswith(a.only):
            continue
        print('%s %s' % (meta['code'], meta['name']))
        color = Image.open(os.path.join(d, 'color.png'))
        mesh, hist, snaps = refine_item(
            color, Image.open(os.path.join(d, 'mask.png')), Image.open(os.path.join(d, 'depth.png')),
            THICKNESS.get(meta.get('slot'), 0.6), a.max_faces, a.target, a.min_gain,
            start_points=a.start_points, colors=a.colors, delight=a.delight, depth_gain=a.depth_gain, log=print)
        out = os.path.join(a.out, meta['code'])
        os.makedirs(out, exist_ok=True)
        write_obj_rgb(mesh, os.path.join(out, 'model.obj'), meta['code'])
        best = max(hist, key=lambda r: r['score'])
        with open(os.path.join(out, 'meta.json'), 'w') as f:
            json.dump(dict(meta, backend='refine', model='model.obj', vertices=len(mesh.V), faces=len(mesh.F),
                           match=best, stop=hist[-1].get('stop'), history=hist), f, indent=1)
        progress_sheet(color, snaps, mesh, '%s %s - stop: %s' % (meta['code'], meta['name'], hist[-1].get('stop'))) \
            .save(os.path.join(out, 'refine.png'))
        summary.append((meta['code'], len(mesh.F), best['score'], hist[-1].get('stop')))
        n += 1
    for code, f, s, why in summary:
        print('%-6s faces %4d  match %.3f  stop %s' % (code, f, s, why))
    print('refine: %d models -> %s' % (n, a.out))


if __name__ == '__main__':
    main()
