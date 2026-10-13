"""Legacy (frame-based) animation, ported from RuneLite's cache module
(FramemapLoader, FrameLoader, ModelDefinition.animate, CircularAngle), plus
player kits and sequences.

The client animates the *merged* player model: body kits and every worn item
are joined into one model first, so a transform's pivot (type 0: the average
of all vertices in its groups) is computed over all of them together. Any
check of whether an item animates correctly has to do the same.
"""
import math

import numpy as np

from .defs import _In

SEQ_ARCHIVE = 12  # index 2
SINE = [int(65536.0 * math.sin(i * math.pi / 1024)) for i in range(2048)]
COSINE = [int(65536.0 * math.cos(i * math.pi / 1024)) for i in range(2048)]


def _jdiv(a, b):
    """Java integer division (truncates toward zero)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def decode_kit(kit_id, b):
    d = dict(id=kit_id, bodyPartId=-1, models=[], nonSelectable=False, recolorToFind=[], recolorToReplace=[])
    s = _In(b)
    while True:
        op = s.u8()
        if op == 0:
            return d
        if op == 1: d['bodyPartId'] = s.u8()
        elif op == 2: d['models'] = [s.u16() for _ in range(s.u8())]
        elif op == 3: d['nonSelectable'] = True
        elif op == 5: d['models'] = [s.i32() for _ in range(s.u8())]
        elif op in (40, 41):
            pairs = [(s.s16(), s.s16()) for _ in range(s.u8())]
            if op == 40:
                d['recolorToFind'] = [p[0] for p in pairs]
                d['recolorToReplace'] = [p[1] for p in pairs]
        elif 60 <= op < 70: s.u16()
        elif 70 <= op < 80: s.i32()
        else:
            raise ValueError('kit %d: unknown opcode %d' % (kit_id, op))


def decode_sequence(b):
    """RuneLite SequenceLoader (rev 226+ opcode layout). Returns a dict with
    frameIDs (index-0 archive << 16 | file), frameLengths, animMayaID and the
    hand-item overrides; frameIDs is empty for skeletal (animaya) sequences."""
    d = dict(frameIDs=[], frameLengths=[], animMayaID=-1, leftHandItem=-1, rightHandItem=-1, verticalOffset=0)
    s = _In(b)
    while True:
        op = s.u8()
        if op == 0:
            return d
        if op == 1:
            n = s.u16()
            d['frameLengths'] = [s.u16() for _ in range(n)]
            lo = [s.u16() for _ in range(n)]
            d['frameIDs'] = [l + (s.u16() << 16) for l in lo]
        elif op == 2: d['frameStep'] = s.u16()
        elif op == 3: [s.u8() for _ in range(s.u8())]
        elif op == 4: d['stretches'] = True
        elif op == 5: d['forcedPriority'] = s.u8()
        elif op == 6: d['leftHandItem'] = s.u16()
        elif op == 7: d['rightHandItem'] = s.u16()
        elif op in (8, 9, 10, 11): s.u8()
        elif op == 12:
            n = s.u8()
            [s.u16() for _ in range(2 * n)]
        elif op == 13: d['animMayaID'] = s.i32()
        elif op == 14:
            for _ in range(s.u16()):
                s.u16(); s.u16(); s.u8(); s.u8(); s.u8(); s.u8()  # frame, sound id, weight, loops, location, retain
        elif op == 15: s.u16(); s.u16()
        elif op == 16: d['verticalOffset'] = s.s8()
        elif op == 17: [s.u8() for _ in range(s.u8())]
        elif op == 18: d['debugName'] = s.string()
        elif op == 19: pass
        else:
            raise ValueError('sequence: unknown opcode %d' % op)


def sequence_frames(b):
    return decode_sequence(b)['frameIDs'] if b else []


def decode_framemap(b):
    s = _In(b)
    n = s.u8()
    types = [s.u8() for _ in range(n)]
    sizes = [s.u8() for _ in range(n)]
    maps = [[s.u8() for _ in range(k)] for k in sizes]
    return dict(types=types, maps=maps)


def _short_smart(s):
    return s.u8() - 64 if s.b[s.o] < 128 else s.u16() - 0xC000


def decode_frame(framemap, b):
    """RuneLite FrameLoader.load -> list of (framemap index, dx, dy, dz)."""
    head = _In(b)
    head.u16()  # framemap archive
    length = head.u8()
    data = _In(b)
    data.o = 3 + length
    types = framemap['types']
    out, last = [], -1
    for i in range(length):
        flags = head.u8()
        if flags <= 0:
            continue
        if types[i] != 0:
            for j in range(i - 1, last, -1):
                if types[j] == 0:
                    out.append([j, 0, 0, 0])
                    break
        default = 128 if types[i] == 3 else 0
        t = [i]
        for bit in (1, 2, 4):
            t.append(_short_smart(data) if flags & bit else default)
        out.append(t)
        last = i
    if data.o != len(b):
        raise ValueError('frame data length mismatch')
    return out


class Animator:
    """Applies frames to one (merged) model: vertices (n, 3) int in RS
    coordinates and a vertex-group label per vertex."""

    def __init__(self, V, labels):
        self.V0 = np.asarray(V, dtype=np.int64).copy()
        lab = np.asarray(labels, int)
        self.groups = [np.where(lab == g)[0] for g in range(int(lab.max()) + 1 if len(lab) else 0)]

    def pose(self, framemap, frame, pivots=None, record=None):
        """Posed vertices. record: a list that receives every type-0 pivot;
        pivots: replay such a list instead of computing them (to pose a model
        with exactly another model's rotation centres)."""
        V = self.V0.copy()
        ox = oy = oz = 0
        k = 0
        for idx, dx, dy, dz in frame:
            ty, gl = framemap['types'][idx], framemap['maps'][idx]
            verts = [self.groups[g] for g in gl if g < len(self.groups)]
            verts = np.concatenate(verts) if verts else np.zeros(0, int)
            if ty == 0 and pivots is not None:
                ox, oy, oz = pivots[k]
                k += 1
            elif ty == 0:
                if len(verts):
                    s = V[verts].sum(0)
                    n = len(verts)
                    ox, oy, oz = dx + _jdiv(int(s[0]), n), dy + _jdiv(int(s[1]), n), dz + _jdiv(int(s[2]), n)
                else:
                    ox, oy, oz = dx, dy, dz
                if record is not None:
                    record.append((ox, oy, oz))
            elif ty == 1:
                V[verts] += (dx, dy, dz)
            elif ty == 2:
                rx, ry, rz = (dx & 255) * 8, (dy & 255) * 8, (dz & 255) * 8
                for v in verts:
                    x, y, z = int(V[v, 0]) - ox, int(V[v, 1]) - oy, int(V[v, 2]) - oz
                    if rz:
                        sn, cs = SINE[rz], COSINE[rz]
                        x, y = (sn * y + cs * x) >> 16, (cs * y - sn * x) >> 16
                    if rx:
                        sn, cs = SINE[rx], COSINE[rx]
                        y, z = (cs * y - sn * z) >> 16, (sn * y + cs * z) >> 16
                    if ry:
                        sn, cs = SINE[ry], COSINE[ry]
                        x, z = (sn * z + cs * x) >> 16, (cs * z - sn * x) >> 16
                    V[v] = (x + ox, y + oy, z + oz)
            elif ty == 3:
                for v in verts:
                    x, y, z = int(V[v, 0]) - ox, int(V[v, 1]) - oy, int(V[v, 2]) - oz
                    V[v] = (_jdiv(dx * x, 128) + ox, _jdiv(dy * y, 128) + oy, _jdiv(dz * z, 128) + oz)
            # type 5: alpha animation, no movement
        return V


def load_sequence(cache, seq_id):
    """[(framemap, frame transforms)] for a legacy sequence."""
    ids = sequence_frames(cache.file(2, SEQ_ARCHIVE, seq_id) or b'')
    out, maps = [], {}
    for fid in ids:
        group, file_id = fid >> 16, fid & 0xFFFF
        b = cache.file(0, group, file_id)
        if b is None:
            continue
        fm_id = int.from_bytes(b[:2], 'big')
        if fm_id not in maps:
            maps[fm_id] = decode_framemap(cache.archive(1, fm_id))
        out.append((maps[fm_id], decode_frame(maps[fm_id], b)))
    return out


def default_body(kits, female=False):
    """The default player body: lowest selectable kit per body part
    (body parts 0..6 male, 7..13 female). {body part 0..6: kit}."""
    base = 7 if female else 0
    out = {}
    for k in sorted(kits):
        d = kits[k]
        bp = d['bodyPartId'] - base
        if 0 <= bp <= 6 and not d['nonSelectable'] and bp not in out and d['models']:
            out[bp] = d
    return out


def kits(cache):
    return {i: decode_kit(i, b) for i, b in cache.files(2, 3).items()}
