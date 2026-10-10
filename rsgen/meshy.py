"""Minimal Meshy image-to-3D API client (standard library only).

API shape (Meshy docs, image-to-3D):
  POST {base}/openapi/v1/image-to-3d        body: {"image_url": <https URL or data URI>, ...options}
       -> {"result": "<task id>"}
  GET  {base}/openapi/v1/image-to-3d/<id>   -> task: {"id", "status", "progress",
       "model_urls": {"glb": ..., "fbx": ..., "obj": ...}, "task_error": null | {"message": ...}}
  status: PENDING | IN_PROGRESS | SUCCEEDED | FAILED | CANCELED (EXPIRED treated as failure)
  auth: "Authorization: Bearer <MESHY_API_KEY>"

The client tolerates small variations ({"id": ...} instead of {"result": ...},
task_error null or {"message": ""}) and retries 429/5xx with backoff.
"""
import base64
import io
import json
import os
import time
import urllib.error
import urllib.request

from PIL import Image

DEFAULT_BASE = 'https://api.meshy.ai'
ENDPOINT = '/openapi/v1/image-to-3d'
DONE_OK = {'SUCCEEDED'}
DONE_BAD = {'FAILED', 'CANCELED', 'CANCELLED', 'EXPIRED'}


class MeshyError(RuntimeError):
    pass


def image_data_uri(path, min_side=512, pad=0.08):
    """PNG data URI of an item cutout: padded, upscaled so the short side is at
    least min_side (image-to-3D models do better on larger inputs), kept RGBA."""
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    side = int(max(w, h) * (1 + 2 * pad))
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    if side < min_side:
        canvas = canvas.resize((min_side, min_side), Image.LANCZOS)
    buf = io.BytesIO()
    canvas.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


class MeshyClient:
    def __init__(self, api_key, base_url=DEFAULT_BASE, timeout=60, retries=5, sleep=time.sleep):
        if not api_key:
            raise MeshyError('no Meshy API key: set MESHY_API_KEY in the environment settings')
        self.key, self.base, self.timeout, self.retries, self.sleep = api_key, base_url.rstrip('/'), timeout, \
            retries, sleep

    def _request(self, method, url, body=None, auth=True, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(url, data=data, method=method)
            if auth:
                req.add_header('Authorization', 'Bearer ' + self.key)
            if data is not None:
                req.add_header('Content-Type', 'application/json')
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    payload = r.read()
                return payload if raw else json.loads(payload or b'{}')
            except urllib.error.HTTPError as e:
                detail = e.read()[:500].decode('utf-8', 'replace')
                if e.code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    wait = float(e.headers.get('Retry-After') or 2 ** (attempt + 1))
                    self.sleep(min(wait, 60))
                    continue
                if e.code in (401, 403):
                    raise MeshyError('Meshy rejected the API key (HTTP %d): %s' % (e.code, detail))
                if e.code == 402:
                    raise MeshyError('Meshy reports insufficient credits (HTTP 402): %s' % detail)
                raise MeshyError('Meshy HTTP %d on %s %s: %s' % (e.code, method, url, detail))
            except urllib.error.URLError as e:
                if attempt < self.retries:
                    self.sleep(2 ** (attempt + 1))
                    continue
                raise MeshyError('cannot reach %s (%s) - is api.meshy.ai in the allowed domains?' % (url, e.reason))
        raise MeshyError('unreachable')

    def create_image_to_3d(self, image_url, **options):
        body = dict(options, image_url=image_url)
        r = self._request('POST', self.base + ENDPOINT, body)
        tid = r.get('result') or r.get('id')
        if not tid:
            raise MeshyError('unexpected create response: %r' % r)
        return tid

    def get_task(self, task_id):
        return self._request('GET', '%s%s/%s' % (self.base, ENDPOINT, task_id))

    def wait(self, task_id, poll=10.0, timeout=3600.0, on_progress=None):
        t0 = time.monotonic()
        while True:
            t = self.get_task(task_id)
            status = (t.get('status') or '').upper()
            if on_progress:
                on_progress(task_id, status, t.get('progress'))
            if status in DONE_OK:
                return t
            if status in DONE_BAD:
                err = t.get('task_error') or {}
                msg = err.get('message') if isinstance(err, dict) else str(err)
                raise MeshyError('task %s %s: %s' % (task_id, status, msg or 'no message'))
            if time.monotonic() - t0 > timeout:
                raise MeshyError('task %s still %s after %ds' % (task_id, status, timeout))
            self.sleep(poll)

    def download(self, url, dest):
        # model URLs are pre-signed; sending our key to a storage host is unnecessary
        data = self._request('GET', url, auth=False, raw=True)
        with open(dest, 'wb') as f:
            f.write(data)
        return dest


def client_from_env(base_url=None):
    return MeshyClient(os.environ.get('MESHY_API_KEY', ''), base_url or os.environ.get('MESHY_BASE_URL', DEFAULT_BASE))
