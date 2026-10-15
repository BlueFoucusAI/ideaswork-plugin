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
call npx --yes --prefer-offline --prefix "%IW_PREFIX%" "@ideaswork/cli-preprod@2026.1015.200710-preprod" --runtime-only %*
exit /b %ERRORLEVEL%
