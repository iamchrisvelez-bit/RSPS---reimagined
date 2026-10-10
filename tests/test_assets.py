"""Release checks for the generated assets. Run after `python3 build.py`:

    python3 -m unittest discover -s tests -v
"""
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'out')
sys.path.insert(0, ROOT)
from rsgen import rsformat  # noqa: E402
from rsgen.geom import Mesh  # noqa: E402
from rsgen.items import ITEMS  # noqa: E402


MAX_FACES = 3000  # keep worn models light: the client draws every face of every visible player


def read(path, mode='rb'):
    with open(path, mode) as f:
        return f.read()


def load_manifest():
    with open(os.path.join(OUT, 'manifest.json')) as f:
        return json.load(f)


class TestEncoder(unittest.TestCase):
    def test_smart_boundaries(self):
        for v in (-16384, -65, -64, -1, 0, 1, 63, 64, 16383):
            b = rsformat._smart(v)
            self.assertEqual(rsformat._R(b, 0).smart(), v)
            self.assertEqual(len(b), 1 if -64 <= v < 64 else 2)
        for v in (-16385, 16384):
            with self.assertRaises(ValueError):
                rsformat._smart(v)

    def test_rejects_unclean_mesh(self):
        m = Mesh([(0, 0, 0), (10.5, 0, 0), (0, 10, 0)], [(0, 1, 2)])
        with self.assertRaises(ValueError):
            rsformat.encode(m)

    def test_clean_drops_degenerate_and_welds(self):
        m = Mesh([(0, 0, 0), (10, 0, 0), (0, 10, 0), (0.2, 0.1, 0), (20, 0, 0)],
                 [(0, 1, 2), (0, 3, 1), (0, 1, 4)])
        c = rsformat.clean(m)
        self.assertEqual(len(c.F), 1)
        self.assertEqual(len(c.V), 3)

    def test_deterministic(self):
        it = ITEMS[0]
        a = rsformat.encode(rsformat.clean(it['build']()))
        b = rsformat.encode(rsformat.clean(it['build']()))
        self.assertEqual(a, b)


class TestOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.man = load_manifest()
        cls.items = cls.man['items']

    def test_counts_and_unique_ids(self):
        self.assertEqual(self.man['count'], len(ITEMS))
        self.assertEqual(len(self.items), 84)
        ids = [m['item_id'] for m in self.items]
        models = [x for m in self.items for x in (m['inventory_model'], m['worn_model'])]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len(set(models)), len(models))
        self.assertEqual(sorted(models), list(range(self.man['base_model_id'], self.man['base_model_id'] + 168)))
        self.assertEqual(len({m['code'] for m in self.items}), 84)

    def test_no_stale_files(self):
        on_disk = {f for f in os.listdir(os.path.join(OUT, 'models'))}
        expected = {'%d.%s' % (x, e) for m in self.items for x in (m['inventory_model'], m['worn_model'])
                    for e in ('dat', 'gz')}
        self.assertEqual(on_disk, expected)

    def test_models_decode_and_are_valid(self):
        for m in self.items:
            for kind in ('inventory', 'worn'):
                with self.subTest(code=m['code'], kind=kind):
                    data = read(os.path.join(OUT, m['files'][kind + '_dat']))
                    self.assertEqual(hashlib.sha1(data).hexdigest(), m['sha1'][kind])
                    gz = gzip.decompress(read(os.path.join(OUT, m['files'][kind + '_gz'])))
                    self.assertEqual(gz, data)
                    d = rsformat.decode(data)
                    V, F = d['V'], d['F']
                    self.assertEqual(len(V), m['vertices'])
                    self.assertEqual(len(F), m['faces'])
                    self.assertLess(len(V), 65536)
                    self.assertLessEqual(len(F), MAX_FACES, 'over the per-model face budget')
                    self.assertTrue((F >= 0).all() and (F < len(V)).all())
                    self.assertEqual(d['texture_count'], 0)
                    self.assertTrue(all(r == 1 for r in d['render_types']))
                    self.assertTrue(all(0 <= c < 65536 for c in d['colors']))
                    t = V[F].astype(float)
                    area = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
                    self.assertTrue((area > 0).all(), 'degenerate face')
                    self.assertEqual(len({tuple(v) for v in V.tolist()}), len(V), 'duplicate vertex')
                    if kind == 'inventory':
                        c = (V.min(0) + V.max(0)) / 2
                        self.assertTrue((np.abs(c) <= 1).all(), 'inventory model not centred: %s' % c)
                    else:
                        lo, hi = m['worn_bounds_min'], m['worn_bounds_max']
                        # RS stores y and z negated
                        self.assertEqual(V[:, 0].min(), lo[0])
                        self.assertEqual(-V[:, 1].max(), lo[1])
                        self.assertEqual(-V[:, 1].min(), hi[1])

    def test_worn_models_fit_player(self):
        """Body-placed items stay inside the standard player volume."""
        for m in self.items:
            if m['worn_placement'] != 'on_body':
                continue
            with self.subTest(code=m['code']):
                lo, hi = m['worn_bounds_min'], m['worn_bounds_max']
                self.assertGreaterEqual(lo[1], -5)
                self.assertLessEqual(hi[1], 260)
                self.assertLessEqual(max(abs(lo[0]), abs(hi[0])), 80)

    def test_sprites(self):
        for m in self.items:
            with self.subTest(code=m['code']):
                with Image.open(os.path.join(OUT, m['files']['sprite'])) as f:
                    im = f.copy()
                self.assertEqual(im.size, (36, 32))
                self.assertEqual(im.mode, 'RGBA')
                a = np.array(im)
                self.assertTrue(set(np.unique(a[..., 3])) <= {0, 255})
                self.assertGreater((a[..., 3] == 255).sum(), 40, 'sprite nearly empty')
                outline = (a[..., 0] == 0) & (a[..., 1] == 0) & (a[..., 2] == 1) & (a[..., 3] == 255)
                self.assertGreater(outline.sum(), 0)

    def test_defs_consistent(self):
        osrs = json.loads(read(os.path.join(OUT, 'defs', 'osrs_item_definitions.json'), 'r'))
        by_id = {m['item_id']: m for m in self.items}
        self.assertEqual(len(osrs), 84)
        for d in osrs:
            m = by_id[d['id']]
            self.assertEqual(d['inventoryModel'], m['inventory_model'])
            self.assertEqual(d['maleModel0'], m['worn_model'])
            self.assertEqual(d['wearPos1'], m['equip_slot'])
            self.assertIn(d['interfaceOptions'][1], ('Wear', 'Wield'))
        java = read(os.path.join(OUT, 'defs', 'ItemDef317_snippet.java'), 'r')
        self.assertEqual(java.count('case '), 84)
        self.assertEqual(java.count('break;'), 84)
        self.assertEqual(java.count('{'), java.count('}'))

    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'needs a JDK')
    def test_runelite_modelloader_agrees(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'verify', 'runelite_check.py')],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('168/168', r.stdout)


if __name__ == '__main__':
    unittest.main()
