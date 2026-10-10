"""Meshy backend tests against a local fake API server (no network, no cost)."""
import argparse
import base64
import json
import os
import struct
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
from rsgen.meshy import MeshyClient, MeshyError, image_data_uri  # noqa: E402
import stage2_images_to_models as s2  # noqa: E402

os.environ['no_proxy'] = os.environ['NO_PROXY'] = '127.0.0.1,localhost'


def tiny_glb():
    P = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], np.float32)
    C = np.array([[1, 0, 0, 1]] * 3, np.float32)
    binb = P.tobytes() + C.tobytes()
    js = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0}],
          'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'COLOR_0': 1}}]}],
          'buffers': [{'byteLength': len(binb)}],
          'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': 36},
                          {'buffer': 0, 'byteOffset': 36, 'byteLength': 48}],
          'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3'},
                        {'bufferView': 1, 'componentType': 5126, 'count': 3, 'type': 'VEC4'}]}
    jb = json.dumps(js).encode()
    jb += b' ' * (-len(jb) % 4)
    return (struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(jb) + 8 + len(binb)) +
            struct.pack('<II', len(jb), 0x4E4F534A) + jb + struct.pack('<II', len(binb), 0x004E4942) + binb)


class FakeMeshy(BaseHTTPRequestHandler):
    state = {}

    def log_message(self, *a):
        pass

    def _json(self, code, obj, headers=()):
        body = json.dumps(obj).encode()
        self.send_response(code)
        for k, v in headers:
            self.send_header(k, v)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        st = self.state
        if self.headers.get('Authorization') != 'Bearer test-key':
            return self._json(401, {'message': 'bad key'})
        if st.get('throttle', 0) > 0:
            st['throttle'] -= 1
            return self._json(429, {'message': 'slow down'}, [('Retry-After', '0')])
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        st.setdefault('bodies', []).append(body)
        tid = 'task%d' % len(st['bodies'])
        st.setdefault('polls', {})[tid] = 0
        self._json(202, {'result': tid})

    def do_GET(self):
        st = self.state
        if self.path.startswith('/files/'):
            data = tiny_glb()
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        tid = self.path.rsplit('/', 1)[-1]
        st['polls'][tid] += 1
        if tid in st.get('fail', ()):
            return self._json(200, {'id': tid, 'status': 'FAILED', 'task_error': {'message': 'bad image'}})
        if st['polls'][tid] < 2:
            return self._json(200, {'id': tid, 'status': 'IN_PROGRESS', 'progress': 50, 'task_error': None})
        host = 'http://127.0.0.1:%d' % self.server.server_port
        self._json(200, {'id': tid, 'status': 'SUCCEEDED', 'progress': 100, 'task_error': {'message': ''},
                         'model_urls': {'glb': host + '/files/%s.glb' % tid}})


class TestMeshy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(('127.0.0.1', 0), FakeMeshy)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = 'http://127.0.0.1:%d' % cls.srv.server_port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        FakeMeshy.state = {}
        self.tmp = tempfile.TemporaryDirectory()
        self.views = os.path.join(self.tmp.name, 'views')
        self.items = []
        for code in ('B99_1', 'B99_2', 'B99_3'):
            d = os.path.join(self.views, code)
            os.makedirs(d)
            Image.new('RGBA', (60, 40), (200, 50, 50, 255)).save(os.path.join(d, 'color.png'))
            meta = {'code': code, 'name': code, 'slot': 'shield'}
            with open(os.path.join(d, 'meta.json'), 'w') as f:
                json.dump(meta, f)
            self.items.append((d, meta))

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, key='test-key'):
        return MeshyClient(key, self.base, sleep=lambda s: None)

    def args(self, **kw):
        a = dict(out=os.path.join(self.tmp.name, 'out'), dry_run=False, max_tasks=None, meshy_polycount=2000,
                 meshy_topology='triangle', meshy_model='', meshy_no_texture=False, meshy_poll=0, meshy_timeout=30)
        a.update(kw)
        return argparse.Namespace(**a)

    def test_data_uri_is_padded_png(self):
        uri = image_data_uri(os.path.join(self.items[0][0], 'color.png'))
        self.assertTrue(uri.startswith('data:image/png;base64,'))
        import io
        im = Image.open(io.BytesIO(base64.b64decode(uri.split(',', 1)[1])))
        self.assertEqual(im.size, (512, 512))

    def test_full_run_then_resume_without_new_tasks(self):
        res = s2.run_meshy_all(self.items, self.args(), self.client(), log=lambda *a: None)
        self.assertEqual(len(res), 3)
        self.assertEqual(len(FakeMeshy.state['bodies']), 3)
        body = FakeMeshy.state['bodies'][0]
        self.assertEqual(body['target_polycount'], 2000)
        self.assertTrue(body['image_url'].startswith('data:image/png;base64,'))
        self.assertEqual(res[0][4].C[0], (255, 0, 0))
        for _, _, out, _, _ in res:
            self.assertTrue(os.path.exists(os.path.join(out, 'source.glb')))
            self.assertTrue(os.path.exists(os.path.join(out, 'model.obj')))
        res2 = s2.run_meshy_all(self.items, self.args(), self.client(), log=lambda *a: None)
        self.assertEqual(len(res2), 3)
        self.assertEqual(len(FakeMeshy.state['bodies']), 3, 'resume must not create new paid tasks')

    def test_resume_pending_task_after_interruption(self):
        out = os.path.join(self.tmp.name, 'out', 'B99_1')
        os.makedirs(out)
        c = self.client()
        tid = c.create_image_to_3d('data:image/png;base64,AAAA')
        with open(os.path.join(out, 'meshy_task.json'), 'w') as f:
            json.dump({'task_id': tid}, f)
        s2.run_meshy_all(self.items[:1], self.args(), c, log=lambda *a: None)
        self.assertEqual(len(FakeMeshy.state['bodies']), 1)
        self.assertTrue(os.path.exists(os.path.join(out, 'source.glb')))

    def test_max_tasks_and_dry_run(self):
        self.assertEqual(s2.run_meshy_all(self.items, self.args(dry_run=True), self.client(), log=lambda *a: None), [])
        self.assertNotIn('bodies', FakeMeshy.state)
        res = s2.run_meshy_all(self.items, self.args(max_tasks=1), self.client(), log=lambda *a: None)
        self.assertEqual(len(res), 1)
        self.assertEqual(len(FakeMeshy.state['bodies']), 1)

    def test_retries_on_429(self):
        FakeMeshy.state['throttle'] = 2
        self.assertEqual(self.client().create_image_to_3d('data:,x'), 'task1')

    def test_failed_task_is_reported_not_fatal(self):
        FakeMeshy.state['fail'] = {'task2'}
        logs = []
        res = s2.run_meshy_all(self.items, self.args(), self.client(), log=logs.append)
        self.assertEqual(sorted(r[0] for r in res), ['B99_1', 'B99_3'])
        self.assertTrue(any('B99_2: FAILED' in l and 'bad image' in l for l in logs))

    def test_bad_key_and_missing_key(self):
        with self.assertRaises(MeshyError) as e:
            self.client('wrong').create_image_to_3d('data:,x')
        self.assertIn('API key', str(e.exception))
        with self.assertRaises(MeshyError):
            MeshyClient('', self.base)


if __name__ == '__main__':
    unittest.main()
