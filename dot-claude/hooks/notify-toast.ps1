# Claude Code Notification hook -> Windows toast.
# Reads hook JSON on stdin ({message, title?, session_id...}), fires a WinRT toast.
# Must run under Windows PowerShell 5.1 (powershell.exe) - WinRT types do not load in pwsh 7.
$raw = [Console]::In.ReadToEnd()
$msg = 'Claude Code notification'
$title = 'Claude Code'
try {
  $j = $raw | ConvertFrom-Json
  if ($j.message) { $msg = [string]$j.message }
  if ($j.title) { $title = [string]$j.title }
} catch {}

try {
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
  [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
  $esc = [System.Security.SecurityElement]::Escape($msg)
  $escTitle = [System.Security.SecurityElement]::Escape($title)
  $xml = "<toast><visual><binding template=`"ToastGeneric`"><text>$escTitle</text><text>$esc</text></binding></visual></toast>"
  $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
  $doc.LoadXml($xml)
  $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
  [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show((New-Object Windows.UI.Notifications.ToastNotification($doc)))
} catch {}
exit 0
