#!/usr/bin/env python3
"""Side-by-side review sheets: reference panel (left) vs current renders (right).

  python3 tools/compare.py [B06 ...]   -> out/compare/<batch>.png
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL_W, CELL_H, COLS = 640, 360, 3


def reference_panel(batch):
    n = int(batch[1:]) - 1
    ref = Image.open(os.path.join(ROOT, 'reference_sheet.jpg')).convert('RGB')
    x, y = (n % COLS) * CELL_W, (n // COLS) * CELL_H
    return ref.crop((x, y, x + CELL_W, y + CELL_H))


def main(batches):
    os.makedirs(os.path.join(ROOT, 'out', 'compare'), exist_ok=True)
    for b in batches:
        ref = reference_panel(b).resize((1080, 608))
        sheet = Image.open(os.path.join(ROOT, 'out', 'sheets', b + '.png')).convert('RGB')
        sheet = sheet.resize((int(sheet.width * 608 / sheet.height), 608))
        out = Image.new('RGB', (ref.width + sheet.width + 10, 608), (0, 0, 0))
        out.paste(ref, (0, 0))
        out.paste(sheet, (ref.width + 10, 0))
        out.save(os.path.join(ROOT, 'out', 'compare', b + '.png'))


if __name__ == '__main__':
    main(sys.argv[1:] or ['B%02d' % i for i in range(1, 15)])
