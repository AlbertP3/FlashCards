@ECHO OFF

CD /D %~dp0\..\
SET MyPath=.\venv\Scripts\python

%@Try% 
"%MyPath%" .\scripts\init.py
%@EndTry%
