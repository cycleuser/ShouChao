@echo off
REM ShouChao - Auto bump version, build, upload to PyPI, and push to GitHub
setlocal
cd /d "%~dp0"

if not defined PYTHON set "PYTHON=python"
set "VERSION_FILE=shouchao\__init__.py"

echo === ShouChao PyPI Upload ===

echo [1/6] Bumping patch version...
%PYTHON% -c "import re,sys;p='%VERSION_FILE%'.replace('\\','/');t=open(p,encoding='utf-8').read();m=re.search(r'(__version__\s*=\"(\d+\.\d+\.)(\d+)\")',t);old=m.group(2)+m.group(3);new=m.group(2)+str(int(m.group(3))+1);open(p,'w',encoding='utf-8').write(t.replace(m.group(1),'__version__ = \"'+new+'\"'));print(f'  {old} -> {new}')"
if %errorlevel% neq 0 (echo Version bump failed! & exit /b 1)

echo [2/6] Cleaning old builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"

echo [3/6] Installing build tools...
%PYTHON% -m pip install --upgrade build twine -q

echo [4/6] Building package...
%PYTHON% -m build
if %errorlevel% neq 0 (echo Build failed! & exit /b 1)
%PYTHON% -m twine check dist\*
if %errorlevel% neq 0 (echo Check failed! & exit /b 1)

echo [5/6] Uploading to PyPI...
%PYTHON% -m twine upload dist\*
if %errorlevel% neq 0 (echo Upload failed! & exit /b 1)

echo [6/6] Pushing to GitHub...
for /f "delims=" %%v in ('%PYTHON% -c "import re;t=open('%VERSION_FILE%'.replace('\\','/')).read();m=re.search(r'__version__\s*=\"(.+?)\"',t);print(m.group(1))"') do set "NEW_VERSION=%%v"
git add -A
git commit -m "release v%NEW_VERSION%"
git push origin
if %errorlevel% neq 0 (echo Git push failed! & exit /b 1)

echo === Done! v%NEW_VERSION% ===
endlocal
pause
