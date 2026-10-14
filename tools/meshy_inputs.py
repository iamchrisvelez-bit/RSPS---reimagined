#!/usr/bin/env python3
"""Clean design shots for image-to-3D tools (Meshy, Tripo, Hunyuan3D, ...).

  python3 tools/meshy_inputs.py [--views pipeline_out/01_views] [--out meshy_input] [--size 1024] [--only B08]

For every item: cut from the reference sheet at full quality, background
removed (the stage-1 mask, repaired with GrabCut when OpenCV is installed), centred on a transparent square and upscaled. Writes
meshy_input/<code>_<name>.png and meshy_input/contact_sheet.png (all of them
on grey, for a quick look). stage2 --backend meshy uploads these when present.
"""
import argparse
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

try:
    import cv2  # optional: pip install opencv-python-headless, repairs masks with GrabCut
except ImportError:
    cv2 = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from rsgen.meshy import clean_shot  # noqa: E402


def refine_mask(sheet_bgr, crop, mask, pad=12, strict_shadows=False):
    """Repair a stage-1 mask with GrabCut (OpenCV), seeded by it.

    Stage 1 cut items out by colour, which bites holes where dark armour is
    close to the sheet's dark backdrop. GrabCut models item and backdrop
    colours and fills those in. Only parts touching the old mask are kept and
    inner holes are filled. Falls back to the old mask when OpenCV is missing
    or the result changes implausibly much."""
    old = np.asarray(mask.convert('L')) > 127
    if cv2 is None:
        return mask
    x0, y0, x1, y1 = crop
    H, W = sheet_bgr.shape[:2]
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    img = sheet_bgr[Y0:Y1, X0:X1].copy()
    seed = np.zeros(img.shape[:2], np.uint8)
    seed[y0 - Y0:y0 - Y0 + old.shape[0], x0 - X0:x0 - X0 + old.shape[1]] = old
    gc = np.full(img.shape[:2], cv2.GC_PR_BGD, np.uint8)
    gc[seed > 0] = cv2.GC_PR_FGD
    gc[cv2.erode(seed, np.ones((5, 5), np.uint8)) > 0] = cv2.GC_FGD
    gc[:3] = gc[-3:] = cv2.GC_BGD
    gc[:, :3] = gc[:, -3:] = cv2.GC_BGD
    cv2.grabCut(img, gc, None, np.zeros((1, 65)), np.zeros((1, 65)), 8, cv2.GC_INIT_WITH_MASK)
    new = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8)
    n, lab = cv2.connectedComponents(new)
    keep = np.zeros_like(new)
    for i in range(1, n):
        comp = lab == i
        if (comp & (seed > 0)).sum() > 20:
            keep[comp] = 1
    ff = keep.copy()
    cv2.floodFill(ff, np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8), (0, 0), 2)
    keep[ff == 0] = 1  # fill holes
    keep = keep[y0 - Y0:y0 - Y0 + old.shape[0], x0 - X0:x0 - X0 + old.shape[1]] > 0
    # drop shadows on the sheet are darker than its backdrop; dark armour is lighter
    crop_img = img[y0 - Y0:y0 - Y0 + old.shape[0], x0 - X0:x0 - X0 + old.shape[1]].astype(float)
    border = np.concatenate([img[:3].reshape(-1, 3), img[-3:].reshape(-1, 3), img[:, :3].reshape(-1, 3),
                             img[:, -3:].reshape(-1, 3)]).astype(float)
    bg_level = np.median(border.max(1))
    chroma = crop_img.max(-1) - crop_img.min(-1)
    shadow = (crop_img.max(-1) <= bg_level + 2) & (chroma < 12)
    # shadows fall beside the item; inside its outline hull, dark pixels are armour
    pts = np.argwhere(old)[:, ::-1].astype(np.int32)
    hull = np.zeros(old.shape, np.uint8)
    if len(pts) >= 3:
        cv2.fillConvexPoly(hull, cv2.convexHull(pts), 1)
    if not strict_shadows:
        shadow &= hull == 0
    keep &= old | ~shadow
    # what's enclosed by the item is item (dark armour), shadows sit outside it;
    # then drop specks under 2% of the item
    k8 = keep.astype(np.uint8)
    ff = np.pad(k8, 1)
    cv2.floodFill(ff, np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8), (0, 0), 2)
    k8[ff[1:-1, 1:-1] == 0] = 1
    n, lab, stats, _ = cv2.connectedComponentsWithStats(k8)
    big = np.zeros(n, bool)
    big[1:] = stats[1:, cv2.CC_STAT_AREA] >= 0.02 * k8.sum()
    keep = big[lab]
    added, removed = (keep & ~old).sum(), (old & ~keep).sum()
    if removed > 0.15 * old.sum() or added > 0.4 * old.sum():
        return mask
    return Image.fromarray((keep * 255).astype(np.uint8))


# items whose sheet art casts a dark shadow inside their own outline (between
# a weapon's head and shaft, under boots and robes): dark, flat pixels are
# rejected everywhere for these, not only outside the outline hull. Checked by
# eye on meshy_input/contact_sheet.png.
STRICT_SHADOWS = {'B02_3', 'B03_3', 'B03_4', 'B03_5', 'B03_6', 'B04_1', 'B04_2', 'B04_3', 'B06_3', 'B06_4',
                  'B09_6', 'B12_1', 'B12_4'}


def slug(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def shot_path(out, code):
    hits = sorted(glob.glob(os.path.join(out, code + '_*.png')))
    return hits[0] if hits else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', default=os.path.join(ROOT, 'pipeline_out', '01_views'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'meshy_input'))
    ap.add_argument('--size', type=int, default=1024)
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    sheets, done = {}, []
    for mj in sorted(glob.glob(os.path.join(a.views, '*', 'meta.json'))):
        with open(mj) as f:
            m = json.load(f)
        if not m['code'].startswith(a.only) or 'crop' not in m:
            continue
        sp = os.path.join(ROOT, m.get('sheet', 'reference_sheet.jpg'))
        if sp not in sheets:
            rgb = Image.open(sp).convert('RGB')
            sheets[sp] = (rgb, np.asarray(rgb)[..., ::-1].copy())
        mask = refine_mask(sheets[sp][1], m['crop'], Image.open(os.path.join(os.path.dirname(mj), 'mask.png')),
                           strict_shadows=m['code'] in STRICT_SHADOWS)
        im = clean_shot(sheets[sp][0], m['crop'], mask, a.size)
        path = os.path.join(a.out, '%s_%s.png' % (m['code'], slug(m['name'])))
        im.save(path)
        done.append((m['code'], m['name'], im))
    T, cols = 200, 12
    sheet = Image.new('RGB', (cols * T, ((len(done) + cols - 1) // cols) * (T + 16)), (40, 40, 44))
    dr = ImageDraw.Draw(sheet)
    for i, (code, name, im) in enumerate(done):
        x, y = (i % cols) * T, (i // cols) * (T + 16)
        bg = Image.new('RGBA', im.size, (205, 205, 205, 255))
        bg.alpha_composite(im)
        sheet.paste(bg.convert('RGB').resize((T, T), Image.LANCZOS), (x, y))
        dr.text((x + 3, y + T + 2), code, fill=(230, 230, 230))
    if not a.only:
        sheet.save(os.path.join(a.out, 'contact_sheet.png'))
    print('%d clean shots -> %s' % (len(done), a.out))


if __name__ == '__main__':
    main()
