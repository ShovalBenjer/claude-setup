# Drives `claude setup-token` non-interactively:
# - spawns it with redirected stdio
# - mirrors stdout to out.log (token later scrubbed; secrets never printed to console)
# - when code.txt appears, feeds its content to the process stdin
# - on exit, extracts the token line into token.txt (0600-ish), scrubs out.log
$dir = "$env:USERPROFILE\.claude\.token-flow"
New-Item -ItemType Directory -Force $dir | Out-Null
Remove-Item "$dir\out.log","$dir\token.txt","$dir\code.txt","$dir\done" -ErrorAction SilentlyContinue

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cmd.exe"
$psi.Arguments = "/c claude setup-token"
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)

$outFile = "$dir\out.log"
$reader = $p.StandardOutput
$errReader = $p.StandardError

# async drain stderr
$null = Register-ObjectEvent -InputObject $p -EventName Exited -Action {}
Start-Job -ScriptBlock { param($r,$f) while (-not $r.EndOfStream) { Add-Content $f ("ERR: " + $r.ReadLine()) } } -ArgumentList $errReader,$outFile | Out-Null

$fed = $false
while (-not $p.HasExited) {
    while (-not $reader.EndOfStream -and $reader.Peek() -ge 0) {
        $line = $reader.ReadLine()
        Add-Content $outFile $line
        if ($reader.EndOfStream) { break }
    }
    if (-not $fed -and (Test-Path "$dir\code.txt")) {
        $code = (Get-Content "$dir\code.txt" -Raw).Trim()
        if ($code) { $p.StandardInput.WriteLine($code); $fed = $true }
    }
    Start-Sleep -Milliseconds 400
}
# final drain
while (-not $reader.EndOfStream) { Add-Content $outFile $reader.ReadLine() }

# extract token (sk-ant-oat... pattern) to token.txt, scrub log
$log = Get-Content $outFile -Raw
$m = [regex]::Match($log, "sk-ant-[A-Za-z0-9_\-]+")
if ($m.Success) {
    Set-Content "$dir\token.txt" $m.Value -NoNewline
    (Get-Content $outFile -Raw) -replace "sk-ant-[A-Za-z0-9_\-]+", "[TOKEN-CAPTURED]" | Set-Content $outFile
}
Set-Content "$dir\done" "exit=$($p.ExitCode)"
