"""Read/write generic triangle meshes with per-face colour.

Supported inputs (no third-party deps beyond numpy/Pillow):
  .obj  - v/vt/f, optional per-vertex colours (v x y z r g b), .mtl Kd and
          map_Kd textures (sampled at each face's UV centroid)
  .ply  - ascii or binary_little_endian; vertex/face colours
  .glb  - glTF 2.0 binary: meshes under the default scene with node
          transforms, COLOR_0, baseColorFactor and embedded baseColorTexture

Everything is returned as a geom.Mesh (triangles, one RGB per face).
"""
import io
import json
import os
import struct

import numpy as np
from PIL import Image

from .geom import Mesh


def load_mesh(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.obj':
        return load_obj(path)
    if ext == '.ply':
        return load_ply(path)
    if ext == '.glb':
        return load_glb(path)
    raise ValueError('unsupported mesh format %r (use .obj, .ply or .glb)' % ext)


def _fan(poly):
    return [(poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]


def _sample(img, uv):
    """Sample an RGB image at UV (v up, wrapped)."""
    w, h = img.size
    u, v = uv[0] % 1.0, uv[1] % 1.0
    return img.getpixel((min(w - 1, int(u * w)), min(h - 1, int((1 - v) * h))))[:3]


# --------------------------------------------------------------------- OBJ

def _load_mtl(path):
    mats, cur = {}, None
    base = os.path.dirname(path)
    with open(path, errors='replace') as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            if p[0] == 'newmtl':
                cur = mats.setdefault(' '.join(p[1:]), {'kd': (0.7, 0.7, 0.7), 'tex': None})
            elif cur is not None and p[0] == 'Kd' and len(p) >= 4:
                cur['kd'] = tuple(float(x) for x in p[1:4])
            elif cur is not None and p[0] == 'map_Kd':
                tp = os.path.join(base, p[-1])
                if os.path.exists(tp):
                    cur['tex'] = Image.open(tp).convert('RGB')
    return mats


def load_obj(path):
    V, VC, VT, F, FM, FT = [], [], [], [], [], []
    mats, cur = {}, None
    with open(path, errors='replace') as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            if p[0] == 'v':
                V.append([float(x) for x in p[1:4]])
                VC.append([float(x) for x in p[4:7]] if len(p) >= 7 else None)
            elif p[0] == 'vt':
                VT.append([float(x) for x in p[1:3]])
            elif p[0] == 'f':
                vi, ti = [], []
                for tok in p[1:]:
                    q = tok.split('/')
                    k = int(q[0])
                    vi.append(k - 1 if k > 0 else len(V) + k)
                    if len(q) > 1 and q[1]:
                        t = int(q[1])
                        ti.append(t - 1 if t > 0 else len(VT) + t)
                    else:
                        ti.append(None)
                for (a, b, c), (ta, tb, tc) in zip(_fan(vi), _fan(ti)):
                    F.append((a, b, c))
                    FM.append(cur)
                    FT.append((ta, tb, tc))
            elif p[0] == 'mtllib':
                mp = os.path.join(os.path.dirname(path), ' '.join(p[1:]))
                if os.path.exists(mp):
                    mats.update(_load_mtl(mp))
            elif p[0] == 'usemtl':
                cur = ' '.join(p[1:])
    V = np.array(V, float)
    cols = []
    for (a, b, c), m, t in zip(F, FM, FT):
        mat = mats.get(m)
        if mat and mat['tex'] is not None and None not in t and VT:
            uv = np.mean([VT[t[0]], VT[t[1]], VT[t[2]]], axis=0)
            rgb = _sample(mat['tex'], uv)
            kd = mat['kd']
            cols.append(tuple(int(rgb[i] * min(1.0, kd[i] if any(kd) else 1.0)) for i in range(3)))
        elif VC and VC[a] is not None:
            c3 = np.mean([VC[a], VC[b], VC[c]], axis=0)
            c3 = c3 * 255 if c3.max() <= 1.0 else c3
            cols.append(tuple(int(x) for x in np.clip(c3, 0, 255)))
        elif mat:
            cols.append(tuple(int(x * 255) for x in mat['kd']))
        else:
            cols.append((180, 180, 180))
    return Mesh(V, F, cols)


def write_obj_rgb(mesh, path, name='model', levels=32):
    """OBJ + MTL with one material per (quantised) face colour."""
    q = 256 // levels
    mats, lines = {}, ['# %s' % name, 'mtllib %s' % (os.path.splitext(os.path.basename(path))[0] + '.mtl'),
                       'o %s' % name]
    lines += ['v %.3f %.3f %.3f' % tuple(v) for v in mesh.V]
    cur = None
    for (a, b, c), col in zip(mesh.F, mesh.C):
        key = tuple(min(255, (x // q) * q + q // 2) for x in col)
        if key not in mats:
            mats[key] = 'c_%02x%02x%02x' % key
        if mats[key] != cur:
            cur = mats[key]
            lines.append('usemtl %s' % cur)
        lines.append('f %d %d %d' % (a + 1, b + 1, c + 1))
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    with open(os.path.splitext(path)[0] + '.mtl', 'w') as f:
        for key, n in mats.items():
            f.write('newmtl %s\nKd %.4f %.4f %.4f\nillum 1\n\n' % (n, key[0] / 255, key[1] / 255, key[2] / 255))


# --------------------------------------------------------------------- PLY

_PLY_T = {'char': 'b', 'int8': 'b', 'uchar': 'B', 'uint8': 'B', 'short': 'h', 'int16': 'h', 'ushort': 'H',
          'uint16': 'H', 'int': 'i', 'int32': 'i', 'uint': 'I', 'uint32': 'I', 'float': 'f', 'float32': 'f',
          'double': 'd', 'float64': 'd'}


def load_ply(path):
    with open(path, 'rb') as f:
        if f.readline().strip() != b'ply':
            raise ValueError('not a PLY file')
        fmt, elems = None, []
        while True:
            line = f.readline().decode('ascii', 'replace').strip()
            p = line.split()
            if not p:
                continue
            if p[0] == 'format':
                fmt = p[1]
            elif p[0] == 'element':
                elems.append([p[1], int(p[2]), []])
            elif p[0] == 'property':
                if p[1] == 'list':
                    elems[-1][2].append((p[4], 'list', p[2], p[3]))
                else:
                    elems[-1][2].append((p[2], p[1]))
            elif p[0] == 'end_header':
                break
        if fmt not in ('ascii', 'binary_little_endian'):
            raise ValueError('unsupported PLY format %r' % fmt)
        data = {}
        if fmt == 'ascii':
            toks = f.read().decode('ascii', 'replace').split()
            pos = 0
            for name, n, props in elems:
                rows = []
                for _ in range(n):
                    row = {}
                    for pr in props:
                        if pr[1] == 'list':
                            k = int(toks[pos])
                            row[pr[0]] = [float(x) for x in toks[pos + 1:pos + 1 + k]]
                            pos += 1 + k
                        else:
                            row[pr[0]] = float(toks[pos])
                            pos += 1
                    rows.append(row)
                data[name] = rows
        else:
            buf = f.read()
            pos = 0
            for name, n, props in elems:
                rows = []
                for _ in range(n):
                    row = {}
                    for pr in props:
                        if pr[1] == 'list':
                            ct, it = _PLY_T[pr[2]], _PLY_T[pr[3]]
                            k = struct.unpack_from('<' + ct, buf, pos)[0]
                            pos += struct.calcsize(ct)
                            row[pr[0]] = list(struct.unpack_from('<%d%s' % (k, it), buf, pos))
                            pos += k * struct.calcsize(it)
                        else:
                            t = _PLY_T[pr[1]]
                            row[pr[0]] = struct.unpack_from('<' + t, buf, pos)[0]
                            pos += struct.calcsize(t)
                    rows.append(row)
                data[name] = rows
    verts = data.get('vertex', [])
    V = np.array([[r['x'], r['y'], r['z']] for r in verts], float)
    has_vc = verts and all(k in verts[0] for k in ('red', 'green', 'blue'))
    F, C = [], []
    for r in data.get('face', []):
        idx = [int(x) for x in r.get('vertex_indices', r.get('vertex_index', []))]
        for tri in _fan(idx):
            F.append(tri)
            if all(k in r for k in ('red', 'green', 'blue')):
                C.append((int(r['red']), int(r['green']), int(r['blue'])))
            elif has_vc:
                C.append(tuple(int(np.mean([verts[i][k] for i in tri])) for k in ('red', 'green', 'blue')))
            else:
                C.append((180, 180, 180))
    return Mesh(V, F, C)


# -------------------------------------------------------------------- GLB

_GL_T = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
_GL_N = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def _node_matrix(n):
    if 'matrix' in n:
        return np.array(n['matrix'], float).reshape(4, 4).T
    T = np.eye(4)
    T[:3, 3] = n.get('translation', [0, 0, 0])
    x, y, z, w = n.get('rotation', [0, 0, 0, 1])
    R = np.eye(4)
    R[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                 [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                 [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    S = np.diag(list(n.get('scale', [1, 1, 1])) + [1])
    return T @ R @ S


def load_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    magic, version, _ = struct.unpack_from('<III', data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError('not a glTF 2.0 binary (.glb)')
    pos, js, bin_ = 12, None, b''
    while pos < len(data):
        ln, typ = struct.unpack_from('<II', data, pos)
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == 0x4E4F534A:
            js = json.loads(chunk)
        elif typ == 0x004E4942:
            bin_ = chunk
        pos += 8 + ln

    def accessor(i):
        a = js['accessors'][i]
        bv = js['bufferViews'][a['bufferView']]
        t, n = _GL_T[a['componentType']], _GL_N[a['type']]
        stride = bv.get('byteStride', 0) or struct.calcsize(t) * n
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        out = np.array([struct.unpack_from('<%d%s' % (n, t), bin_, off + k * stride) for k in range(a['count'])],
                       float)
        if a.get('normalized') and t != 'f':
            out /= {'B': 255.0, 'H': 65535.0, 'b': 127.0, 'h': 32767.0}[t]
        return out

    images = {}

    def texture(ti):
        if ti not in images:
            src = js['textures'][ti]['source']
            bv = js['bufferViews'][js['images'][src]['bufferView']]
            raw = bin_[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
            images[ti] = Image.open(io.BytesIO(raw)).convert('RGB')
        return images[ti]

    allV, allF, allC = [], [], []

    def visit(ni, M):
        node = js['nodes'][ni]
        M = M @ _node_matrix(node)
        if 'mesh' in node:
            for prim in js['meshes'][node['mesh']]['primitives']:
                if prim.get('mode', 4) != 4:
                    continue
                P = accessor(prim['attributes']['POSITION'])
                P = (np.c_[P, np.ones(len(P))] @ M.T)[:, :3]
                idx = accessor(prim['indices']).astype(int).ravel() if 'indices' in prim else np.arange(len(P))
                tris = idx.reshape(-1, 3)
                mat = js.get('materials', [{}])[prim['material']] if 'material' in prim else {}
                pbr = mat.get('pbrMetallicRoughness', {})
                factor = np.array(pbr.get('baseColorFactor', [1, 1, 1, 1])[:3])
                tex = pbr.get('baseColorTexture')
                vc = accessor(prim['attributes']['COLOR_0'])[:, :3] if 'COLOR_0' in prim['attributes'] else None
                uv = None
                if tex is not None:
                    uv = accessor(prim['attributes']['TEXCOORD_%d' % tex.get('texCoord', 0)])
                    img = texture(tex['index'])
                base = sum(len(v) for v in allV)
                allV.append(P)
                for a, b, c in tris:
                    if uv is not None:
                        u = uv[[a, b, c]].mean(0)
                        rgb = np.array(_sample(img, (u[0], 1 - u[1]))) / 255.0  # glTF UV origin is top-left
                    elif vc is not None:
                        rgb = vc[[a, b, c]].mean(0)
                    else:
                        rgb = np.ones(3)
                    allC.append(tuple(int(x) for x in np.clip(rgb * factor * 255, 0, 255)))
                    allF.append((a + base, b + base, c + base))
        for ch in node.get('children', []):
            visit(ch, M)

    scene = js['scenes'][js.get('scene', 0)] if 'scenes' in js else {'nodes': range(len(js['nodes']))}
    for ni in scene['nodes']:
        visit(ni, np.eye(4))
    V = np.vstack(allV) if allV else np.zeros((0, 3))
    return Mesh(V, allF, allC)
