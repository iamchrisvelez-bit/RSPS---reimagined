"""Decode models (any format) through RuneLite's ModelLoader (verify/ModelDump.java)."""
import glob
import json
import os
import subprocess
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VERIFY = os.path.join(ROOT, 'verify')
BUILD = os.path.join(VERIFY, 'build')


def _build():
    if os.path.exists(os.path.join(BUILD, 'ModelDump.class')):
        return
    srcs = glob.glob(os.path.join(VERIFY, 'runelite', '**', '*.java'), recursive=True)
    subprocess.run(['javac', '-nowarn', '-d', BUILD, *srcs, os.path.join(VERIFY, 'ModelDump.java')],
                   check=True, capture_output=True)


def decode_many(models):
    """{model id: bytes} -> {model id: dict(V (n,3) int, F (m,3), col, rtype, prio, alpha, tex, vgroup, animaya)}.
    Coordinates are as stored (RS: y down)."""
    _build()
    out = {}
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for mid, data in models.items():
            p = os.path.join(d, '%d.dat' % mid)
            with open(p, 'wb') as f:
                f.write(data)
            paths.append(p)
        for i in range(0, len(paths), 200):
            res = subprocess.run(['java', '-cp', BUILD, 'ModelDump', *paths[i:i + 200]], check=True,
                                 capture_output=True, text=True)
            for line in res.stdout.splitlines():
                j = json.loads(line)
                m = dict(id=j['id'], V=np.stack([j['x'], j['y'], j['z']], 1).reshape(-1, 3),
                         F=np.stack([j['f1'], j['f2'], j['f3']], 1).reshape(-1, 3), col=j['col'],
                         priority=j['priority'], animaya=j['animaya'])
                for k in ('rtype', 'prio', 'alpha', 'tex', 'vgroup'):
                    m[k] = j.get(k)
                out[j['id']] = m
    return out


def from_cache(cache, ids):
    return decode_many({i: cache.archive(7, i) for i in ids if i >= 0 and cache.archive(7, i) is not None})


def render_icon(model_bytes, item_def):
    """36x32 RGBA inventory icon of a model with an item's icon settings,
    rendered by RuneLite's port of the client's sprite code (IconRender)."""
    from PIL import Image
    _build()
    if not os.path.exists(os.path.join(BUILD, 'IconRender.class')):
        subprocess.run(['javac', '-nowarn', '-cp', BUILD, '-d', BUILD, os.path.join(VERIFY, 'IconRender.java')],
                       check=True, capture_output=True)
    with tempfile.TemporaryDirectory() as t:
        p, o = os.path.join(t, '0.dat'), os.path.join(t, 'i.png')
        with open(p, 'wb') as f:
            f.write(model_bytes)
        args = [str(item_def[k]) for k in ('zoom2d', 'xan2d', 'yan2d', 'zan2d', 'xOffset2d', 'yOffset2d', 'resizeX',
                                           'resizeY', 'resizeZ', 'ambient', 'contrast')]
        subprocess.run(['java', '-cp', BUILD, 'IconRender', p, o, *args], check=True, capture_output=True)
        return Image.open(o).convert('RGBA')


def icon_extent(img):
    """Largest side of the icon's opaque area (pixels)."""
    a = np.asarray(img)[..., 3] > 0
    if not a.any():
        return 0
    ys, xs = np.nonzero(a)
    return max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)
