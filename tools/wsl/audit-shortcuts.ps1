# Read every Claude shortcut on the Desktop and report target, args and working dir.
# Read-only. Nothing is created, renamed or deleted here.
#
# Inline PowerShell through the Bash tool mangles the quoting on these, so this lives
# in a file. Output is one block per shortcut, so duplicates are visible by eye.

$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath('Desktop')
$shell   = New-Object -ComObject WScript.Shell

Get-ChildItem $desktop -Filter '*.lnk' | Sort-Object Name | ForEach-Object {
  $l = $shell.CreateShortcut($_.FullName)
  Write-Output ("### " + $_.BaseName)
  Write-Output ("  target : " + $l.TargetPath)
  if ($l.Arguments)        { Write-Output ("  args   : " + $l.Arguments) }
  if ($l.WorkingDirectory) { Write-Output ("  wd     : " + $l.WorkingDirectory) }
  if ($l.Description)      { Write-Output ("  desc   : " + $l.Description) }
  Write-Output ("  mtime  : " + $_.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))
}
