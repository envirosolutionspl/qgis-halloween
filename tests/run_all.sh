#!/bin/sh
# Run the test suite without QGIS (needs: pip install PyQt5).
# Previews of the menu bar, web and spiders are written to tests/out/.
set -e
cd "$(dirname "$0")"
QT_QPA_PLATFORM=offscreen python -m unittest discover -s . -p "test_*.py" "$@"
