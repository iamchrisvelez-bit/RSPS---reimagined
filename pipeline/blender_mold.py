#!/usr/bin/env python3
"""Stage 2 (Blender backend) - mold each design into a 3D model with Blender.

Runs with Blender's Python module (pip install bpy numpy pillow, then run with
that interpreter; see PIPELINE.md). For every stage-1 item:

  1. outline   the cutout's silhouette, traced and simplified (rsgen.lowpoly)
  2. slab      Blender curve fill -> extruded, chamfer-bevelled solid
  3. remesh    voxel remesh so the faces can be shaped
  4. mold      front pushed out (and back pulled in) by the smoothed depth map
  5. facet     Blender's collapse decimation down to the face budget
  6. colour    each face takes the design's flat colour under it (front
               projection), backs slightly darker

Writes pipeline_out/02_models/<code>/model.obj (+ .mtl, meta.json), the same
layout every other stage-2 backend produces, so stage 3 converts it to RS.

  <bpy-python> pipeline/blender_mold.py [--only B14] [--faces 1800]
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))

try:
    import bpy
except ImportError:  # pragma: no cover - explained to the user
    sys.exit('blender_mold.py needs Blender as a Python module: pip install bpy (in its own venv), '
             'then run this script with that interpreter.')

from rsgen.geom import Mesh  # noqa: E402
from rsgen.lowpoly import _components, trace_outline, simplify  # noqa: E402
from rsgen.meshio import write_obj_rgb  # noqa: E402
from stage2_images_to_models import THICKNESS, blur, delit, palette_labels  # noqa: E402


def outlines(mask, eps):
    """Simplified outer outline (x, y-up model coords) of each sizeable blob."""
    h, w = mask.shape
    lab, comps = _components(mask)
    polys = []
    for k, n in comps:
        if n < max(30, mask.sum() * 0.01):
            continue
        ring = simplify(trace_outline(lab == k), eps)
        if len(ring) >= 3:
            polys.append([(x - w / 2, h / 2 - y) for y, x in ring])
    return polys


def new_object(name, data):
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    return o


def evaluated_mesh(obj):
    return bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))


def slab(polys, half_thickness, bevel):
    cu = bpy.data.curves.new('slab', 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    cu.extrude = half_thickness
    cu.bevel_depth = bevel
    cu.bevel_resolution = 0  # a single chamfer: crisp low-poly rim
    for poly in polys:
        sp = cu.splines.new('POLY')
        sp.points.add(len(poly) - 1)
        for p, (x, y) in zip(sp.points, poly):
            p.co = (x, y, 0.0, 1.0)
        sp.use_cyclic_u = True
    return new_object('slab', cu)


def with_modifier(mesh, kind, **props):
    obj = new_object('tmp', mesh)
    mod = obj.modifiers.new('m', kind)
    for k, v in props.items():
        setattr(mod, k, v)
    out = evaluated_mesh(obj)
    bpy.data.objects.remove(obj)
    return out


def mold_item(d, meta, faces=1800, depth_gain=1.0, colors=8, delight=0.75, voxels=70):
    color = Image.open(os.path.join(d, 'color.png'))
    m = np.asarray(Image.open(os.path.join(d, 'mask.png')).convert('L')) > 127
    h, w = m.shape
    size = max(h, w)
    ratio = THICKNESS.get(meta.get('slot'), 0.6)
    half = size * 0.045 * (0.6 + ratio)  # slab half-thickness (pixels)
    polys = outlines(m, eps=max(0.8, size / 160))
    if not polys:
        raise RuntimeError('%s: empty silhouette' % meta['code'])
    bpy.ops.wm.read_factory_settings(use_empty=True)

    base = evaluated_mesh(slab(polys, half, min(half * 0.6, size * 0.02)))
    base = with_modifier(base, 'REMESH', mode='VOXEL', voxel_size=size / voxels)
    # mold: push the front out / back in by the smoothed depth map
    z = blur(np.asarray(Image.open(os.path.join(d, 'depth.png'))).astype(np.float64) / 65535.0, size / 30) * m
    zs = depth_gain * size * 0.2
    for v in base.vertices:
        x, y, zz = v.co
        px = int(np.clip(round(x + w / 2), 0, w - 1))
        py = int(np.clip(round(h / 2 - y), 0, h - 1))
        dz = z[py, px] * zs
        v.co.z = zz + (dz if zz >= 0 else -dz * ratio) * min(1.0, abs(zz) / half + 0.25)
    base.update()
    n0 = len(base.polygons)
    base = with_modifier(base, 'DECIMATE', decimate_type='COLLAPSE', ratio=min(1.0, faces / 2 / max(n0, 1)))
    base = with_modifier(base, 'TRIANGULATE')
    V = np.array([v.co[:] for v in base.vertices])
    F = np.array([p.vertices[:] for p in base.polygons])

    rgb = delit(color, delight)
    L, pal = palette_labels(rgb, m, colors)
    # nearest-inside label for faces whose projection lands just off the cutout
    from collections import deque
    near = L.copy()
    q = deque(map(tuple, np.argwhere(near >= 0)))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and near[ny, nx] < 0:
                near[ny, nx] = near[y, x]
                q.append((ny, nx))
    C = []
    cen = V[F].mean(1)
    nrm = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    for c, n in zip(cen, nrm):
        px = int(np.clip(round(c[0] + w / 2), 0, w - 1))
        py = int(np.clip(round(h / 2 - c[1]), 0, h - 1))
        col = pal[near[py, px]]
        k = 1.0 if n[2] >= 0 else 0.8  # backs a little darker
        C.append(tuple(int(v * k) for v in col))
    return Mesh(V, F, C)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', default=os.path.join(ROOT, 'pipeline_out', '01_views'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'pipeline_out', '02_models'))
    ap.add_argument('--only', default='')
    ap.add_argument('--faces', type=int, default=1800, help='target faces per model')
    ap.add_argument('--depth-gain', type=float, default=1.0)
    ap.add_argument('--colors', type=int, default=8)
    ap.add_argument('--delight', type=float, default=0.75)
    a = ap.parse_args()
    n = 0
    for mj in sorted(glob.glob(os.path.join(a.views, '*', 'meta.json'))):
        d = os.path.dirname(mj)
        with open(mj) as f:
            meta = json.load(f)
        if not meta['code'].startswith(a.only):
            continue
        mesh = mold_item(d, meta, a.faces, a.depth_gain, a.colors, a.delight)
        out = os.path.join(a.out, meta['code'])
        os.makedirs(out, exist_ok=True)
        write_obj_rgb(mesh, os.path.join(out, 'model.obj'), meta['code'])
        with open(os.path.join(out, 'meta.json'), 'w') as f:
            json.dump(dict(meta, backend='blender', blender=bpy.app.version_string, model='model.obj',
                           vertices=len(mesh.V), faces=len(mesh.F)), f, indent=1)
        print('%-6s %-28s blender v=%d f=%d' % (meta['code'], meta['name'], len(mesh.V), len(mesh.F)))
        n += 1
    print('blender mold: %d models -> %s' % (n, a.out))


if __name__ == '__main__':
    main()
