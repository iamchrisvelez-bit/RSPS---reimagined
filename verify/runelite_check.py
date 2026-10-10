#!/usr/bin/env python3
"""Decode every out/models/*.dat with RuneLite's own ModelLoader (Java) and
compare the result against rsgen's decoder, field by field.

  python3 verify/runelite_check.py [models_dir]   -> exit 0 when every model matches

models_dir defaults to out/models; folders are searched recursively for
<id>.dat (e.g. pipeline_out/03_rs).
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from rsgen import rsformat  # noqa: E402


def java_dump(models_dir):
    build = os.path.join(HERE, 'build')
    srcs = glob.glob(os.path.join(HERE, 'runelite', '**', '*.java'), recursive=True)
    subprocess.run(['javac', '-nowarn', '-d', build, *srcs, os.path.join(HERE, 'VerifyModels.java')],
                   check=True, capture_output=True)
    out = subprocess.run(['java', '-cp', build, 'VerifyModels', models_dir], check=True,
                         capture_output=True, text=True).stdout
    models, cur = {}, None
    for line in out.splitlines():
        p = line.split()
        if p[0] == 'M':
            cur = models[int(p[1])] = dict(nv=int(p[2]), nf=int(p[3]), V=[], F=[])
        elif p[0] == 'v':
            cur['V'].append(tuple(map(int, p[1:4])))
        elif p[0] == 'f':
            cur['F'].append(tuple(map(int, p[1:7])))
    return models


def main():
    models_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'out', 'models')
    files = sorted(glob.glob(os.path.join(models_dir, '**', '*.dat'), recursive=True))
    java = {}
    for d in sorted({os.path.dirname(f) for f in files}):
        java.update(java_dump(d))
    bad = 0
    for path in files:
        mid = int(os.path.basename(path)[:-4])
        with open(path, 'rb') as f:
            d = rsformat.decode(f.read())
        j = java.get(mid)
        ok = (j is not None and j['nv'] == len(d['V']) and j['nf'] == len(d['F'])
              and j['V'] == [tuple(v) for v in d['V'].tolist()]
              and j['F'] == [(a, b, c, col, rt, -1) for (a, b, c), col, rt in
                             zip(d['F'].tolist(), d['colors'], d['render_types'])])
        if not ok:
            bad += 1
            print('MISMATCH model', mid)
    print('RuneLite ModelLoader check: %d/%d models identical' % (len(files) - bad, len(files)))
    return 1 if bad or not files else 0


if __name__ == '__main__':
    sys.exit(main())
