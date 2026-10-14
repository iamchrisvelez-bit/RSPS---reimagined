"""Item and kit definition decoders, ported from RuneLite's ItemLoader and
KitLoader (cache module, rev 241). Fields keep RuneLite's names."""
import struct

ITEM_ARCHIVE, KIT_ARCHIVE = 10, 3  # index 2 (configs)

_CP1252 = ('€\x00‚ƒ„…†‡ˆ‰Š‹Œ\x00Ž\x00'
           '\x00‘’“”•–—˜™š›œ\x00žŸ')


class _In:
    def __init__(self, b):
        self.b, self.o = b, 0

    def u8(self):
        self.o += 1
        return self.b[self.o - 1]

    def s8(self):
        v = self.u8()
        return v - 256 if v > 127 else v

    def u16(self):
        self.o += 2
        return struct.unpack('>H', self.b[self.o - 2:self.o])[0]

    def s16(self):
        self.o += 2
        return struct.unpack('>h', self.b[self.o - 2:self.o])[0]

    def u24(self):
        self.o += 3
        return int.from_bytes(self.b[self.o - 3:self.o], 'big')

    def i32(self):
        self.o += 4
        return struct.unpack('>i', self.b[self.o - 4:self.o])[0]

    def i64(self):
        self.o += 8
        return struct.unpack('>q', self.b[self.o - 8:self.o])[0]

    def string(self):
        out = []
        while True:
            c = self.u8()
            if c == 0:
                return ''.join(out)
            if 128 <= c < 160:
                ch = _CP1252[c - 128]
                out.append(ch if ch != '\x00' else '?')
            else:
                out.append(chr(c))

    def params(self):
        out = {}
        for _ in range(self.u8()):
            kind = self.u8()
            pid = self.u24()
            out[pid] = self.string() if kind == 1 else self.i64() if kind == 2 else self.i32()
        return out


def decode_item(item_id, b):
    d = dict(id=item_id, name='null', inventoryModel=-1, zoom2d=2000, xan2d=0, yan2d=0, zan2d=0, xOffset2d=0,
             yOffset2d=0, maleModel0=-1, maleModel1=-1, maleModel2=-1, maleOffset=0, femaleModel0=-1,
             femaleModel1=-1, femaleModel2=-1, femaleOffset=0, maleHeadModel=-1, maleHeadModel2=-1,
             femaleHeadModel=-1, femaleHeadModel2=-1, wearPos1=-1, wearPos2=-1, wearPos3=-1, colorFind=[],
             colorReplace=[], textureFind=[], textureReplace=[], notedTemplate=-1, placeholderTemplateId=-1,
             boughtTemplateId=-1, resizeX=128, resizeY=128, resizeZ=128, ambient=0, contrast=0, params={},
             interfaceOptions=[None] * 5, groundOps=[None] * 5)
    s = _In(b)
    while True:
        op = s.u8()
        if op == 0:
            return d
        if op == 1: d['inventoryModel'] = s.u16()
        elif op == 2: d['name'] = s.string()
        elif op == 3: d['examine'] = s.string()
        elif op == 4: d['zoom2d'] = s.u16()
        elif op == 5: d['xan2d'] = s.u16()
        elif op == 6: d['yan2d'] = s.u16()
        elif op == 7: d['xOffset2d'] = s.s16()
        elif op == 8: d['yOffset2d'] = s.s16()
        elif op == 9: d['unknown1'] = s.string()
        elif op == 11: d['stackable'] = 1
        elif op == 12: d['cost'] = s.i32()
        elif op == 13: d['wearPos1'] = s.s8()
        elif op == 14: d['wearPos2'] = s.s8()
        elif op == 15: d['tradeable'] = False
        elif op == 16: d['members'] = True
        elif op == 23: d['maleModel0'] = s.u16(); d['maleOffset'] = s.u8()
        elif op == 24: d['maleModel1'] = s.u16()
        elif op == 25: d['femaleModel0'] = s.u16(); d['femaleOffset'] = s.u8()
        elif op == 26: d['femaleModel1'] = s.u16()
        elif op == 27: d['wearPos3'] = s.s8()
        elif 30 <= op < 35:
            t = s.string()
            d['groundOps'][op - 30] = None if t.lower() == 'hidden' else t
        elif 35 <= op < 40: d['interfaceOptions'][op - 35] = s.string()
        elif op in (40, 41):
            n = s.u8()
            pairs = [(s.u16(), s.u16()) for _ in range(n)]
            key = 'color' if op == 40 else 'texture'
            d[key + 'Find'] = [p[0] for p in pairs]
            d[key + 'Replace'] = [p[1] for p in pairs]
        elif op == 42: d['shiftClickDropIndex'] = s.s8()
        elif op == 43:
            s.u8()
            while s.u8() - 1 != -1:
                s.string()
        elif op == 44: d['inventoryModel'] = s.i32()
        elif op == 45: d['maleModel0'] = s.i32(); d['maleOffset'] = s.u8()
        elif op == 46: d['maleModel1'] = s.i32()
        elif op == 47: d['maleModel2'] = s.i32()
        elif op == 48: d['femaleModel0'] = s.i32(); d['femaleOffset'] = s.u8()
        elif op == 49: d['femaleModel1'] = s.i32()
        elif op == 50: d['femaleModel2'] = s.i32()
        elif op == 51: d['maleHeadModel'] = s.i32()
        elif op == 52: d['maleHeadModel2'] = s.i32()
        elif op == 53: d['femaleHeadModel'] = s.i32()
        elif op == 54: d['femaleHeadModel2'] = s.i32()
        elif op == 65: d['geTradeable'] = True
        elif op == 75: d['weight'] = s.s16()
        elif op == 78: d['maleModel2'] = s.u16()
        elif op == 79: d['femaleModel2'] = s.u16()
        elif op == 90: d['maleHeadModel'] = s.u16()
        elif op == 91: d['femaleHeadModel'] = s.u16()
        elif op == 92: d['maleHeadModel2'] = s.u16()
        elif op == 93: d['femaleHeadModel2'] = s.u16()
        elif op == 94: d['category'] = s.u16()
        elif op == 95: d['zan2d'] = s.u16()
        elif op == 97: d['notedID'] = s.u16()
        elif op == 98: d['notedTemplate'] = s.u16()
        elif op == 99: d['fullRecolor'] = s.u16()
        elif 100 <= op < 110: s.u16(); s.u16()
        elif op == 110: d['resizeX'] = s.u16()
        elif op == 111: d['resizeY'] = s.u16()
        elif op == 112: d['resizeZ'] = s.u16()
        elif op == 113: d['ambient'] = s.s8()
        elif op == 114: d['contrast'] = s.s8()
        elif op == 115: d['team'] = s.u8()
        elif op == 139: d['boughtId'] = s.u16()
        elif op == 140: d['boughtTemplateId'] = s.u16()
        elif op == 148: d['placeholderId'] = s.u16()
        elif op == 149: d['placeholderTemplateId'] = s.u16()
        elif op == 160: d['stackable'] = 2
        elif op == 161: [s.u16() for _ in range(s.u16())]
        elif op == 200: s.u8(); s.u8(); s.string()
        elif op == 201: s.u8(); s.u16(); s.u16(); s.i32(); s.i32(); s.string()
        elif op == 202: s.u8(); s.u16(); s.u16(); s.u16(); s.i32(); s.i32(); s.string()
        elif op == 249: d['params'] = s.params()
        elif op == 251: d['bronzeman'] = True
        else:
            raise ValueError('item %d: unknown opcode %d at %d' % (item_id, op, s.o - 1))


def items(cache):
    """{item id: definition} for every item in the cache."""
    return {i: decode_item(i, b) for i, b in cache.files(2, ITEM_ARCHIVE).items()}
