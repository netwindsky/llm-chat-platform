Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "cmd /c cd /d """ & strPath & "\server"" && python main.py", 0, False
WScript.Sleep 4000
WshShell.Run "cmd /c cd /d """ & strPath & "\web"" && npm run dev", 0, False
WScript.Sleep 2000
WshShell.Run "http://localhost:38522", 1, False
MsgBox "LLM Platform Started!" & vbCrLf & "Backend: http://localhost:38520" & vbCrLf & "Frontend: http://localhost:38522", vbInformation, "LLM Platform"