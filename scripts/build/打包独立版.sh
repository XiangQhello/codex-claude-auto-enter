#!/usr/bin/env bash

set -euo pipefail

BUILD_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$BUILD_DIR/../.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    bash "$ROOT_DIR/scripts/install/linux_macos.sh"
fi

"$VENV_PYTHON" -m pip install pyinstaller
cd "$ROOT_DIR"
"$VENV_PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name '解放单手' \
    --paths "$ROOT_DIR/src" \
    "$ROOT_DIR/src/app.py"

printf '独立版已生成：%s/dist/解放单手\n' "$ROOT_DIR"
