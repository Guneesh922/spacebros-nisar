#!/usr/bin/env bash
# Emulate update.yml + pages.yml locally, in a scratch copy (no GitHub, no docker, no push). See tools/sim/emulate_workflow.py.
#   tools/sim/emulate_workflow.sh <scratch-dir> [log-file] [--force-test-failure]
# Needs the repo venv (h5py numpy pyproj Pillow) and PyYAML:  .venv/bin/pip install pyyaml   (venv only, for this emulator)
set -u
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
py="${PYTHON:-$repo/.venv/bin/python}"
scratch="${1:?usage: emulate_workflow.sh <scratch-dir> [log-file]}"
log="$(dirname "$scratch")/reports/workflow_emulation.log"
extra=""
shift
for a in "$@"; do case "$a" in --force-test-failure) extra="--force-test-failure" ;; *) log="$a" ;; esac; done
mkdir -p "$(dirname "$log")"
"$py" -c "import yaml" 2>/dev/null || { echo "PyYAML missing: $repo/.venv/bin/pip install pyyaml"; exit 3; }
# the real Earthdata token must never reach the emulation
unset EARTHDATA_TOKEN
exec "$py" "$here/emulate_workflow.py" --scratch "$scratch" --log "$log" $extra
