#!/bin/bash
# Install dependencies and publish the freshly built assets.
set -euo pipefail

APP_ROOT=/opt/shoutout
RELEASE="$APP_ROOT/release"

# The venv lives outside the CodeDeploy destination so it survives deployments
# and only changes when requirements.txt does.
if [ ! -x "$APP_ROOT/venv/bin/python" ]; then
  python3.11 -m venv "$APP_ROOT/venv"
fi
"$APP_ROOT/venv/bin/pip" install --quiet --upgrade pip
"$APP_ROOT/venv/bin/pip" install --quiet -r "$RELEASE/backend/requirements.txt"

# Frontend was built in CodeBuild; here we only publish it.
install -d /usr/share/nginx/html
rm -rf /usr/share/nginx/html/*
cp -r "$RELEASE/frontend/dist/." /usr/share/nginx/html/

install -m 0644 "$RELEASE/deploy/shoutout-api.service" /etc/systemd/system/shoutout-api.service
install -m 0644 "$RELEASE/deploy/nginx-shoutout.conf" /etc/nginx/conf.d/shoutout.conf

cat > /etc/shoutout.env <<'ENVEOF'
AWS_REGION=ap-south-1
SHOUTOUTS_TABLE=diva-shoutouts
IMAGES_BUCKET=diva-shoutout-images-851725336997
BOARD_ID=main
ALLOWED_ORIGINS=*
ENVEOF
chmod 0644 /etc/shoutout.env

chown -R shoutout:shoutout "$APP_ROOT"
