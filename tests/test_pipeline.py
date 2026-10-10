"""Tests for the design -> 3D images -> model -> RS pipeline (no sheet needed)."""
import json
import os
import struct
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
from rsgen import rsformat  # noqa: E402
from rsgen.fit import decimate, fit_to_slot, reorient, SLOT_BOX  # noqa: E402
from rsgen.geom import box  # noqa: E402
from rsgen.meshio import load_mesh, write_obj_rgb  # noqa: E402
import stage1_designs_to_3d as s1  # noqa: E402
import stage2_images_to_models as s2  # noqa: E402
import stage3_models_to_rs as s3  # noqa: E402


def synthetic_panel():
    """640x360 dark panel with six simple coloured items in a 3x2 layout."""
    im = Image.new('RGB', (640, 360), (26, 27, 29))
    d = ImageDraw.Draw(im)
    cols = [(200, 60, 40), (60, 120, 200), (220, 190, 70), (90, 160, 80), (180, 180, 190), (150, 60, 160)]
    for k, c in enumerate(cols):
        x, y = 70 + (k % 3) * 200, 50 + (k // 3) * 160
        d.ellipse((x, y, x + 110, y + 90), fill=c)
        d.rectangle((x + 40, y + 20, x + 70, y + 60), fill=tuple(int(v * 0.6) for v in c))
    return im


class TestStage1(unittest.TestCase):
    def test_segments_six_items_in_reading_order(self):
        p = synthetic_panel()
        comps = s1.components(s1.foreground_mask(p), 150)
        items = s1.group_items(comps, 6)
        self.assertEqual(len(items), 6)
        xs = [g[:, 1].mean() for g in items]
        ys = [g[:, 0].mean() for g in items]
        self.assertTrue(xs[0] < xs[1] < xs[2] and xs[3] < xs[4] < xs[5])
        self.assertTrue(max(ys[:3]) < min(ys[3:]))

    def test_split_touching(self):
        m = np.zeros((100, 200), bool)
        m[20:80, 20:90] = True     # two blocks...
        m[20:80, 105:180] = True
        m[46:54, 88:107] = True    # ...joined by a thin bridge
        parts = s1.split_touching(m, 2)
        self.assertGreaterEqual(len(parts), 2)

    def test_depth_peaks_inside(self):
        m = np.zeros((60, 60), bool)
        m[10:50, 10:50] = True
        z = s1.depth_map(Image.new('RGB', (60, 60), (120, 120, 120)), m)
        self.assertEqual(z[0, 0], 0)
        self.assertGreater(z[30, 30], z[12, 30])


class TestMeshIO(unittest.TestCase):
    def test_obj_roundtrip_keeps_colours(self):
        m = box(10, 20, 30, (200, 40, 40))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'b.obj')
            write_obj_rgb(m, p, 'b')
            r = load_mesh(p)
        self.assertEqual(len(r.F), len(m.F))
        self.assertTrue(all(abs(c[0] - 200) <= 8 and c[1] < 60 for c in r.C))

    def test_ply_ascii(self):
        txt = ('ply\nformat ascii 1.0\nelement vertex 4\nproperty float x\nproperty float y\nproperty float z\n'
               'property uchar red\nproperty uchar green\nproperty uchar blue\nelement face 1\n'
               'property list uchar int vertex_indices\nend_header\n'
               '0 0 0 255 0 0\n1 0 0 255 0 0\n1 1 0 255 0 0\n0 1 0 255 0 0\n4 0 1 2 3\n')
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'q.ply')
            open(p, 'w').write(txt)
            m = load_mesh(p)
        self.assertEqual(len(m.F), 2)
        self.assertEqual(m.C[0], (255, 0, 0))

    def test_glb_with_vertex_colours_and_node_transform(self):
        P = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], np.float32)
        Cc = np.array([[0, 1, 0, 1]] * 3, np.float32)
        I = np.array([0, 1, 2], np.uint16)
        binb = P.tobytes() + Cc.tobytes() + I.tobytes() + b'\0\0'
        js = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
              'nodes': [{'mesh': 0, 'translation': [5, 0, 0]}],
              'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'COLOR_0': 1}, 'indices': 2}]}],
              'buffers': [{'byteLength': len(binb)}],
              'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': 36},
                              {'buffer': 0, 'byteOffset': 36, 'byteLength': 48},
                              {'buffer': 0, 'byteOffset': 84, 'byteLength': 6}],
              'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3'},
                            {'bufferView': 1, 'componentType': 5126, 'count': 3, 'type': 'VEC4'},
                            {'bufferView': 2, 'componentType': 5123, 'count': 3, 'type': 'SCALAR'}]}
        jb = json.dumps(js).encode()
        jb += b' ' * (-len(jb) % 4)
        glb = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(jb) + 8 + len(binb))
        glb += struct.pack('<II', len(jb), 0x4E4F534A) + jb + struct.pack('<II', len(binb), 0x004E4942) + binb
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 't.glb')
            open(p, 'wb').write(glb)
            m = load_mesh(p)
        self.assertEqual(len(m.F), 1)
        self.assertEqual(m.C[0], (0, 255, 0))
        self.assertAlmostEqual(m.V[:, 0].min(), 5.0)


class TestFitAndConvert(unittest.TestCase):
    def test_reorient_blender_axes(self):
        m = box(2, 2, 10)  # tall along source z
        r = reorient(m, up='z', forward='-y')
        ext = r.V.max(0) - r.V.min(0)
        self.assertAlmostEqual(ext[1], 10)

    def test_fit_inside_slot_box(self):
        m = fit_to_slot(box(5, 50, 3), 'body')
        lo, hi = (np.array(b) for b in SLOT_BOX['body'])
        self.assertTrue((m.V.min(0) >= lo - 1e-6).all() and (m.V.max(0) <= hi + 1e-6).all())

    def test_decimate_meets_budget(self):
        m = box(40, 40, 40)
        for _ in range(4):
            m = m.subdivide()
        self.assertLessEqual(len(decimate(m, 300).F), 300)

    def test_relief_to_rs_end_to_end(self):
        p = synthetic_panel()
        mask_full = s1.foreground_mask(p)
        item = s1.group_items(s1.components(mask_full, 150), 6)[0]
        y0, x0 = item.min(0)
        y1, x1 = item.max(0) + 1
        m = np.zeros(mask_full.shape, bool)
        m[item[:, 0], item[:, 1]] = True
        m = m[y0:y1, x0:x1]
        rgb = p.crop((x0, y0, x1, y1))
        z = s1.depth_map(rgb, m)
        depth = Image.fromarray((z / max(z.max(), 1) * 65535).astype(np.uint16))
        mesh = s2.relief_mesh(rgb, Image.fromarray((m * 255).astype(np.uint8)), depth, 32, 0.35)
        self.assertGreater(len(mesh.F), 100)
        self.assertGreater(mesh.signed_volume(), 0)  # closed-ish and outward facing
        rs = s3.convert(mesh, 'shield', 500)
        self.assertLessEqual(len(rs.F), 500)
        dec = rsformat.decode(rsformat.encode(rs))
        self.assertTrue(np.array_equal(dec['V'] * np.array([1, -1, -1]), rs.V))
        self.assertTrue(np.array_equal(dec['F'], rs.F))


if __name__ == '__main__':
    unittest.main()
