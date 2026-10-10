#!/usr/bin/env python3
"""Stage 2 - per-item "3D images" -> 3D models (OBJ/MTL, one colour per face).

Backends:
  lowpoly  (default, runs anywhere) Low-poly triangulation that follows the
           artwork: points dense along the silhouette and colour borders,
           Delaunay triangles each carrying their dominant flat colour, front
           from the depth map, thinner mirrored back. Matches the faceted
           style of the designs within a small face budget.
  relief   (runs anywhere) Builds a closed mesh from the stage-1
           depth map: a front surface, a back surface mirrored and scaled by
           a per-slot thickness, meeting at the silhouette. Face colours come
           from the artwork with its baked lighting partly flattened (the RS
           client lights models itself). Best for flat items (blades, shields,
           amulets, capes); armour comes out as a convincing bas-relief, not
           a full sculpt.
  command  Runs your own image-to-3D tool (an AI model on a GPU box, a
           Blender script, ...). --cmd is a template with {image} {mask}
           {depth} {outdir} {code}; the tool must write a .obj/.ply/.glb into
           {outdir}.
  import   Copies meshes you made elsewhere (online image-to-3D services,
           Blender) from --import-dir/<code>.{glb,obj,ply}.

  python3 pipeline/stage2_images_to_models.py [--views pipeline_out/01_views] [--out pipeline_out/02_models]
"""
import argparse
import glob
import json
import os
import shlex
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from rsgen.geom import Mesh  # noqa: E402
from rsgen.lowpoly import triangulate_art  # noqa: E402
from rsgen.meshio import load_mesh, write_obj_rgb  # noqa: E402

# back-surface depth relative to the front, per slot (flat items stay thin)
THICKNESS = {'weapon': 0.35, 'shield': 0.3, 'neck': 0.35, 'cape': 0.25, 'head': 0.95, 'body': 0.8,
             'legs': 0.8, 'hands': 0.8, 'feet': 0.8}


def palette_labels(rgb, m, k=10, iters=12, smooth=1):
    """k-means the item's colours into k flat tones, then clean speckle with a
    3x3 mode filter. Returns (labels HxW, -1 outside; palette k x 3)."""
    pts = rgb[m]
    L = np.full(m.shape, -1, int)
    if len(pts) == 0:
        return L, np.zeros((0, 3))
    k = max(1, min(k, len(np.unique(pts.astype(int), axis=0))))
    order = np.argsort(pts.mean(1))
    cent = pts[order[np.linspace(0, len(pts) - 1, k).astype(int)]].astype(np.float64)
    for _ in range(iters):
        lab = np.argmin(((pts[:, None, :] - cent[None]) ** 2).sum(-1), 1)
        for j in range(k):
            if (lab == j).any():
                cent[j] = pts[lab == j].mean(0)
    L[m] = np.argmin(((pts[:, None, :] - cent[None]) ** 2).sum(-1), 1)
    for _ in range(smooth):
        P = np.pad(L, 1, constant_values=-1)
        nb = np.stack([P[1 + dy:P.shape[0] - 1 + dy, 1 + dx:P.shape[1] - 1 + dx]
                       for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
        counts = np.stack([(nb == j).sum(0) for j in range(k)])
        L = np.where(m & (counts.max(0) >= 4), counts.argmax(0), L)
    return L, cent


def palette_reduce(rgb, m, k=10):
    L, cent = palette_labels(rgb, m, k)
    out = rgb.copy()
    out[m] = cent[L[m]]
    return out


def blur(a, r):
    """Approximate Gaussian blur of a float array (three box passes per axis)."""
    k = max(1, int(round(r)))
    out = a.astype(np.float64)
    for axis in (0, 1):
        for _ in range(3):
            p = np.pad(out, [(k, k) if i == axis else (0, 0) for i in range(2)], mode='edge')
            c = np.cumsum(p, axis=axis)
            c = np.insert(c, 0, 0, axis=axis)
            n = out.shape[axis]
            hi = np.take(c, np.arange(2 * k + 1, 2 * k + 1 + n), axis=axis)
            lo = np.take(c, np.arange(0, n), axis=axis)
            out = (hi - lo) / (2 * k + 1)
    return out


def delit(color, delight):
    """RGB array with baked shading partly flattened toward a smoothed image."""
    rgb = np.asarray(color.convert('RGB')).astype(np.float64)
    if delight <= 0:
        return rgb
    sm = np.asarray(color.convert('RGB').filter(ImageFilter.GaussianBlur(3))).astype(np.float64)
    lum, slum = rgb.mean(-1, keepdims=True), sm.mean(-1, keepdims=True)
    return np.clip(rgb * ((slum * delight + lum * (1 - delight)) / np.maximum(lum, 1)), 0, 255)


def lowpoly_mesh(color, mask, depth, points=420, thickness=0.6, depth_gain=1.0, delight=0.35, colors=12,
                 seed=0, smooth_div=30.0):
    """Closed low-poly mesh following the artwork: Delaunay triangles placed
    along the silhouette and colour borders, each with its dominant flat
    colour; front from the depth map, mirrored thinner back, sealed at the rim.
    Units: 1 = one source pixel."""
    m = np.asarray(mask.convert('L')) > 127
    h, w = m.shape
    rgb = delit(color, delight)
    L, pal = palette_labels(rgb, m, colors)
    P, T, lab, rim = triangulate_art(m, L, points, max(2.5, max(h, w) / 70), seed)
    # smooth the depth so neighbouring facets tilt coherently (the stage-1 depth
    # carries fine shading relief that would otherwise make every facet flicker)
    z = blur(np.asarray(depth).astype(np.float64) / 65535.0, max(1.5, max(h, w) / smooth_div)) * m
    zs = depth_gain * max(h, w) * 0.22
    V, front, back = [], [], []
    for (y, x), r in zip(P, rim):
        X, Y = x - w / 2, h / 2 - y
        if r:
            front.append(len(V))
            back.append(len(V))
            V.append((X, Y, 0.0))
        else:
            d = z[min(h - 1, int(round(y))), min(w - 1, int(round(x)))] * zs
            front.append(len(V))
            V.append((X, Y, d))
            back.append(len(V))
            V.append((X, Y, -d * thickness))
    F, C = [], []
    for t, li in zip(T, lab):
        col = tuple(int(c) for c in pal[li])
        a, b, c = t
        # T is CCW in image (x, y-down) coordinates, i.e. clockwise once y points up
        F.append((front[a], front[c], front[b]))
        C.append(col)
        F.append((back[a], back[b], back[c]))
        C.append(tuple(int(v * 0.8) for v in col))
    mesh = Mesh(np.array(V, float), F, C)
    keep = [i for i, (p, q, r) in enumerate(mesh.F) if len({p, q, r}) == 3]
    return Mesh(mesh.V, mesh.F[keep], [mesh.C[i] for i in keep])


def relief_mesh(color, mask, depth, cells=56, thickness=0.6, depth_gain=1.0, delight=0.55, colors=10):
    """Closed relief mesh from a cutout + depth map. Units: 1 = one cell."""
    w, h = mask.size
    k = cells / max(w, h)
    gw, gh = max(2, round(w * k)), max(2, round(h * k))
    m = np.asarray(mask.resize((gw, gh), Image.BOX)) > 110
    z = np.asarray(depth.resize((gw, gh), Image.BOX)).astype(np.float64) / 65535.0
    rgb = np.asarray(color.convert('RGB').resize((gw, gh), Image.BOX)).astype(np.float64)
    if delight > 0:  # flatten baked shading: pull each cell's brightness toward a smoothed value
        sm = np.asarray(color.convert('RGB').resize((gw, gh), Image.BOX).filter(ImageFilter.GaussianBlur(2.5)))
        lum, slum = rgb.mean(-1, keepdims=True), sm.astype(np.float64).mean(-1, keepdims=True)
        rgb = np.clip(rgb * ((slum * delight + lum * (1 - delight)) / np.maximum(lum, 1)), 0, 255)
    if colors:
        rgb = palette_reduce(rgb, m, colors)
    zscale = depth_gain * max(gw, gh) * 0.22  # depth map 0..1 -> cells
    # nodes sit on cell corners; a node is on the rim when any neighbouring cell is outside
    inside = np.pad(m, 1)
    nodes_in = inside[:-1, :-1] | inside[1:, :-1] | inside[:-1, 1:] | inside[1:, 1:]
    rim = nodes_in & ~(inside[:-1, :-1] & inside[1:, :-1] & inside[:-1, 1:] & inside[1:, 1:])
    zc = np.pad(z * m, 1)
    nz = (zc[:-1, :-1] + zc[1:, :-1] + zc[:-1, 1:] + zc[1:, 1:]) / np.maximum(
        inside[:-1, :-1].astype(int) + inside[1:, :-1] + inside[:-1, 1:] + inside[1:, 1:], 1)
    V, front, back = [], {}, {}
    for y in range(gh + 1):
        for x in range(gw + 1):
            if not nodes_in[y, x]:
                continue
            X, Y = x - gw / 2, gh / 2 - y
            if rim[y, x]:
                front[(y, x)] = back[(y, x)] = len(V)  # front and back meet at the silhouette
                V.append((X, Y, 0.0))
            else:
                d = nz[y, x] * zscale
                front[(y, x)] = len(V)
                V.append((X, Y, d))
                back[(y, x)] = len(V)
                V.append((X, Y, -d * thickness))
    F, C = [], []
    for y in range(gh):
        for x in range(gw):
            if not m[y, x]:
                continue
            col = tuple(int(c) for c in rgb[y, x])
            a, b, c, d = (y, x), (y, x + 1), (y + 1, x + 1), (y + 1, x)
            fa, fb, fc, fd = front[a], front[b], front[c], front[d]
            F += [(fa, fd, fc), (fa, fc, fb)]  # CCW seen from +z (y up, rows go down)
            C += [col, col]
            ba, bb, bc, bd = back[a], back[b], back[c], back[d]
            dark = tuple(int(v * 0.8) for v in col)
            F += [(ba, bc, bd), (ba, bb, bc)]
            C += [dark, dark]
    mesh = Mesh(np.array(V, float), F, C)
    keep = [i for i, (p, q, r) in enumerate(mesh.F) if len({p, q, r}) == 3]
    return Mesh(mesh.V, mesh.F[keep], [mesh.C[i] for i in keep])


def run_lowpoly(d, out, meta, a):
    color = Image.open(os.path.join(d, 'color.png'))
    mask = Image.open(os.path.join(d, 'mask.png'))
    depth = Image.open(os.path.join(d, 'depth.png'))
    t = a.thickness if a.thickness is not None else THICKNESS.get(meta.get('slot'), 0.6)
    mesh = lowpoly_mesh(color, mask, depth, a.points, t, a.depth_gain, a.delight, a.colors)
    path = os.path.join(out, 'model.obj')
    write_obj_rgb(mesh, path, meta['code'])
    return path, mesh


def run_relief(d, out, meta, a):
    color = Image.open(os.path.join(d, 'color.png'))
    mask = Image.open(os.path.join(d, 'mask.png')).convert('L')
    depth = Image.open(os.path.join(d, 'depth.png'))
    t = a.thickness if a.thickness is not None else THICKNESS.get(meta.get('slot'), 0.6)
    mesh = relief_mesh(color, mask, depth, a.cells, t, a.depth_gain, a.delight, a.colors)
    path = os.path.join(out, 'model.obj')
    write_obj_rgb(mesh, path, meta['code'])
    return path, mesh


def run_command(d, out, meta, a):
    cmd = a.cmd.format(image=shlex.quote(os.path.join(d, 'color.png')), mask=shlex.quote(os.path.join(d, 'mask.png')),
                       depth=shlex.quote(os.path.join(d, 'depth.png')), outdir=shlex.quote(out),
                       code=shlex.quote(meta['code']))
    subprocess.run(cmd, shell=True, check=True)
    found = sorted(glob.glob(os.path.join(out, '**', '*.glb'), recursive=True) +
                   glob.glob(os.path.join(out, '**', '*.obj'), recursive=True) +
                   glob.glob(os.path.join(out, '**', '*.ply'), recursive=True))
    found = [p for p in found if os.path.basename(p) != 'model.obj']
    if not found:
        raise RuntimeError('%s: command wrote no .glb/.obj/.ply into %s' % (meta['code'], out))
    return _normalise(found[0], out, meta)


def run_import(d, out, meta, a):
    for ext in ('.glb', '.obj', '.ply'):
        src = os.path.join(a.import_dir, meta['code'] + ext)
        if os.path.exists(src):
            return _normalise(src, out, meta)
    raise FileNotFoundError('%s: no %s.{glb,obj,ply} in %s' % (meta['code'], meta['code'], a.import_dir))


def _normalise(src, out, meta):
    """Load any supported mesh and re-save as model.obj so stage 3 has one input format."""
    mesh = load_mesh(src)
    path = os.path.join(out, 'model.obj')
    write_obj_rgb(mesh, path, meta['code'])
    shutil.copy(src, os.path.join(out, 'source' + os.path.splitext(src)[1]))
    return path, mesh


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', default=os.path.join(ROOT, 'pipeline_out', '01_views'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'pipeline_out', '02_models'))
    ap.add_argument('--backend', choices=('lowpoly', 'relief', 'command', 'import'), default='lowpoly')
    ap.add_argument('--points', type=int, default=420, help='lowpoly: triangulation points per item')
    ap.add_argument('--only', default='', help='code prefix filter, e.g. B06')
    ap.add_argument('--cells', type=int, default=56, help='relief grid resolution (longest side)')
    ap.add_argument('--thickness', type=float, default=None, help='override back/front depth ratio')
    ap.add_argument('--depth-gain', type=float, default=1.0)
    ap.add_argument('--delight', type=float, default=0.75, help='0 keeps baked shading, 1 flattens it')
    ap.add_argument('--colors', type=int, default=8, help='flat colours per item (0 = keep every cell colour)')
    ap.add_argument('--cmd', help='command template for --backend command')
    ap.add_argument('--import-dir', help='folder of <code>.glb/.obj/.ply for --backend import')
    a = ap.parse_args()
    if a.backend == 'command' and not a.cmd:
        ap.error('--backend command needs --cmd')
    if a.backend == 'import' and not a.import_dir:
        ap.error('--backend import needs --import-dir')

    run = {'lowpoly': run_lowpoly, 'relief': run_relief, 'command': run_command, 'import': run_import}[a.backend]
    n = 0
    for d in sorted(glob.glob(os.path.join(a.views, '*', 'meta.json'))):
        d = os.path.dirname(d)
        with open(os.path.join(d, 'meta.json')) as f:
            meta = json.load(f)
        if not meta['code'].startswith(a.only):
            continue
        out = os.path.join(a.out, meta['code'])
        os.makedirs(out, exist_ok=True)
        path, mesh = run(d, out, meta, a)
        with open(os.path.join(out, 'meta.json'), 'w') as f:
            json.dump(dict(meta, backend=a.backend, model=os.path.basename(path), vertices=len(mesh.V),
                           faces=len(mesh.F)), f, indent=1)
        print('%-6s %-28s %-7s v=%d f=%d' % (meta['code'], meta['name'], a.backend, len(mesh.V), len(mesh.F)))
        n += 1
    print('stage 2: %d models -> %s' % (n, a.out))


if __name__ == '__main__':
    main()
