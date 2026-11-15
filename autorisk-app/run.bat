@echo off
REM Double-click to start AutoRisk, or run "run.bat <command>" (setup, backend, frontend, reset-db, help).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
if errorlevel 1 pause
