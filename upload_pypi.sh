#!/bin/bash
# Upload ShouChao to PyPI
set -e
echo "Building ShouChao..."
python3 -m build
echo ""
echo "Uploading to PyPI..."
python3 -m twine upload dist/*
echo ""
echo "Done!"
