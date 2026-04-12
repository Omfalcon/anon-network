# Windows: run from repo root in PowerShell: .\startup.ps1
# Opens a cmd window per node so logs stay visible (like multiple terminals).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:PYTHONPATH = "."
Write-Host "Generating RSA keyring..."
python generate_keyring.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Starting Anon-Network nodes (Phase 4: ECDH + link AES-GCM)..."
$root = (Get-Location).Path

function Start-Node($port, $nodeName, $script) {
    $cmd = "title $nodeName & cd /d `"$root`" & set PYTHONPATH=. & set PORT=$port & set NODE_NAME=$nodeName & python `"$root\$script`""
    Start-Process cmd -ArgumentList "/k", $cmd
}

Start-Node 5000 "trustee" "trustee\app.py"
Start-Sleep -Seconds 1
Start-Node 5001 "ME1" "me\app.py"
Start-Node 5002 "ME2" "me\app.py"
Start-Sleep -Seconds 1
Start-Node 6001 "routerS" "router\app.py"
Start-Node 6002 "routerX" "router\app.py"
Start-Node 6003 "routerY" "router\app.py"
Start-Sleep -Seconds 1
Start-Node 7000 "receiverB" "receiver\app.py"

Write-Host "----------------------------------------------------------------"
Write-Host "Wait ~3s for ports to listen, then in THIS window run:"
Write-Host '  $env:PYTHONPATH="."; python -m sender.sender'
Write-Host "----------------------------------------------------------------"
