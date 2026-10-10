#!/usr/bin/env sh
# Rebuild every asset from source and run all release checks.
# Exit code 0 means the out/ folder is complete, consistent and decodes in
# RuneLite's own ModelLoader. Pass build.py flags through, e.g.
#   ./verify.sh --base-model-id 61000 --base-item-id 31000
set -eu
cd "$(dirname "$0")"
python3 build.py "$@"
python3 -m unittest discover -s tests -v
