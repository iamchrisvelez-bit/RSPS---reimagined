#!/usr/bin/env python3
"""Stage 2 (refine backend) - iterate renders, adding faces until the model
matches the design image.

For every stage-1 item:

  1. start    a coarse model: simplified silhouette + a few interior points
  2. render   the model's front view at the design's resolution (an exact
              orthographic, pixel-aligned render of every facet's colour)
  3. compare  against the design: silhouette IoU and colour accuracy (the
              share of design pixels whose facet colour is within reach of
              the design's own colour there)
  4. refine   add points exactly where the error is - silhouette misses snap
              to the true outline, colour misses snap onto the nearest colour
              border - then rebuild the triangles (rounds that make the match
              worse are undone)
  5. repeat   until the score reaches --target, the next round would pass the
              RS face budget (--max-faces, front + back), or extra faces stop
              helping (best score up less than --min-gain over 3 rounds)

Shadows and texture (--mode detail, the default): each face takes the
design's true colour under it, so baked shadows, ambient occlusion,
highlights and surface texture (scales, cracks, weave, glow lines) are part of
what gets matched. Only part of the broad light gradient is removed, because
the RS client lights the model itself. Areas darker than their surroundings
(gaps between plates, recesses) are also dented into the geometry (--cavity),
so in-game lighting shades them as well. The back is a coarse, rim-sealed
version of the front (--back-share of the budget), leaving the rest of the
faces for front detail. --mode flat keeps the earlier 8-tone, shading-free
look.

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

from rsgen.lowpoly import (_components, boundary_pixels, collapse_interior, rasterize_labels,  # noqa: E402
                           simplify, trace_outline, triangulate_points)
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


def shading_target(color, mask, broad_div=5.0, strength=0.5):
    """The design with shadows and texture kept. Only part of the broad
    lighting gradient is removed (the RS client lights the model by its
    normals itself); crevice shadows, ambient occlusion, highlights and surface
    texture all stay in the colours the faces are matched against."""
    rgb = np.asarray(color.convert('RGB')).astype(np.float64)
    m = mask
    h, w = m.shape
    lum = rgb.mean(-1)
    wsum = blur(m.astype(np.float64), max(h, w) / broad_div)
    broad = blur(lum * m, max(h, w) / broad_div) / np.maximum(wsum, 1e-6)
    mean = lum[m].mean() if m.any() else 1.0
    gain = (mean / np.maximum(broad, 1.0)) ** strength
    return np.clip(rgb * gain[..., None], 0, 255)


def cavity_relief(target, mask, size, gain=0.06):
    """Shadows as geometry: pixels darker than their surroundings (crevices,
    gaps between plates, recessed panels) become dents in the depth, so the
    in-game lighting shades them too. Returns depth offsets (0..-gain)."""
    lum = target.mean(-1)
    wsum = blur(mask.astype(np.float64), size / 25)
    local = blur(lum * mask, size / 25) / np.maximum(wsum, 1e-6)
    dark = np.clip((local - lum) / np.maximum(local, 1.0), 0, 1) * mask
    return -gain * np.clip(blur(dark, 1.0) * 2.5, 0, 1)


COLOUR_TOL = 24.0  # RGB distance that still reads as the same colour


def colour_score(cov, img, mask, target):
    """(combined, silhouette IoU, colour accuracy) of a true-colour render."""
    iou = (cov & mask).sum() / max(1, (cov | mask).sum())
    dist = np.linalg.norm(img - target, axis=-1)
    acc = ((dist < COLOUR_TOL) & cov & mask).sum() / max(1, mask.sum())
    return 0.5 * iou + 0.5 * acc, float(iou), float(acc)


def colour_error_map(cov, img, mask, target, r):
    dist = np.linalg.norm(img - target, axis=-1)
    err = (cov ^ mask) * 2.0 + np.clip(dist / (2 * COLOUR_TOL), 0, 1.5) * (mask & cov)
    return blur(err, r) if r >= 1 else err


def face_colours(ids, target, P, T):
    """Mean design colour under each triangle (centroid pixel for slivers)."""
    n = len(T)
    sel = ids >= 0
    cnt = np.bincount(ids[sel], minlength=n).astype(np.float64)
    cols = np.stack([np.bincount(ids[sel], target[..., c][sel], minlength=n) for c in range(3)], 1)
    h, w = ids.shape
    for i in np.where(cnt == 0)[0]:
        cy, cx = P[T[i]].mean(0)
        cols[i] = target[min(h - 1, int(cy)), min(w - 1, int(cx))]
        cnt[i] = 1
    return cols / cnt[:, None]


class Refiner:
    def __init__(self, mask, labels, start_points=60, seed=0, target=None):
        """labels: palette labels (flat mode). With target (HxWx3 design
        colours, detail mode) every face takes the true colour under it and
        the match is judged on colour, so shadows and texture are refined too."""
        self.m, self.L, self.target = mask, labels, target
        self.cols = self.img = None
        self.back_faces = None  # None: back mirrors the front; n: coarse back of ~n faces
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
        return (list(self.edge), list(self.interior), set(self.used), self.P, self.T, self.lab, self.rim, self.R,
                self.cols, self.img)

    def restore(self, snap, ban_last=True):
        """Go back to a snapshot; ban_last keeps the points just added (which
        made things worse) from being tried at the same spots again."""
        if ban_last:
            for y, x in self.last_added:
                self.tabu[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = True
            self.banned |= set(self.edge) - set(snap[0])
        (edge, interior, used, self.P, self.T, self.lab, self.rim, self.R, self.cols, self.img) = snap
        self.edge, self.interior, self.used = list(edge), list(interior), set(used)

    def points(self):
        return np.array(self.edge + self.interior, float)

    def build(self):
        P = self.points()
        T, lab, rim = triangulate_points(self.m, self.L, P, len(self.edge))
        self.P, self.T, self.lab, self.rim = P, T, lab, rim
        if self.target is None:
            self.R = rasterize_labels(P, T, lab, self.m.shape)
        else:
            self.R = rasterize_labels(P, T, np.arange(len(T)), self.m.shape)  # face id per pixel
            self.lab = np.arange(len(T))
            self.cols = face_colours(self.R, self.target, P, T)
            self.img = np.zeros(self.m.shape + (3,))
            self.img[self.R >= 0] = self.cols[self.R[self.R >= 0]]
        return self

    def score(self):
        if self.target is None:
            return score(self.R, self.m, self.L)
        return colour_score(self.R >= 0, self.img, self.m, self.target)

    def error(self, r):
        if self.target is None:
            return error_map(self.R, self.m, self.L, r)
        return colour_error_map(self.R >= 0, self.img, self.m, self.target, r)

    def picture(self, pal=None):
        if self.target is None:
            return flat_image(self.R, pal)
        img = np.full(self.m.shape + (3,), 24.0)
        cov = self.R >= 0
        img[cov] = self.img[cov]
        return Image.fromarray(img.astype(np.uint8))

    def faces(self):
        if self.back_faces is None:
            return 2 * len(self.T)  # front + mirrored back
        # coarse back: rim vertices are locked, so it can't get below ~1 face per rim point
        return len(self.T) + max(self.back_faces, len(self.edge))

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
        err = self.error(self.spacing * 0.6)
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
                smooth=3, mode='detail', cavity=0.06, back_share=0.15, log=None):
    """Returns (mesh, history, snapshots). history: one dict per round.

    mode 'detail': faces take the design's true colours, shadows and texture
    included, and darker-than-surroundings areas are dented into the geometry
    (cavity) so in-game lighting shades them too.
    mode 'flat': the design reduced to `colors` flat tones, shading removed.
    back_share: fraction of the face budget for a coarse back (the rim stays
    shared, so the model is closed); the front gets the rest. None mirrors the
    front onto the back (half the budget each)."""
    m = np.asarray(mask.convert('L')) > 127
    detail = None
    if mode == 'detail':
        tgt = shading_target(color, m)
        L, pal = palette_labels(tgt, m, 16, smooth=1)  # only used for border snapping
        ref = Refiner(m, L, start_points, seed, target=tgt)
        if cavity:
            detail = cavity_relief(tgt, m, max(m.shape), cavity)
    elif mode == 'flat':
        rgb = delit(color, delight)
        # the target is the design reduced to flat colour shapes (speckle and
        # shading noise smoothed away)
        L, pal = palette_labels(rgb, m, colors, smooth=smooth)
        ref = Refiner(m, L, start_points, seed)
    else:
        raise ValueError('mode must be detail or flat')
    if back_share:
        ref.back_faces = int(max_faces * back_share)
    history, snaps = [], []
    best, trail = None, []  # trail: best score after each round
    for rnd in range(max_rounds + 1):
        s, iou, acc = ref.score()
        history.append({'round': rnd, 'points': len(ref.P), 'faces': ref.faces(), 'score': round(float(s), 4),
                        'iou': round(iou, 4), 'colour': round(acc, 4)})
        snaps.append((ref.picture(pal), history[-1]))
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
        # a new point costs ~2 front faces (~4 when the back mirrors the front)
        room = (max_faces - ref.faces()) // (4 if ref.back_faces is None else 2)
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
    _, (_, _, _, P, T, lab, rim, R, cols, img) = best
    if cols is not None:
        lab, pal = np.arange(len(T)), cols
    else:
        img = np.zeros(m.shape + (3,))
        img[R >= 0] = np.asarray(pal, float)[R[R >= 0]]
    back = None
    if ref.back_faces is not None:
        Tb = collapse_interior(P, T, rim, max(ref.back_faces, max_faces - len(T)))
        ids = rasterize_labels(P, Tb, np.arange(len(Tb)), m.shape)
        back = (Tb, face_colours(ids, img, P, Tb) * 0.8)  # the front's look, a little darker
    mesh = mesh_from_triangles(P, T, lab, rim, pal, m, depth, thickness, depth_gain, detail=detail, back=back)
    history[-1]['back_faces'] = 0 if back is None else len(back[0])
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
    ap.add_argument('--mode', choices=['detail', 'flat'], default='detail',
                    help='detail: true colours with shadows and texture (default); flat: 8 flat tones')
    ap.add_argument('--cavity', type=float, default=0.06, help='detail: how deep dark crevices are dented (0 = off)')
    ap.add_argument('--back-share', type=float, default=0.15,
                    help='share of the face budget for the coarse back (0 = mirror the front)')
    ap.add_argument('--colors', type=int, default=8, help='flat mode: number of tones')
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
            start_points=a.start_points, colors=a.colors, delight=a.delight, depth_gain=a.depth_gain,
            mode=a.mode, cavity=a.cavity, back_share=a.back_share or None, log=print)
        out = os.path.join(a.out, meta['code'])
        os.makedirs(out, exist_ok=True)
        write_obj_rgb(mesh, os.path.join(out, 'model.obj'), meta['code'])
        best = max(hist, key=lambda r: r['score'])
        with open(os.path.join(out, 'meta.json'), 'w') as f:
            json.dump(dict(meta, backend='refine', mode=a.mode, model='model.obj', vertices=len(mesh.V), faces=len(mesh.F),
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
