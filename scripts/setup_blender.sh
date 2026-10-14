#!/usr/bin/env sh
# Install Blender as a Python module (bpy from PyPI) in its own venv, for
# pipeline/blender_mold.py and any Blender Python build scripts.
#   ./scripts/setup_blender.sh [venv-dir]      (default: .venv-blender)
set -eu
V="${1:-.venv-blender}"
python3 -m venv "$V"
"$V/bin/pip" install -q bpy numpy pillow
"$V/bin/python" -c "import bpy; print('Blender', bpy.app.version_string, 'ready at $V/bin/python')"
