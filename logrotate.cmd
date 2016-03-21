@echo off
set LOGDIR=d:\log
set SRC=%LOGDIR%\prodasync.log
set DEST=%LOGDIR%\%DATE%\

if not exist %DEST% (
	echo "Created logrotate dir: %DEST%"
	mkdir %DEST%
)
if exist %SRC% (
	echo "log file: %SRC% rotated and saved at: %DEST%"
	move %SRC% %DEST%
)

rem remove files older than 30 days:
forfiles -p %LOGDIR% /D -30 /C "cmd /c echo removing @path && rd /q /s @path"