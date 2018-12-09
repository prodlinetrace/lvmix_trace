@echo off
set LOGDIR=d:\log
set SRC1=%LOGDIR%\prodasync.log
set SRC2=%LOGDIR%\prodasync-missing.log
set SRC3=%LOGDIR%\prodasync-remove.log
set DEST=%LOGDIR%\%DATE%\

if not exist %DEST% (
	echo "Created logrotate dir: %DEST%"
	mkdir %DEST%
)
if exist %SRC1% (
	echo "log file: %SRC1% rotated and saved at: %DEST%"
	move %SRC1% %DEST%
)
if exist %SRC2% (
	echo "log file: %SRC2% rotated and saved at: %DEST%"
	move %SRC2% %DEST%
)
if exist %SRC3% (
	echo "log file: %SRC3% rotated and saved at: %DEST%"
	move %SRC3% %DEST%
)

rem remove files older than 30 days:
forfiles -p %LOGDIR% /D -30 /C "cmd /c echo removing @path && rd /q /s @path"