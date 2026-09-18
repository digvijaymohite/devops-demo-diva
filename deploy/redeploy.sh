#!/bin/bash
# Pull the latest main and restart. Run on the instance via SSM:
#   aws ssm send-command --document-name AWS-RunShellScript \
#     --parameters 'commands=["bash /opt/shoutout/app/deploy/redeploy.sh"]' ...
set -euxo pipefail

APP_ROOT=/opt/shoutout
APP_DIR="$APP_ROOT/app"

git -C "$APP_DIR" fetch --all --prune
git -C "$APP_DIR" reset --hard origin/main

"$APP_ROOT/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

cd "$APP_DIR/frontend"
npm install --no-audit --no-fund
npm run build
rm -rf /usr/share/nginx/html/*
cp -r dist/* /usr/share/nginx/html/

install -m 0644 "$APP_DIR/deploy/shoutout-api.service" /etc/systemd/system/shoutout-api.service
install -m 0644 "$APP_DIR/deploy/nginx-shoutout.conf" /etc/nginx/conf.d/shoutout.conf
chown -R shoutout:shoutout "$APP_ROOT"

systemctl daemon-reload
systemctl restart shoutout-api
nginx -t && systemctl reload nginx
echo "redeploy complete"
