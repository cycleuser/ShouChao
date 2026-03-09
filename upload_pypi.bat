@echo off
REM Upload ShouChao to PyPI
echo Building ShouChao...
python -m build
echo.
echo Uploading to PyPI...
python -m twine upload dist/*
echo.
echo Done!
pause
