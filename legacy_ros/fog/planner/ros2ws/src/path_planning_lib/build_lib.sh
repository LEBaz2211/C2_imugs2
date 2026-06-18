#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d Fields2Cover ]; then
  cd Fields2Cover
  mkdir -p build
  cd build
  cmake -DCMAKE_BUILD_TYPE=Release -DUSE_ORTOOLS_RELEASE=ON ..
  make -j"$(nproc)"
  make install
  cd "$SCRIPT_DIR"
else
  echo "Fields2Cover source not vendored; skipping optional Fields2Cover native build."
fi

# Build Path Planning Lib Library
python3 "$SCRIPT_DIR/setup.py" bdist_wheel
cd dist && python3 -m pip install *.whl --force-reinstall --no-deps
