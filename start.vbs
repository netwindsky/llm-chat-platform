Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)

' 启动 API Server 1 (端口 38520)
WshShell.Run "cmd /c cd /d """ & strPath & "\server"" && python main.py --port 38520", 0, False
WScript.Sleep 4000

' 启动 API Server 2 (端口 39520)
WshShell.Run "cmd /c cd /d """ & strPath & "\server"" && python main.py --port 39520", 0, False
WScript.Sleep 4000

' 启动前端
WshShell.Run "cmd /c cd /d """ & strPath & "\web"" && npm run dev", 0, False
WScript.Sleep 2000

' 打开浏览器
WshShell.Run "http://localhost:38522", 1, False

MsgBox "LLM Platform Started!" & vbCrLf & _
       "API Server 1: http://localhost:38520" & vbCrLf & _
       "API Server 2: http://localhost:39520" & vbCrLf & _
       "Frontend: http://localhost:38522", _
       vbInformation, "LLM Platform"
