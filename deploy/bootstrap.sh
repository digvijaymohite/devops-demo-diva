#!/bin/bash
# First-boot provisioning for the shoutout board instance (Amazon Linux 2023).
# Runs as root from EC2 user-data. Safe to re-run.
#
# This prepares the host only. The application itself arrives via CodeDeploy,
# so there is no clone, no npm and no build step here.
set -euxo pipefail

APP_ROOT=/opt/shoutout

dnf update -y
dnf install -y nginx python3.11 python3.11-pip ruby wget

id -u shoutout &>/dev/null || useradd --system --home-dir "$APP_ROOT" --shell /sbin/nologin shoutout
mkdir -p "$APP_ROOT/release"
chown -R shoutout:shoutout "$APP_ROOT"

# CodeDeploy agent. The installer is region-specific and needs ruby.
if ! systemctl is-active --quiet codedeploy-agent; then
  cd /tmp
  wget -q "https://aws-codedeploy-ap-south-1.s3.ap-south-1.amazonaws.com/latest/install" -O install-codedeploy
  chmod +x install-codedeploy
  ./install-codedeploy auto
fi
systemctl enable --now codedeploy-agent

# AL2023 ships a default server on :80 that would collide with ours.
if grep -q "listen       80;" /etc/nginx/nginx.conf; then
  sed -i '/^\s*server\s*{/,/^\s*}/{ s/listen       80;/listen       8080;/; s/listen       \[::\]:80;/listen       [::]:8080;/ }' /etc/nginx/nginx.conf
fi

systemctl enable --now nginx

echo "bootstrap complete - waiting for CodeDeploy to deliver the application"
