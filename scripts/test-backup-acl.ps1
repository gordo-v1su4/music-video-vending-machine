$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'private-backup-directory.ps1')
$root = Join-Path ([IO.Path]::GetTempPath()) ('mvvm-acl-test-' + [guid]::NewGuid())
$nested = Join-Path $root 'archive'
New-Item -ItemType Directory -Path $nested -Force | Out-Null
$file = Join-Path $nested 'snapshot.json'
'synthetic fixture' | Set-Content -LiteralPath $file
$everyone = [Security.Principal.SecurityIdentifier]::new('S-1-1-0')
foreach ($path in @($root,$file)) {
  $acl = Get-Acl -LiteralPath $path
  $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($everyone,'Read','Allow'))
  Set-Acl -LiteralPath $path -AclObject $acl
}
Set-PrivateBackupDirectory $root
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
foreach ($path in @($root,$nested,$file)) {
  $acl = Get-Acl -LiteralPath $path
  if (-not $acl.AreAccessRulesProtected) { throw 'Inheritance is still enabled' }
  $rules = @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
  if ($rules.Count -ne 1 -or $rules[0].IdentityReference.Value -ne $sid -or $rules[0].AccessControlType -ne 'Allow') { throw 'Unexpected access remains' }
}
if ((Get-Content -LiteralPath $file) -ne 'synthetic fixture') { throw 'File contents changed' }
'Private ACL test passed for existing directory and child explicit grants.'
