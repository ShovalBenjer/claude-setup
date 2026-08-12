# CDP client that ATTACHES to the operator's already-running, already-logged-in Chrome.
# WINDOWS POWERSHELL 5.1 ONLY. Companion to cdp.py, which launches its own instance.
#
# WHY 5.1 AND NOT pwsh 7, measured rather than assumed. Chrome's DevTools endpoint
# rejects a WebSocket upgrade that carries an Origin header:
#
#   pwsh 7, default            -> 500 (server returned 500 when 101 was expected)
#   pwsh 7, Origin set to null -> 403
#   Windows PowerShell 5.1     -> state: Open
#
# .NET Framework's ClientWebSocket sends no Origin; .NET 7+ does and gives no supported
# way to remove it. So this file uses New-Object rather than ::new() throughout, because
# the generic ::new() forms are what broke under 5.1 in the first draft.
#
# WHY NOT tools/browser/cdp.py. That tool launches its own Chrome and drives it from WSL.
# Chrome here binds the debug port to WINDOWS' 127.0.0.1: WSL cannot reach it
# (192.168.160.1:9224 refused), netsh portproxy needs elevation, and a userspace relay on
# 9225 was unreachable, most likely inbound firewall. The client has to live on this side.
#
# It ATTACHES to the operator's existing logged-in profile rather than launching a clean
# one, which is the point: authenticated pages work. It also opens exactly one tab and
# closes it again, because that profile currently holds 33 real tabs.

param(
  [Parameter(Mandatory=$true)][string]$Url,
  [string]$Prompt = "",
  [int]$Port = 9224,
  [int]$WaitSec = 30
)
$ErrorActionPreference = "Stop"

# Open about:blank and attach BEFORE navigating. Creating the tab directly at the target
# URL looks simpler and does not work: a cross-origin navigation swaps the renderer, so
# the webSocketDebuggerUrl handed back by /json/new is stale by the time the page loads
# and Chrome answers "No such target id". Measured: about:blank attaches every time,
# https://example.com fails every time, with the identical code.
$tab = (Invoke-WebRequest -Uri "http://127.0.0.1:$Port/json/new?about%3Ablank" -Method PUT -UseBasicParsing).Content | ConvertFrom-Json

$ws = New-Object System.Net.WebSockets.ClientWebSocket
$ct = [Threading.CancellationToken]::None
$ws.ConnectAsync([Uri]$tab.webSocketDebuggerUrl, $ct).Wait()

function Send-Cmd($id, $method, $params) {
  $m = @{ id = $id; method = $method }
  if ($params) { $m.params = $params }
  $bytes = [Text.Encoding]::UTF8.GetBytes(($m | ConvertTo-Json -Depth 10 -Compress))
  $seg = New-Object System.ArraySegment[byte] (,$bytes)
  $script:ws.SendAsync($seg, 'Text', $true, $script:ct).Wait()
}
function Read-Id($id, $timeoutSec) {
  # Chrome splits large payloads across continuation frames. Assuming one frame per
  # message works on small replies and silently truncates the interesting ones.
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    $sb = New-Object Text.StringBuilder
    do {
      $buf = New-Object System.ArraySegment[byte] (,(New-Object byte[] 65536))
      $res = $script:ws.ReceiveAsync($buf, $script:ct).GetAwaiter().GetResult()
      [void]$sb.Append([Text.Encoding]::UTF8.GetString($buf.Array, 0, $res.Count))
    } while (-not $res.EndOfMessage)
    $o = $sb.ToString() | ConvertFrom-Json
    if ($o.id -eq $id) { return $o }
  }
  throw "timeout waiting for id=$id"
}

$n = 1
Send-Cmd $n 'Page.navigate' @{ url = $Url }
$null = Read-Id $n 60; $n++
Start-Sleep -Seconds 6

if ($Prompt -ne "") {
  $lit = $Prompt | ConvertTo-Json
  $js = "(function(){var t=document.querySelector('rich-textarea .ql-editor')||document.querySelector('div[contenteditable=\""true\""]')||document.querySelector('textarea');if(!t)return 'NO_COMPOSER';t.focus();if(t.tagName==='TEXTAREA'){t.value=$lit;}else{t.innerText=$lit;}t.dispatchEvent(new Event('input',{bubbles:true}));return 'TYPED';})()"
  Send-Cmd $n 'Runtime.evaluate' @{ expression = $js; returnByValue = $true }
  $r = Read-Id $n 60; $n++
  Write-Output ("COMPOSER: " + $r.result.result.value)
  Start-Sleep -Milliseconds 900
  foreach ($ty in @('keyDown','keyUp')) {
    Send-Cmd $n 'Input.dispatchKeyEvent' @{ type=$ty; key='Enter'; code='Enter'; windowsVirtualKeyCode=13; nativeVirtualKeyCode=13 }
    $null = Read-Id $n 30; $n++
  }
  Start-Sleep -Seconds $WaitSec
}

Send-Cmd $n 'Runtime.evaluate' @{ expression = 'document.body.innerText'; returnByValue = $true }
$r = Read-Id $n 120
Write-Output "----- PAGE TEXT -----"
Write-Output $r.result.result.value

$ws.Dispose()
Invoke-WebRequest -Uri "http://127.0.0.1:$Port/json/close/$($tab.id)" -UseBasicParsing | Out-Null
Write-Output "----- tab closed -----"

# STATUS 2026-08-06: the transport is proven end to end. It attaches, navigates, types
# into a composer, submits, reads document.body.innerText and closes its own tab. Two
# runs against Gemini with a YouTube URL produced one partial answer and then one empty
# answer, so the round trip works and the Gemini side is not reliable at this wait.
# Whoever picks this up should poll until the response text stops growing rather than
# sleeping a fixed WaitSec, which is what both failures actually were.
