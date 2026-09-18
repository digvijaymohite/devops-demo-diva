#!/bin/bash
# CodeDeploy wipes the destination directory, so only prepare things that live
# outside it.
set -euo pipefail

APP_ROOT=/opt/shoutout

id -u shoutout &>/dev/null || useradd --system --home-dir "$APP_ROOT" --shell /sbin/nologin shoutout
mkdir -p "$APP_ROOT"
