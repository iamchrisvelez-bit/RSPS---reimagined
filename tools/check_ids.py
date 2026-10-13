#!/usr/bin/env python3
"""Check that our model and item ids are free in a game cache before packing.

  python3 tools/check_ids.py --cache <flatcache dump of the SERVER's cache> [--manifest out/manifest.json]
                             [--swaps out_swap/swaps.json]

Exit 0 when nothing collides. The server's cache is what counts: an OpenRune
server adds its own custom items and models on top of the game's (rev 241
alone ends at item 34645, model 62050), so check against an export of the
server's actual cache, not only the stock one.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'tools')]
from osrs.cache import FlatCache  # noqa: E402
from osrs.defs import ITEM_ARCHIVE  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', required=True)
    ap.add_argument('--manifest', default=os.path.join(ROOT, 'out', 'manifest.json'))
    ap.add_argument('--swaps', default=os.path.join(ROOT, 'out_swap', 'swaps.json'))
    a = ap.parse_args()
    c = FlatCache(a.cache)
    models = set(c.archive_ids(7))
    item_ids = set(c.files(2, ITEM_ARCHIVE))
    bad = 0
    if os.path.exists(a.manifest):
        with open(a.manifest) as f:
            man = json.load(f)
        for m in man['items']:
            for key in ('inventory_model', 'worn_model'):
                if m[key] in models:
                    print('COLLISION model %d (%s %s) already in the cache' % (m[key], m['code'], key))
                    bad += 1
            if m['item_id'] in item_ids:
                print('COLLISION item %d (%s) already in the cache' % (m['item_id'], m['code']))
                bad += 1
        print('%s: %d items checked' % (a.manifest, len(man['items'])))
    if os.path.exists(a.swaps):
        with open(a.swaps) as f:
            sw = json.load(f)
        n = 0
        for e in sw['swaps']:
            for p in e['parts']:
                if p['model'] >= 0:
                    n += 1
                    if p['model'] in models:
                        print('COLLISION model %d (%s %s) already in the cache' % (p['model'], e['code'], p['kind']))
                        bad += 1
        print('%s: %d swap models checked' % (a.swaps, n))
    print('cache: %d models (last %d), %d items (last %d)' % (len(models), max(models), len(item_ids), max(item_ids)))
    print('OK' if not bad else '%d collisions' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
