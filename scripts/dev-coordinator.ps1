# Local development: load the gitignored .env.local into this process only, then run the coordinator.
# The coordinator never reads .env files itself (see README). Values are never echoed.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root '.env.local'
if (-not (Test-Path $envFile)) { throw "Missing $envFile; see .env.example for the variable names." }
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*([A-Z0-9_]+)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process') }
}
Set-Location $root
cargo run -p mvm-coordinator --locked @args
