Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "taskkill /f /im llama-server.exe", 0, False
WshShell.Run "taskkill /f /im python.exe", 0, False
WshShell.Run "taskkill /f /im node.exe", 0, False
MsgBox "LLM Platform Stopped!", vbInformation, "Done"