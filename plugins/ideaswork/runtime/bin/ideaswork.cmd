@echo off
rem Thin Runtime Core launcher; the native program is installed by the npm package pinned to this plugin.
setlocal DisableDelayedExpansion
where node >nul 2>nul
if errorlevel 1 (
  echo IdeasWork: Node.js 22+ ^(node^) is required for the local Runtime Core. >&2
  echo   错误码：node_missing >&2
  exit /b 2
)
rem Private, otherwise empty npm project root: npm must never read the caller's repository .npmrc or node_modules.
set "IW_PREFIX=%TEMP%\ideaswork-npx"
if defined USERPROFILE set "IW_PREFIX=%USERPROFILE%\.ideaswork\npx"
if not exist "%IW_PREFIX%" mkdir "%IW_PREFIX%"
set "IW_PACKAGE_DIR=%IW_PREFIX%\node_modules\@ideaswork\cli-preprod"
set "IW_ENTRY=%IW_PACKAGE_DIR%\scripts\run.cjs"
rem The prefix holds exactly the pinned version: run its entry point directly, with no npm and no network.
rem npx --prefix cannot do this: it resolves a prefix-local package but never puts its .bin on the child PATH,
rem so the spawned shell cannot find `ideaswork` (Windows, npm 11.20, already-installed package).
node -e "process.exit(require(process.argv[1] + '/package.json').version === process.argv[2] ? 0 : 1)" "%IW_PACKAGE_DIR%" "2026.1118.131717-preprod" >nul 2>nul
if errorlevel 1 goto ideaswork_install
if not exist "%IW_ENTRY%" goto ideaswork_install
goto ideaswork_run
:ideaswork_install
where npm >nul 2>nul
if errorlevel 1 (
  echo IdeasWork: Node.js 22+ ^(npm^) is required to install the local Runtime Core. >&2
  echo   错误码：npm_missing >&2
  exit /b 2
)
rem First run or upgrade. --prefer-online revalidates the packument; cd into the private prefix so npm reads
rem that prefix's project config, never the caller's repository.
set "IW_LOG=%IW_PREFIX%\.npm-install.log"
del "%IW_LOG%" >nul 2>nul
pushd "%IW_PREFIX%" >nul
call npm install --prefix "%IW_PREFIX%" --prefer-online --no-save --no-audit --no-fund "@ideaswork/cli-preprod@2026.1118.131717-preprod" <nul >"%IW_LOG%" 2>&1
set "IW_NPM_EXIT=%ERRORLEVEL%"
popd >nul
if not "%IW_NPM_EXIT%"=="0" goto ideaswork_install_failed
del "%IW_LOG%" >nul 2>nul
if not exist "%IW_ENTRY%" goto ideaswork_entry_missing
node -e "process.exit(require(process.argv[1] + '/package.json').version === process.argv[2] ? 0 : 1)" "%IW_PACKAGE_DIR%" "2026.1118.131717-preprod" >nul 2>nul
if errorlevel 1 goto ideaswork_version_mismatch
:ideaswork_run
node "%IW_ENTRY%" --runtime-only %*
exit /b %ERRORLEVEL%

:ideaswork_install_failed
findstr /I /C:"ETARGET" /C:"No matching version" "%IW_LOG%" >nul 2>nul
if not errorlevel 1 goto ideaswork_version_not_found
findstr /I /C:"ENOTFOUND" /C:"EAI_AGAIN" /C:"ECONNREFUSED" /C:"ECONNRESET" /C:"ETIMEDOUT" /C:"ENETUNREACH" /C:"EHOSTUNREACH" /C:"network request" /C:"network connectivity" "%IW_LOG%" >nul 2>nul
if not errorlevel 1 goto ideaswork_registry_unreachable
echo IdeasWork: 本地 Runtime Core（"@ideaswork/cli-preprod@2026.1118.131717-preprod"）安装失败：npm install 未完成。 >&2
echo   错误码：npm_install_failed >&2
goto ideaswork_report_log

:ideaswork_version_not_found
echo IdeasWork: npm registry 上查不到 @ideaswork/cli-preprod@2026.1118.131717-preprod，或本地 npm 缓存缺少该版本且当前无法联网刷新。 >&2
echo   错误码：npm_version_not_found >&2
echo   请确认该版本已发布并与插件版本一致；不要改用其他版本，也不要清空整个 npm 缓存。 >&2
goto ideaswork_report_log

:ideaswork_registry_unreachable
echo IdeasWork: 无法下载本地 Runtime Core（"@ideaswork/cli-preprod@2026.1118.131717-preprod"）：当前环境没有网络（沙箱里常见）。 >&2
echo   错误码：npm_registry_unreachable >&2
echo   请让用户放开网络权限，或先在有网络的终端运行一次本命令完成安装，然后重试；不要改用其他版本。 >&2

:ideaswork_report_log
type "%IW_LOG%" >&2
del "%IW_LOG%" >nul 2>nul
exit /b 1

:ideaswork_entry_missing
echo IdeasWork: 本地 Runtime Core（"@ideaswork/cli-preprod@2026.1118.131717-preprod"）安装后找不到入口（%IW_ENTRY%）。 >&2
echo   错误码：launcher_entry_missing >&2
exit /b 1

:ideaswork_version_mismatch
echo IdeasWork: 本地 Runtime Core（"@ideaswork/cli-preprod@2026.1118.131717-preprod"）安装后版本与插件不一致；私有前缀被其他版本占用。 >&2
echo   错误码：launcher_version_mismatch >&2
exit /b 1
