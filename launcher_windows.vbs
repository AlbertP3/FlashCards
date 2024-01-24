Set oShell = CreateObject ("Wscript.Shell") 
Dim WshShell, strCurDir
Set WshShell = CreateObject("WScript.Shell")
strCurDir = WshShell.CurrentDirectory
Dim strArgs
strArgs = "cmd /c " & strCurDir & "\src\launcher.bat"
oShell.Run strArgs, 0, false