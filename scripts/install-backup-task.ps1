param(
  [Parameter(Mandatory=$true)][string]$SecretsRunner,
  [string]$RunnerRoot = "$env:LOCALAPPDATA\mvvm\backup-runner",
  [string]$BackupRoot = "$env:LOCALAPPDATA\mvvm\backups"
)
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$node = (Get-Command node -ErrorAction Stop).Source
$bun = (Get-Command bun -ErrorAction Stop).Source
$nodeMajor = & $node -p 'process.versions.node.split(".")[0]'
if ($LASTEXITCODE -ne 0 -or [int]$nodeMajor -lt 24) { throw 'Node 24 or newer is required' }
. (Join-Path $PSScriptRoot 'private-backup-directory.ps1')
foreach ($path in @($RunnerRoot,$BackupRoot,$SecretsRunner)) {
  if (-not [IO.Path]::IsPathFullyQualified($path)) { throw 'Absolute paths required' }
}
if (-not (Test-Path -LiteralPath $SecretsRunner -PathType Leaf)) { throw 'Secret runner is absent' }
if (Get-ScheduledTask -TaskPath '\MVVM\' -TaskName 'Verified backup' -ErrorAction SilentlyContinue) { throw 'Inspect the existing task before replacing it' }
if (Test-Path -LiteralPath $RunnerRoot) { throw 'Use an empty runner destination' }
foreach ($path in @($RunnerRoot,$BackupRoot)) {
  Set-PrivateBackupDirectory $path
}
New-Item -ItemType Directory -Path (Join-Path $RunnerRoot 'scripts') | Out-Null
foreach ($name in @('backup-convex-live.mjs','convex-backup.mjs','run-scheduled-backup.mjs')) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $RunnerRoot "scripts\$name")
}
foreach ($name in @('package.json','bun.lock')) {
  Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $RunnerRoot
}
Push-Location $RunnerRoot
try {
  & $bun install --production --frozen-lockfile
  if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
} finally { Pop-Location }
@{secretsRunner=$SecretsRunner;backupRoot=$BackupRoot} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $RunnerRoot 'backup-config.json')
$action = New-ScheduledTaskAction -Execute $node -Argument ('"' + (Join-Path $RunnerRoot 'scripts\run-scheduled-backup.mjs') + '"') -WorkingDirectory $RunnerRoot
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$triggers = @((New-ScheduledTaskTrigger -Daily -At '03:00'),(New-ScheduledTaskTrigger -AtLogOn -User $identity))
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskPath '\MVVM\' -TaskName 'Verified backup' -Action $action -Trigger $triggers -Principal $principal -Settings $settings -Description 'Private MVVM archive on this workstation; live BWS credentials, checksum verification, no automatic deletion.' | Select-Object TaskPath,TaskName,State
