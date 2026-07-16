#!/bin/sh
set -eu

profile_dir=/data/chromium
extension_dir=/opt/agent-browser/chrome-extension

mkdir -p "$profile_dir"
touch "$profile_dir/First Run"
rm -rf "$profile_dir"/Singleton* "$profile_dir/DevToolsActivePort"

i=0
until nc -z 127.0.0.1 8118; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
        echo "sandbox egress proxy did not become ready" >&2
        exit 1
    fi
    sleep 1
done

test -s "$extension_dir/manifest.json"

exec /usr/bin/chromium \
    --user-data-dir="$profile_dir" \
    --no-first-run \
    --disable-session-crashed-bubble \
    --window-position=0,0 \
    --window-size=1280,720 \
    --remote-debugging-address=127.0.0.1 \
    --remote-debugging-port=9222 \
    --remote-allow-origins='*' \
    --proxy-server=http://127.0.0.1:8118 \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-extensions-except="$extension_dir" \
    --load-extension="$extension_dir" \
    https://example.com/
