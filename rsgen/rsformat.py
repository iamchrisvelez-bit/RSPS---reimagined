"""RuneScape model encoder/decoder (the classic "old" format).

This is the format of 317-era model files, and OSRS clients still decode it
(ModelLoader.decodeOldFormat in RuneLite's cache library), so the same .dat
loads on both 317 and OSRS-revision servers. Layout and smart-number rules
follow RuneLite's ModelLoader.

Axis convention: RS uses y down and z away from the camera, so authoring
coordinates (y up, z toward viewer) are written as (x, -y, -z), a proper
rotation that keeps CCW-outward winding (same mapping RuneLite's OBJ
exporter inverts).
"""
import struct
import numpy as np

BRIGHTNESS = 0.8  # client default-ish brightness used for palette preview


def _build_palette(brightness=BRIGHTNESS):
    pal = np.zeros((65536, 3), dtype=np.uint8)
    j = 0
    for k in range(512):
        h = (k // 8) / 64.0 + 0.0078125
        s = (k & 7) / 8.0 + 0.0625
        for k1 in range(128):
            l = k1 / 128.0
            r = g = b = l
            if s != 0:
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                rgb = []
                for t in (h + 1 / 3, h, h - 1 / 3):
                    t = t - 1 if t > 1 else (t + 1 if t < 0 else t)
                    if 6 * t < 1:
                        v = p + (q - p) * 6 * t
                    elif 2 * t < 1:
                        v = q
                    elif 3 * t < 2:
                        v = p + (q - p) * (2 / 3 - t) * 6
                    else:
                        v = p
                    rgb.append(v)
                r, g, b = rgb
            col = [int(c * 256) for c in (r, g, b)]
            col = [min(255, int((c / 256.0) ** brightness * 256)) for c in col]
            pal[j] = col
            j += 1
    return pal


_PAL = None


def palette():
    global _PAL
    if _PAL is None:
        _PAL = _build_palette()
    return _PAL


def rgb_to_hsl16(rgbs):
    """Nearest RS HSL16 colour for each RGB (searched against the client palette)."""
    pal = palette().astype(np.int32)
    out = []
    cache = {}
    for c in rgbs:
        c = tuple(int(x) for x in c)
        if c not in cache:
            d = pal - np.array(c, np.int32)
            # weight luminance error a bit more than chroma, like the eye
            dist = (d[:, 0] * 3) ** 2 + (d[:, 1] * 4) ** 2 + (d[:, 2] * 2) ** 2
            cache[c] = int(np.argmin(dist))
        out.append(cache[c])
    return out


def hsl16_to_rgb(h):
    return tuple(int(x) for x in palette()[h])


def _smart(v):
    if -64 <= v < 64:
        return bytes([v + 64])
    if -16384 <= v < 16384:
        return struct.pack('>H', v + 0xC000)
    raise ValueError('delta out of range for smart encoding: %d' % v)


def clean(mesh):
    """Snap vertices to the integer grid the format stores, weld duplicates,
    and drop triangles that become degenerate (repeated vertex or zero area)
    plus vertices no face uses. Returns a new Mesh; colours/glow follow faces."""
    from .geom import Mesh
    R = np.rint(mesh.V).astype(int)
    keymap, newV, remap = {}, [], np.zeros(len(R), int)
    for i, v in enumerate(map(tuple, R)):
        if v not in keymap:
            keymap[v] = len(newV)
            newV.append(v)
        remap[i] = keymap[v]
    F, C, G = [], [], []
    Vn = np.array(newV, float)
    for (a, b, c), col, g in zip(remap[mesh.F], mesh.C, mesh.G):
        if a == b or b == c or a == c:
            continue
        if np.linalg.norm(np.cross(Vn[b] - Vn[a], Vn[c] - Vn[a])) == 0:
            continue
        F.append((a, b, c))
        C.append(col)
        G.append(g)
    used = sorted({i for f in F for i in f})
    idx = {o: n for n, o in enumerate(used)}
    return Mesh(Vn[used], [(idx[a], idx[b], idx[c]) for a, b, c in F], C, G)


def encode(mesh, priority=10):
    """Encode a cleaned mesh (see clean()); vertices must already be integers."""
    if not np.array_equal(mesh.V, np.rint(mesh.V)):
        raise ValueError('mesh has non-integer vertices; run clean() first')
    if not 0 <= priority <= 254:
        raise ValueError('priority must be 0..254 (255 means per-face)')
    V = np.rint(mesh.V * np.array([1, -1, -1])).astype(int)
    if len(mesh.F) and (mesh.F.min() < 0 or mesh.F.max() >= len(V)):
        raise ValueError('face index out of range')
    F = mesh.F
    nv, nf = len(V), len(F)
    if nv > 65535 or nf > 65535:
        raise ValueError('model too large')
    colors = rgb_to_hsl16(mesh.C)

    vflags, xs, ys, zs = bytearray(), bytearray(), bytearray(), bytearray()
    prev = np.zeros(3, int)
    for v in V:
        d = v - prev
        f = 0
        if d[0]:
            f |= 1
            xs += _smart(int(d[0]))
        if d[1]:
            f |= 2
            ys += _smart(int(d[1]))
        if d[2]:
            f |= 4
            zs += _smart(int(d[2]))
        vflags.append(f)
        prev = v

    ctypes, fdata = bytearray(), bytearray()
    last = 0
    for a, b, c in F:
        ctypes.append(1)
        fdata += _smart(int(a) - last) + _smart(int(b) - int(a)) + _smart(int(c) - int(b))
        last = int(c)

    for name, sec in (('x', xs), ('y', ys), ('z', zs), ('face index', fdata)):
        if len(sec) > 65535:  # the footer stores each section length as an unsigned 16-bit value
            raise ValueError('model too large: %s data is %d bytes (format limit 65535)' % (name, len(sec)))

    render_types = bytes([1]) * nf  # flat shading -> faceted low-poly look
    col = b''.join(struct.pack('>H', c) for c in colors)

    body = vflags + ctypes + render_types + fdata + col + xs + ys + zs
    footer = struct.pack('>HHBBBBBBHHHH', nv, nf, 0,
                         1,          # per-face render types present
                         priority,   # single priority for every face
                         0, 0, 0,    # no alpha, no face/vertex skins
                         len(xs), len(ys), len(zs), len(fdata))
    return bytes(body + footer)


class _R:
    def __init__(self, data, off):
        self.d, self.o = data, off

    def u8(self):
        v = self.d[self.o]
        self.o += 1
        return v

    def u16(self):
        v = struct.unpack_from('>H', self.d, self.o)[0]
        self.o += 2
        return v

    def smart(self):
        return self.u8() - 64 if self.d[self.o] < 128 else self.u16() - 0xC000


def decode(data):
    """Port of RuneLite ModelLoader.decodeOldFormat (no textures/skins)."""
    f = _R(data, len(data) - 18)
    nv, nf, ntex = f.u16(), f.u16(), f.u8()
    textured, prio, alpha, tskin, vskin = f.u8(), f.u8(), f.u8(), f.u8(), f.u8()
    xl, yl, zl, fl = f.u16(), f.u16(), f.u16(), f.u16()
    o = nv
    o_ctype = o; o += nf
    o_prio = o
    if prio == 255: o += nf
    o_tskin = o
    if tskin == 1: o += nf
    o_rtype = o
    if textured == 1: o += nf
    o_vskin = o
    if vskin == 1: o += nv
    o_alpha = o
    if alpha == 1: o += nf
    o_fidx = o; o += fl
    o_col = o; o += nf * 2
    o += ntex * 6
    o_x = o; o += xl
    o_y = o; o += yl
    o_z = o; o += zl
    assert o == len(data) - 18, 'section lengths do not add up'

    fl_, sx, sy, sz = _R(data, 0), _R(data, o_x), _R(data, o_y), _R(data, o_z)
    V = []
    p = [0, 0, 0]
    for _ in range(nv):
        fg = fl_.u8()
        p = [p[0] + (sx.smart() if fg & 1 else 0), p[1] + (sy.smart() if fg & 2 else 0),
             p[2] + (sz.smart() if fg & 4 else 0)]
        V.append(p)
    cs, rt = _R(data, o_col), _R(data, o_rtype)
    cols = [cs.u16() for _ in range(nf)]
    rtypes = [rt.u8() for _ in range(nf)] if textured == 1 else [0] * nf
    pr = _R(data, o_prio)
    prios = [pr.u8() for _ in range(nf)] if prio == 255 else [prio] * nf
    al = _R(data, o_alpha)
    alphas = [al.u8() for _ in range(nf)] if alpha == 1 else [0] * nf
    ts = _R(data, o_tskin)
    tskins = [ts.u8() for _ in range(nf)] if tskin == 1 else None
    vs = _R(data, o_vskin)
    vskins = [vs.u8() for _ in range(nv)] if vskin == 1 else None
    fi, ct = _R(data, o_fidx), _R(data, o_ctype)
    a = b = c = 0
    F = []
    for _ in range(nf):
        t = ct.u8()
        if t == 1:
            a = fi.smart() + c
            b = fi.smart() + a
            c = fi.smart() + b
        elif t == 2:
            b = c
            c = fi.smart() + c
        elif t == 3:
            a = c
            c = fi.smart() + c
        elif t == 4:
            a, b = b, a
            c = fi.smart() + c
        F.append((a, b, c))
    return {'V': np.array(V, int).reshape(-1, 3), 'F': np.array(F, int).reshape(-1, 3), 'colors': cols,
            'render_types': rtypes, 'priorities': prios, 'alphas': alphas, 'face_skins': tskins,
            'vertex_skins': vskins, 'texture_count': ntex}


def write_obj(mesh, path_obj, name):
    """OBJ + MTL in authoring space (y up), colours already snapped to RS palette."""
    hsl = rgb_to_hsl16(mesh.C)
    mats = {}
    with open(path_obj, 'w') as o:
        o.write('# %s\nmtllib %s.mtl\no %s\n' % (name, name, name))
        for v in mesh.V:
            o.write('v %.2f %.2f %.2f\n' % tuple(v))
        cur = None
        for (a, b, c), h in zip(mesh.F, hsl):
            if h != cur:
                mats.setdefault(h, 'hsl_%d' % h)
                o.write('usemtl %s\n' % mats[h])
                cur = h
            o.write('f %d %d %d\n' % (a + 1, b + 1, c + 1))
    with open(path_obj[:-4] + '.mtl', 'w') as m:
        for h, n in mats.items():
            r, g, b = hsl16_to_rgb(h)
            m.write('newmtl %s\nKd %.4f %.4f %.4f\nillum 1\n\n' % (n, r / 255, g / 255, b / 255))
