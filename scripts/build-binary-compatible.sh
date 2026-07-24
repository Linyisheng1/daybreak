#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_IMAGE="daybreak-release-builder:glibc2.31"
IMAGE="${DAYBREAK_BUILD_IMAGE:-$DEFAULT_IMAGE}"
CONTAINER_PYTHON="${DAYBREAK_BUILD_PYTHON:-/usr/local/bin/python}"

command -v docker >/dev/null 2>&1 || {
    printf 'Docker is required for the compatible Linux release build.\n' >&2
    exit 1
}

if [ -z "${DAYBREAK_BUILD_IMAGE:-}" ]; then
    docker build \
        --tag "$DEFAULT_IMAGE" \
        --file "$ROOT_DIR/docker/release-builder.Dockerfile" \
        "$ROOT_DIR"
fi

if [ -d "$ROOT_DIR/web" ]; then
    if [ ! -d "$ROOT_DIR/web/node_modules" ]; then
        (cd "$ROOT_DIR/web" && npm ci)
    fi
    (cd "$ROOT_DIR/web" && npm run build)
fi

docker run --rm \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --volume "$ROOT_DIR:/workspace" \
    --workdir /workspace \
    "$IMAGE" \
    bash -lc "
        set -Eeuo pipefail
        rm -rf /workspace/release/compat-venv
        \"$CONTAINER_PYTHON\" -m venv /workspace/release/compat-venv
        /workspace/release/compat-venv/bin/python -m pip install \
            --disable-pip-version-check \
            --no-cache-dir \
            -r /workspace/requirements.txt \
            pyinstaller
        BUILD_WEB=0 \
            PYTHON=/workspace/release/compat-venv/bin/python \
            /workspace/scripts/build-binary.sh
    "

docker run --rm \
    --volume "$ROOT_DIR/release/binary/daybreak.bin:/opt/daybreak.bin:ro" \
    "$IMAGE" \
    /opt/daybreak.bin --self-test-encoding

printf 'glibc 2.31 compatible binary created: %s\n' \
    "$ROOT_DIR/release/binary/daybreak.bin"
