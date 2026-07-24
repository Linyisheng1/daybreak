#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BINARY="${1:-$ROOT_DIR/daybreak.bin}"
VERSION="${2:-dev}"
OUTPUT_DIR="$ROOT_DIR/release"
PACKAGE_DIR="$OUTPUT_DIR/daybreak-linux-amd64-$VERSION"

[ -f "$BINARY" ] || {
    printf 'daybreak binary not found: %s\n' "$BINARY" >&2
    exit 1
}

rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/deploy" "$PACKAGE_DIR/daybreak-defaults"
install -m 755 "$BINARY" "$PACKAGE_DIR/daybreak.bin"
install -m 755 "$ROOT_DIR/daybreak" "$PACKAGE_DIR/daybreak"
install -m 644 "$ROOT_DIR/.env.example" "$PACKAGE_DIR/.env.example"
install -m 644 \
    "$ROOT_DIR/deploy/docker-compose.dependencies.yml" \
    "$PACKAGE_DIR/deploy/docker-compose.dependencies.yml"
install -m 600 \
    "$ROOT_DIR/daybreak-persist/config.json" \
    "$PACKAGE_DIR/daybreak-defaults/config.json"
cp -a "$ROOT_DIR/daybreak-persist/agents" "$PACKAGE_DIR/daybreak-defaults/agents"

if [ -n "${NUCLEI_BINARY:-}" ]; then
    [ -x "$NUCLEI_BINARY" ] || {
        printf 'Nuclei binary is not executable: %s\n' "$NUCLEI_BINARY" >&2
        exit 1
    }
    mkdir -p "$PACKAGE_DIR/tools"
    install -m 755 "$NUCLEI_BINARY" "$PACKAGE_DIR/tools/nuclei"
fi

if [ -n "${POC_LIBRARY_ARCHIVE:-}" ]; then
    [ -f "$POC_LIBRARY_ARCHIVE" ] || {
        printf 'PoC library archive not found: %s\n' "$POC_LIBRARY_ARCHIVE" >&2
        exit 1
    }
    mkdir -p "$PACKAGE_DIR/pocs"
    install -m 644 "$POC_LIBRARY_ARCHIVE" "$PACKAGE_DIR/pocs/TscanPlus_pocs_8690.zip"
fi

tar -C "$OUTPUT_DIR" -czf "$OUTPUT_DIR/daybreak-linux-amd64-$VERSION.tar.gz" \
    "daybreak-linux-amd64-$VERSION"

printf 'release package created: %s\n' "$OUTPUT_DIR/daybreak-linux-amd64-$VERSION.tar.gz"
