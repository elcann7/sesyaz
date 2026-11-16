Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
AppDir = FSO.GetParentFolderName(WScript.ScriptFullName) & "\app"
Args = ""
If WScript.Arguments.Count > 0 Then
  Args = " " & WScript.Arguments(0)
End If
WshShell.Run """pythonw.exe"" """ & AppDir & "\main.py""" & Args, 0, False
