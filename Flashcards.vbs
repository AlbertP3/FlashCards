Set oShell = CreateObject ("Wscript.Shell") 
Dim strArgs
strArgs = "cmd /c Flashcards.bat"
oShell.Run strArgs, 0, false