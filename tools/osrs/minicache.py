"""Write a small flatcache with only what the swap/build/verify tools read.

The full game cache is ~250 MB; building and verifying our models needs a
few hundred of its files: the template items' definitions and models, the
player kits and their models, the player skeleton and the frames of the
checked animations. Those go into the same RuneLite flatcache format, so
FlatCache reads either.

  python3 -m osrs.minicache <full cache> <out dir>        (run from tools/)
"""
import base64
import os
import struct
import sys

from .anim import decode_sequence, kits as load_kits, SEQ_ARCHIVE
from .cache import FlatCache
from .defs import ITEM_ARCHIVE, KIT_ARCHIVE, items


def container(data):
    """Uncompressed container (RuneLite Container: type 0, length, data)."""
    return bytes([0]) + struct.pack('>i', len(data)) + data


def pack_files(files):
    """Multi-file archive body: the files back to back, then one chunk's
    size table (delta-coded) and the chunk count - ArchiveFiles.loadContents."""
    if len(files) == 1:
        return files[0]
    body = b''.join(files)
    table, prev = b'', 0
    for f in files:
        table += struct.pack('>i', len(f) - prev)
        prev = len(f)
    return body + table + bytes([1])


def write_index(path, archives):
    """archives: {archive id: {file id: bytes}} -> <index>.flatcache"""
    lines = ['protocol=7', 'revision=0', 'compression=0', 'crc=0', 'named=false']
    for aid in sorted(archives):
        files = archives[aid]
        ids = sorted(files)
        lines.append('id=%d' % aid)
        lines.append('namehash=0')
        lines.append('revision=0')
        lines.append('crc=0')
        lines.append('contents=' + base64.b64encode(container(pack_files([files[i] for i in ids]))).decode())
        if len(ids) > 1 or ids != [0]:
            lines += ['file=%d=0' % i for i in ids]
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def extract(cache, out, item_ids, sequences=(808, 819, 824, 390)):
    defs = items(cache)
    model_ids = set()
    for i in item_ids:
        d = defs[i]
        for k in ('inventoryModel', 'maleModel0', 'maleModel1', 'maleModel2', 'femaleModel0', 'femaleModel1',
                  'femaleModel2'):
            if d[k] >= 0:
                model_ids.add(d[k])
    kits = load_kits(cache)
    for k in kits.values():
        model_ids.update(k['models'])
    seq_files = {s: cache.file(2, SEQ_ARCHIVE, s) for s in sequences}
    frames = {}
    for s, b in seq_files.items():
        for fid in decode_sequence(b)['frameIDs']:
            frames.setdefault(fid >> 16, {})[fid & 0xFFFF] = cache.file(0, fid >> 16, fid & 0xFFFF)
    framemaps = {int.from_bytes(next(iter(g.values()))[:2], 'big') for g in frames.values()}
    os.makedirs(out, exist_ok=True)
    item_files = cache.files(2, ITEM_ARCHIVE)
    write_index(os.path.join(out, '2.flatcache'), {
        ITEM_ARCHIVE: {i: item_files[i] for i in item_ids},
        KIT_ARCHIVE: cache.files(2, KIT_ARCHIVE),
        SEQ_ARCHIVE: seq_files,
    })
    write_index(os.path.join(out, '7.flatcache'), {m: {0: cache.archive(7, m)} for m in model_ids})
    write_index(os.path.join(out, '1.flatcache'), {f: {0: cache.archive(1, f)} for f in framemaps | {0}})
    # frame groups: keep the group's file ids as in the game (frame ids encode them)
    write_index(os.path.join(out, '0.flatcache'), frames)
    return dict(items=len(item_ids), models=len(model_ids), framemaps=len(framemaps | {0}),
                frame_groups=len(frames))


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from rsgen.swap import TEMPLATES
    full = FlatCache(sys.argv[1])
    d = items(full)
    ids = sorted({next(i for i in sorted(d) if d[i]['name'] == n and d[i]['maleModel0'] >= 0
                       and d[i]['inventoryModel'] >= 0 and d[i]['notedTemplate'] == -1
                       and d[i]['placeholderTemplateId'] == -1) for n in set(TEMPLATES.values())})
    print(extract(full, sys.argv[2], ids))
