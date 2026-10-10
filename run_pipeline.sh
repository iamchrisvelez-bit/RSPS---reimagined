#!/usr/bin/env sh
# Design sheet -> 3D images -> 3D models -> RuneScape models, in one go.
# Extra arguments go to stage 2 (e.g. --backend import --import-dir my_glbs/).
set -eu
cd "$(dirname "$0")"
python3 pipeline/stage1_designs_to_3d.py
python3 pipeline/stage2_images_to_models.py "$@"
python3 pipeline/stage3_models_to_rs.py
echo "done: see pipeline_out/03_rs/SHEET.png and report.json"
