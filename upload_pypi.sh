#!/usr/bin/env bash
# ShouChao - Auto bump version, build, upload to PyPI, and push to GitHub
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON="${PYTHON:-python3}"
VERSION_FILE="shouchao/__init__.py"

echo "=== ShouChao PyPI Upload ==="

echo "[1/6] Bumping patch version..."
"$PYTHON" -c "
import re, sys
p = '$VERSION_FILE'
t = open(p, encoding='utf-8').read()
m = re.search(r'(__version__\s*=\s*\"(\d+\.\d+\.)(\d+)\")', t)
if not m: print('ERROR: cannot parse version'); sys.exit(1)
old_v = m.group(2) + m.group(3)
new_v = m.group(2) + str(int(m.group(3)) + 1)
open(p, 'w', encoding='utf-8').write(t.replace(m.group(1), '__version__ = \"' + new_v + '\"'))
print(f'  {old_v} -> {new_v}')
"

echo "[2/6] Cleaning old builds..."
rm -rf dist/ build/ *.egg-info shouchao.egg-info

echo "[3/6] Installing build tools..."
"$PYTHON" -m pip install --upgrade build twine -q

echo "[4/6] Building package..."
"$PYTHON" -m build
"$PYTHON" -m twine check dist/*

echo "[5/6] Uploading to PyPI..."
"$PYTHON" -m twine upload dist/*

NEW_VERSION=$("$PYTHON" -c "import re; t=open('$VERSION_FILE').read(); m=re.search(r'__version__\s*=\s*\"(.+?)\"', t); print(m.group(1))")
echo "[6/6] Pushing to GitHub..."
git add -A
git commit -m "release v${NEW_VERSION}"
git push origin

echo "=== Done! v${NEW_VERSION} ==="
