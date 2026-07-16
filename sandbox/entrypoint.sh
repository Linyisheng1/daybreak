#!/bin/sh
set -eu

mkdir -p /data/chromium /data/target
touch '/data/chromium/First Run'
rm -rf /data/chromium/Singleton* /data/chromium/DevToolsActivePort

echo "sandbox entrypoint starting supervisord"
exec supervisord -c /supervisord.conf
