#!/usr/bin/env python3
"""Quick look at ad-hoc meshes while tuning templates.

  python3 tools/preview.py out.png  (edit the MESHES dict below or import and call show())
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rsgen import rsformat, render  # noqa: E402


def show(meshes, path, views=None, cols=None):
    """meshes: {label: Mesh}. Renders through the real encoder/decoder."""
    tiles = []
    for k, m in meshes.items():
        m = rsformat.clean(m)
        d = rsformat.decode(rsformat.encode(m))
        V = d['V'] * np.array([1, -1, -1])
        v = (views or {}).get(k, {})
        if v.get('roll'):
            a = np.radians(v['roll'])
            R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
            V = V @ R.T
        c = [rsformat.hsl16_to_rgb(h) for h in d['colors']]
        img = render.render(V, d['F'], c, m.G, size=420, yaw=v.get('yaw', -32), pitch=v.get('pitch', 16))
        tiles.append(render.label(img, k, '%d faces' % len(m.F)))
    render.sheet(tiles, cols or min(4, len(tiles)), 420).save(path)
