@echo off
rem Thin Runtime Core launcher; the native program is installed by the npm package pinned to this plugin.
setlocal DisableDelayedExpansion
where npx >nul 2>nul
if errorlevel 1 (
  echo IdeasWork: Node.js 22+ ^(npx^) is required for the local Runtime Core. >&2
  exit /b 2
)
rem Private, empty npm project root: never read .npmrc or node_modules from the caller's repository.
set "IW_PREFIX=%TEMP%\ideaswork-npx"
if defined USERPROFILE set "IW_PREFIX=%USERPROFILE%\.ideaswork\npx"
if not exist "%IW_PREFIX%" mkdir "%IW_PREFIX%"
rem Already-installed exact version: local npm cache only, never the registry.
call npx --yes --no-install --offline --prefix "%IW_PREFIX%" "@ideaswork/cli-dev@2026.1106.154531-dev" --runtime-only --help <nul >nul 2>nul
if errorlevel 1 goto ideaswork_install
call npx --yes --no-install --offline --prefix "%IW_PREFIX%" "@ideaswork/cli-dev@2026.1106.154531-dev" --runtime-only %*
exit /b %ERRORLEVEL%

:ideaswork_install
rem First run or upgrade: revalidate the packument; npm falls back to the cached response when offline.
call npx --yes --prefer-online --prefix "%IW_PREFIX%" "@ideaswork/cli-dev@2026.1106.154531-dev" --runtime-only --help <nul >nul
if errorlevel 1 (
  echo IdeasWork: 本地 Runtime Core（"@ideaswork/cli-dev@2026.1106.154531-dev"）安装失败：可能是该版本尚未发布，或当前无法联网。 >&2
  exit /b 1
)
call npx --yes --no-install --offline --prefix "%IW_PREFIX%" "@ideaswork/cli-dev@2026.1106.154531-dev" --runtime-only %*
exit /b %ERRORLEVEL%
