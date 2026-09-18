#!/bin/bash
set -euo pipefail

systemctl daemon-reload
systemctl enable shoutout-api
systemctl restart shoutout-api

nginx -t
systemctl enable nginx
systemctl reload nginx 2>/dev/null || systemctl restart nginx
