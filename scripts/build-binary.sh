#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/venv/bin/python}"

[ -x "$PYTHON" ] || {
    printf 'Python environment not found: %s\n' "$PYTHON" >&2
    exit 1
}

"$PYTHON" -m PyInstaller --version >/dev/null 2>&1 || {
    printf 'PyInstaller is not installed. Run: %s -m pip install pyinstaller\n' "$PYTHON" >&2
    exit 1
}

cd "$ROOT_DIR"
if [ -d "$ROOT_DIR/web" ]; then
    (cd "$ROOT_DIR/web" && npm run build)
fi

"$PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --name daybreak.bin \
    --paths "$ROOT_DIR" \
    --add-data "$ROOT_DIR/web/dist-app:web/dist-app" \
    --add-data "$ROOT_DIR/daybreak-persist/config.json:daybreak-defaults" \
    --add-data "$ROOT_DIR/daybreak-persist/agents:daybreak-defaults/agents" \
    --collect-all agents \
    --distpath "$ROOT_DIR/release/binary" \
    --workpath "$ROOT_DIR/release/pyinstaller-build" \
    --specpath "$ROOT_DIR/release" \
    "$ROOT_DIR/main.py"

printf 'binary created: %s\n' "$ROOT_DIR/release/binary/daybreak.bin"
