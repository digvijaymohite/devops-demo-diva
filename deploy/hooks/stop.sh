#!/bin/bash
# Runs from the previously deployed revision. Must tolerate a half-installed
# or entirely absent service, or a failed deploy can never be superseded.
set -uo pipefail
systemctl stop shoutout-api 2>/dev/null || true
exit 0
