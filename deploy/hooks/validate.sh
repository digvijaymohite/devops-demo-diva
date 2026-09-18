#!/bin/bash
# Fail the deployment if the new revision cannot serve traffic, so CodeDeploy
# reports a failure instead of leaving a broken board live.
set -euo pipefail

for attempt in $(seq 1 30); do
  api=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1/api/health || echo 000)
  page=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1/ || echo 000)
  if [ "$api" = "200" ] && [ "$page" = "200" ]; then
    echo "healthy after ${attempt}s (api=$api page=$page)"
    exit 0
  fi
  echo "attempt $attempt: api=$api page=$page"
  sleep 1
done

echo "service did not become healthy" >&2
systemctl status shoutout-api --no-pager --lines=30 >&2 || true
journalctl -u shoutout-api --no-pager --lines=50 >&2 || true
exit 1
