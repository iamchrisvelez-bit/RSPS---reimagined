#!/usr/bin/env python3
"""Side-by-side review sheets: reference panel (left) vs renders (right).

  python3 tools/compare.py [B06 ...]              hand-built models  -> out/compare/
  python3 tools/compare.py --pipeline [B06 ...]   pipeline RS models -> pipeline_out/compare/
"""
import glob
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
CELL_W, CELL_H, COLS = 640, 360, 3


def reference_panel(batch):
    n = int(batch[1:]) - 1
    ref = Image.open(os.path.join(ROOT, 'reference_sheet.jpg')).convert('RGB')
    x, y = (n % COLS) * CELL_W, (n // COLS) * CELL_H
    return ref.crop((x, y, x + CELL_W, y + CELL_H))


def pipeline_sheet(batch):
    from rsgen import render
    tiles = [render.label(Image.open(p).convert('RGB'), os.path.basename(os.path.dirname(p)))
             for p in sorted(glob.glob(os.path.join(ROOT, 'pipeline_out', '03_rs', batch + '_*', 'preview.png')))]
    return render.sheet(tiles, 3, 300) if tiles else None


def main(args):
    pipeline = '--pipeline' in args
    batches = [a for a in args if a != '--pipeline'] or ['B%02d' % i for i in range(1, 15)]
    out_dir = os.path.join(ROOT, 'pipeline_out' if pipeline else 'out', 'compare')
    os.makedirs(out_dir, exist_ok=True)
    for b in batches:
        sheet = pipeline_sheet(b) if pipeline else Image.open(os.path.join(ROOT, 'out', 'sheets', b + '.png'))
        if sheet is None:
            continue
        ref = reference_panel(b).resize((1080, 608))
        sheet = sheet.convert('RGB')
        sheet = sheet.resize((int(sheet.width * 608 / sheet.height), 608))
        out = Image.new('RGB', (ref.width + sheet.width + 10, 608), (0, 0, 0))
        out.paste(ref, (0, 0))
        out.paste(sheet, (ref.width + 10, 0))
        out.save(os.path.join(out_dir, b + '.png'))


if __name__ == '__main__':
    main(sys.argv[1:])
