#!/usr/bin/env bash
# Runs after the board's post-build script: removes services the endpoint doesn't need.
set -euo pipefail
rm -f "$TARGET_DIR/etc/init.d/S50crond"
# No login prompts: the board script adds one on HDMI and the generic one sits on the serial console.
sed -i '/^[^#].*\/sbin\/getty/d' "$TARGET_DIR/etc/inittab"
