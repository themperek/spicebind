#!/bin/sh
# Rebuild generated/ using the pinned IIC-OSIC-TOOLS image.
# https://github.com/iic-jku/IIC-OSIC-TOOLS
set -eu
cd "$(dirname "$0")/.."
python3 tools/regenerate.py --force-container
