@ECHO OFF

CD /D %~dp0\
SET MyPath=%~dp0\venv\Scripts\python

%@Try% 
"%MyPath%" .\scripts\launcher.pyw
%@EndTry%

