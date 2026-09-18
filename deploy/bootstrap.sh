#!/bin/bash
# First-boot provisioning for the shoutout board instance (Amazon Linux 2023).
# Runs as root from EC2 user-data. Safe to re-run.
set -euxo pipefail

REPO_URL="${REPO_URL:-https://github.com/digvijaymohite/devops-demo-diva.git}"
APP_ROOT=/opt/shoutout
APP_DIR="$APP_ROOT/app"

dnf update -y
dnf install -y git nginx python3.11 python3.11-pip nodejs20 nodejs20-npm

ln -sf /usr/bin/node-20 /usr/local/bin/node 2>/dev/null || true
ln -sf /usr/bin/npm-20  /usr/local/bin/npm  2>/dev/null || true

id -u shoutout &>/dev/null || useradd --system --home-dir "$APP_ROOT" --shell /sbin/nologin shoutout
mkdir -p "$APP_ROOT"

if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --all --prune
  git -C "$APP_DIR" reset --hard origin/main
else
  git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi

# --- backend ---
python3.11 -m venv "$APP_ROOT/venv"
"$APP_ROOT/venv/bin/pip" install --upgrade pip
"$APP_ROOT/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

# --- frontend ---
cd "$APP_DIR/frontend"
npm install --no-audit --no-fund
npm run build
rm -rf /usr/share/nginx/html/*
cp -r dist/* /usr/share/nginx/html/

# --- config ---
cat > /etc/shoutout.env <<'ENVEOF'
AWS_REGION=ap-south-1
SHOUTOUTS_TABLE=diva-shoutouts
IMAGES_BUCKET=diva-shoutout-images-851725336997
BOARD_ID=main
ALLOWED_ORIGINS=*
ENVEOF
chmod 0644 /etc/shoutout.env

install -m 0644 "$APP_DIR/deploy/shoutout-api.service" /etc/systemd/system/shoutout-api.service
install -m 0644 "$APP_DIR/deploy/nginx-shoutout.conf" /etc/nginx/conf.d/shoutout.conf

# AL2023 ships a default server on :80 that would collide with ours.
if grep -q "listen       80;" /etc/nginx/nginx.conf; then
  sed -i '/^\s*server\s*{/,/^\s*}/{ s/listen       80;/listen       8080;/; s/listen       \[::\]:80;/listen       [::]:8080;/ }' /etc/nginx/nginx.conf
fi

chown -R shoutout:shoutout "$APP_ROOT"

systemctl daemon-reload
systemctl enable --now shoutout-api
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "bootstrap complete"
