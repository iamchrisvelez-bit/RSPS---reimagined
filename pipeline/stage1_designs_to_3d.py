#!/usr/bin/env python3
"""Stage 1 - design sheet -> per-item "3D images".

Cuts every item out of the reference sheet and writes, per item:
  color.png   RGBA cutout (transparent background)
  mask.png    item silhouette
  depth.png   16-bit depth map (white = nearest the viewer)
  normal.png  tangent-space normal map derived from the depth
  meta.json   code, name, slot, crop box, depth scale

Depth comes from the silhouette (a rounded "inflation" profile from the
distance to the edge) plus fine relief from the artwork's own shading. It
is an estimate, not a measurement: good enough for the relief
reconstruction in stage 2 and as conditioning for AI image-to-3D tools.

  python3 pipeline/stage1_designs_to_3d.py [--sheet reference_sheet.jpg] [--out pipeline_out/01_views]
"""
import argparse
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

GRID_COLS, GRID_ROWS = 3, 5          # panels on the reference sheet
ITEMS_PER_PANEL = 6
LABEL_BOX = (0, 0, 140, 52)          # "B01" caption in each panel's corner


def item_names():
    """code -> (name, slot) from the model library, when available."""
    try:
        from rsgen.items import ITEMS
        return {i['code']: (i['name'], i['slot']) for i in ITEMS}
    except Exception:  # stage 1 must work without the library
        return {}


def foreground_mask(panel):
    """Separate artwork from the dark, vignetted backdrop and soft shadows.
    A pixel is foreground when it differs in colour from the local backdrop
    or carries texture (gradient energy); shadows are smooth and dark, so
    they fail both tests."""
    a = np.asarray(panel).astype(np.float32)
    lum = a.mean(-1)
    border = np.concatenate([a[:3].reshape(-1, 3), a[-3:].reshape(-1, 3), a[:, :3].reshape(-1, 3),
                             a[:, -3:].reshape(-1, 3)])
    bg0 = np.median(border, axis=0)
    rough = np.abs(a - bg0).max(-1) > 22
    fill = a.copy()
    fill[rough] = bg0
    bg = np.asarray(Image.fromarray(fill.astype(np.uint8)).filter(ImageFilter.GaussianBlur(28))).astype(np.float32)
    diff = np.abs(a - bg).max(-1)
    sat = a.max(-1) - a.min(-1)
    gy, gx = np.gradient(lum)
    grad = np.asarray(Image.fromarray(np.clip(np.hypot(gx, gy) * 8, 0, 255).astype(np.uint8))
                      .filter(ImageFilter.BoxBlur(2))).astype(np.float32) / 8
    m = (diff > 14) | (sat > 34) | ((grad > 4) & (lum > bg.mean(-1) + 3))
    img = Image.fromarray((m * 255).astype(np.uint8))
    img = img.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))  # close small gaps
    img = img.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))  # drop speckle
    m = np.asarray(img) > 127
    # erase the white caption text (not the artwork behind/around it)
    x0, y0, x1, y1 = LABEL_BOX
    text = (lum > 150) & (sat < 40)
    text = np.asarray(Image.fromarray((text * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))) > 127
    box = np.zeros_like(m)
    box[y0:y1, x0:x1] = True
    m = m & ~(text & box)
    return fill_holes(m)


def fill_holes(m):
    """Fill background regions not connected to the border."""
    h, w = m.shape
    outside = np.zeros_like(m)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not m[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if not m[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not m[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                q.append((ny, nx))
    return ~outside


def components(m, min_area):
    """Connected components (4-neighbour) as lists of (y, x) arrays."""
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    comps = []
    for sy, sx in zip(*np.nonzero(m)):
        if lab[sy, sx]:
            continue
        k = len(comps) + 1
        lab[sy, sx] = k
        q, pix = deque([(sy, sx)]), []
        while q:
            y, x = q.popleft()
            pix.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = k
                    q.append((ny, nx))
        comps.append(np.array(pix))
    return [c for c in comps if len(c) >= min_area]


def split_touching(mask, n, min_area=60, max_iter=12):
    """When fewer than n blobs exist, erode until touching items separate,
    then grow the cores back over the original mask (multi-source BFS)."""
    cur = Image.fromarray((mask * 255).astype(np.uint8))
    for _ in range(max_iter):
        cur = cur.filter(ImageFilter.MinFilter(3))
        cores = components(np.asarray(cur) > 127, min_area)
        if len(cores) >= n:
            break
    else:
        return components(mask, min_area)
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    q = deque()
    for k, c in enumerate(cores, 1):
        lab[c[:, 0], c[:, 1]] = k
        q.extend(map(tuple, c))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                lab[ny, nx] = lab[y, x]
                q.append((ny, nx))
    return [np.argwhere(lab == k) for k in range(1, len(cores) + 1)]


def split_oversized(comps, shape, ratio=2.0):
    """Split blobs much larger than the typical item (two touching items)."""
    out = []
    big = sorted(len(c) for c in comps)
    med = float(np.median(big[-ITEMS_PER_PANEL:])) if big else 0
    for c in comps:
        if med and len(c) > ratio * med:
            m = np.zeros(shape, bool)
            m[c[:, 0], c[:, 1]] = True
            parts = split_touching(m, 2)
            if len(parts) >= 2:
                out += parts
                continue
        out.append(c)
    return out


def group_items(comps, n):
    """Merge the closest components (pairs like gauntlets, twin mauls) until
    exactly n items remain; returns per-item pixel arrays in reading order."""
    groups = [c for c in comps]
    med = float(np.median([len(g) for g in groups]))
    while len(groups) > n:
        boxes = [(g[:, 0].min(), g[:, 1].min(), g[:, 0].max(), g[:, 1].max()) for g in groups]
        best = None
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                a, b = boxes[i], boxes[j]
                gap = max(0, max(a[0], b[0]) - min(a[2], b[2])) + max(0, max(a[1], b[1]) - min(a[3], b[3]))
                # prefer joining close, small pieces (a pair of greaves) over two large items
                cost = gap + 40.0 * (len(groups[i]) + len(groups[j])) / med
                if best is None or cost < best[0]:
                    best = (cost, i, j)
        _, i, j = best
        groups[i] = np.vstack([groups[i], groups[j]])
        del groups[j]
    if len(groups) < n:
        raise RuntimeError('found only %d items (expected %d)' % (len(groups), n))
    centres = [(g[:, 0].mean(), g[:, 1].mean()) for g in groups]
    order = sorted(range(n), key=lambda k: centres[k][0])
    rows, cur = [], [order[0]]
    for k in order[1:]:  # split into rows where the vertical gap is large
        if centres[k][0] - centres[cur[-1]][0] > 60:
            rows.append(cur)
            cur = [k]
        else:
            cur.append(k)
    rows.append(cur)
    return [groups[k] for r in rows for k in sorted(r, key=lambda k: centres[k][1])]


def distance_to_edge(mask):
    """Approximate Euclidean distance (pixels) from the silhouette edge, by
    repeated erosion alternating square and cross kernels (octagonal metric)."""
    d = np.zeros(mask.shape, np.float32)
    cur = Image.fromarray((mask * 255).astype(np.uint8))
    k = 0
    while True:
        a = np.asarray(cur) > 127
        if not a.any():
            break
        d += a
        if k % 2:
            cur = cur.filter(ImageFilter.MinFilter(3))
        else:  # cross-shaped erosion = min of the two 1-pixel shifts
            arr = np.asarray(cur)
            sh = np.minimum.reduce([arr, np.roll(arr, 1, 0), np.roll(arr, -1, 0), np.roll(arr, 1, 1),
                                    np.roll(arr, -1, 1)])
            cur = Image.fromarray(sh)
        k += 1
    return d


def depth_map(rgb, mask, relief=0.12):
    """Rounded inflation from the silhouette + shading relief."""
    d = distance_to_edge(mask)
    R = max(float(d.max()), 1.0)
    base = np.sqrt(np.clip(2 * R * d - d * d, 0, None))  # circular profile: 0 at the edge, R at the core
    lum = np.asarray(rgb.convert('L')).astype(np.float32)
    blur = np.asarray(Image.fromarray(lum.astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))).astype(np.float32)
    detail = (lum - blur) / 255.0 * R * relief * 4
    z = np.where(mask, np.clip(base + detail, 0, None), 0)
    return z


def normal_map(z):
    gy, gx = np.gradient(z)
    n = np.dstack([-gx, gy, np.ones_like(z)])
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sheet', default=os.path.join(ROOT, 'reference_sheet.jpg'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'pipeline_out', '01_views'))
    ap.add_argument('--batches', default='', help='comma list, e.g. B06,B12 (default: all)')
    ap.add_argument('--pad', type=int, default=6)
    a = ap.parse_args()

    sheet = Image.open(a.sheet).convert('RGB')
    pw, ph = sheet.width // GRID_COLS, sheet.height // GRID_ROWS
    names = item_names()
    wanted = set(filter(None, a.batches.split(',')))
    contact = []
    for n in range(GRID_COLS * GRID_ROWS):
        batch = 'B%02d' % (n + 1)
        x0, y0 = (n % GRID_COLS) * pw, (n // GRID_COLS) * ph
        panel = sheet.crop((x0, y0, x0 + pw, y0 + ph))
        mask = foreground_mask(panel)
        comps = components(mask, 150)
        if not comps:
            continue  # empty panel (the sheet has 14 batches on a 15-cell grid)
        if wanted and batch not in wanted:
            continue
        if len(comps) < ITEMS_PER_PANEL:
            comps = split_touching(mask, ITEMS_PER_PANEL)
        comps = split_oversized(comps, mask.shape)
        items = group_items(comps, ITEMS_PER_PANEL)
        for k, pix in enumerate(items, 1):
            code = '%s_%d' % (batch, k)
            ys, xs = pix[:, 0], pix[:, 1]
            bx0, by0 = int(max(0, xs.min() - a.pad)), int(max(0, ys.min() - a.pad))
            bx1, by1 = int(min(pw, xs.max() + 1 + a.pad)), int(min(ph, ys.max() + 1 + a.pad))
            m = np.zeros((ph, pw), bool)
            m[ys, xs] = True
            m = m[by0:by1, bx0:bx1]
            rgb = panel.crop((bx0, by0, bx1, by1))
            z = depth_map(rgb, m)
            d = os.path.join(a.out, code)
            os.makedirs(d, exist_ok=True)
            rgba = rgb.copy()
            rgba.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
            rgba.save(os.path.join(d, 'color.png'))
            Image.fromarray((m * 255).astype(np.uint8)).save(os.path.join(d, 'mask.png'))
            zmax = float(z.max()) or 1.0
            Image.fromarray((z / zmax * 65535).astype(np.uint16)).save(os.path.join(d, 'depth.png'))
            Image.fromarray(normal_map(z)).save(os.path.join(d, 'normal.png'))
            name, slot = names.get(code, (code, None))
            with open(os.path.join(d, 'meta.json'), 'w') as f:
                json.dump(dict(code=code, name=name, slot=slot, sheet=os.path.basename(a.sheet),
                               crop=[x0 + bx0, y0 + by0, x0 + bx1, y0 + by1], size=[bx1 - bx0, by1 - by0],
                               depth_scale_px=zmax), f, indent=1)
            contact.append((code, rgba, Image.fromarray(normal_map(z))))
            print('%-6s %-28s crop=%s' % (code, name, [x0 + bx0, y0 + by0, bx1 - bx0, by1 - by0]))
    if contact:
        T = 128
        sheet_out = Image.new('RGB', (T * 2 * 6, T * ((len(contact) + 5) // 6)), (22, 22, 26))
        for i, (code, rgba, nrm) in enumerate(contact):
            for j, im in enumerate((rgba, nrm)):
                im = im.copy()
                im.thumbnail((T - 8, T - 8))
                cell = Image.new('RGB', (T, T), (22, 22, 26))
                cell.paste(im, ((T - im.width) // 2, (T - im.height) // 2), im if im.mode == 'RGBA' else None)
                sheet_out.paste(cell, ((i % 6) * 2 * T + j * T, (i // 6) * T))
        sheet_out.save(os.path.join(a.out, 'CONTACT.png'))
    print('stage 1: %d items -> %s' % (len(contact), a.out))


if __name__ == '__main__':
    main()
