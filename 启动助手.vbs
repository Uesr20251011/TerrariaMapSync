Option Explicit
Dim shell, files, base, pythonw, command
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
base = files.GetParentFolderName(WScript.ScriptFullName)
pythonw = shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.conda\envs\terraria-sync\pythonw.exe"
If Not files.FileExists(pythonw) Then pythonw = "pythonw.exe"
command = """" & pythonw & """ """ & base & "\main.py" & """"
shell.Run command, 0, False
