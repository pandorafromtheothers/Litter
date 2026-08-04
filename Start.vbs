dim cmd
cmd = "{YOUR_PATH_TO_LITTER}\initalize.bat"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run cmd, 0
Set WshShell = Nothing