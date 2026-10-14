"""OSRS cache reader for RuneLite "flatcache" dumps (e.g. github.com/abextm/osrs-cache).

Ported from RuneLite's cache module (FlatStorage, Container, ArchiveFiles).
Only what model checking needs: archive contents by (index, archive), split
into files for multi-file archives (configs).

  cache = FlatCache('/path/to/osrs-cache')      # folder of <index>.flatcache
  cache.file(2, 10, 1127)                         # item 1127's definition bytes
  cache.archive(7, 3820)                          # model 3820's bytes
"""
import base64
import bz2
import gzip
import os
import struct


class FlatCache:
    def __init__(self, root):
        self.root = root
        self._idx = {}

    def _load(self, index):
        if index in self._idx:
            return self._idx[index]
        path = os.path.join(self.root, '%d.flatcache' % index)
        if not os.path.exists(path):
            raise FileNotFoundError('%s (fetch it from the cache dump first)' % path)
        archives, cur = {}, None
        with open(path, encoding='utf-8') as f:
            for line in f:
                key, _, value = line.rstrip('\n').partition('=')
                if key == 'id':
                    cur = archives[int(value)] = {'files': []}
                elif cur is None:
                    continue  # index header (protocol, revision, ...)
                elif key == 'file':
                    fid, _, _ = value.partition('=')
                    cur['files'].append(int(fid))
                elif key == 'contents':
                    cur['raw'] = value  # base64, decoded lazily
        self._idx[index] = archives
        return archives

    def archive_ids(self, index):
        return sorted(self._load(index))

    def archive(self, index, archive):
        """Decompressed archive data (bytes) or None if absent."""
        a = self._load(index).get(archive)
        if a is None or 'raw' not in a:
            return None
        return decompress(base64.b64decode(a['raw']))

    def files(self, index, archive):
        """{file id: bytes} of an archive (one entry for single-file archives)."""
        a = self._load(index).get(archive)
        if a is None:
            return {}
        data = self.archive(index, archive)
        ids = a['files'] or [0]
        return dict(zip(ids, split_files(data, len(ids))))

    def file(self, index, archive, file_id):
        return self.files(index, archive).get(file_id)


def decompress(b):
    """RuneLite Container.decompress (no XTEA: models and configs aren't encrypted)."""
    compression, length = b[0], struct.unpack('>i', b[1:5])[0]
    if compression == 0:
        return bytes(b[5:5 + length])
    size = struct.unpack('>i', b[5:9])[0]
    payload = b[9:9 + length]
    if compression == 1:
        data = bz2.decompress(b'BZh1' + payload)  # the cache strips the bzip2 header
    elif compression == 2:
        data = gzip.decompress(payload)
    else:
        raise ValueError('unknown compression %d' % compression)
    if len(data) != size:
        raise ValueError('decompressed %d bytes, header says %d' % (len(data), size))
    return data


def split_files(data, count):
    """RuneLite ArchiveFiles.loadContents."""
    if count == 1:
        return [data]
    chunks = data[-1]
    off = len(data) - 1 - chunks * count * 4
    sizes = [[0] * chunks for _ in range(count)]
    for c in range(chunks):
        run = 0
        for i in range(count):
            run += struct.unpack('>i', data[off:off + 4])[0]
            off += 4
            sizes[i][c] = run
    out = [bytearray() for _ in range(count)]
    pos = 0
    for c in range(chunks):
        for i in range(count):
            n = sizes[i][c]
            out[i] += data[pos:pos + n]
            pos += n
    return [bytes(x) for x in out]
