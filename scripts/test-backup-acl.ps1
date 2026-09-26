$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'private-backup-directory.ps1')
$root = Join-Path ([IO.Path]::GetTempPath()) ('mvvm-acl-test-' + [guid]::NewGuid())
$nested = Join-Path $root 'archive'
New-Item -ItemType Directory -Path $nested -Force | Out-Null
$file = Join-Path $nested 'snapshot.json'
'synthetic fixture' | Set-Content -LiteralPath $file
$operator = [Security.Principal.WindowsIdentity]::GetCurrent().User
# Hosted Windows runners may default new files to Administrators ownership.
# Prepare operator-owned inputs, matching the installer's explicit contract.
foreach ($path in @($root,$nested,$file)) {
  $entry = Get-Item -LiteralPath $path
  $acl = Get-Acl -LiteralPath $path
  $acl.SetOwner($operator)
  [IO.FileSystemAclExtensions]::SetAccessControl($entry,$acl)
}
$everyone = [Security.Principal.SecurityIdentifier]::new('S-1-1-0')
foreach ($path in @($root,$file)) {
  $acl = Get-Acl -LiteralPath $path
  $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($everyone,'Read','Allow'))
  Set-Acl -LiteralPath $path -AclObject $acl
}
$owners = @{}
foreach ($path in @($root,$nested,$file)) {
  $owners[$path] = (Get-Acl -LiteralPath $path).GetOwner([Security.Principal.SecurityIdentifier]).Value
}
$auditSupported = $false
try {
  $audit = Get-Acl -LiteralPath $file -Audit
  $audit.AddAuditRule([Security.AccessControl.FileSystemAuditRule]::new($operator,'Write','Success'))
  [IO.FileSystemAclExtensions]::SetAccessControl((Get-Item -LiteralPath $file),$audit)
  $auditBefore = (Get-Acl -LiteralPath $file -Audit).GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Audit)
  $auditSupported = $true
} catch {
  if ($_.Exception.ToString() -notmatch 'SeSecurityPrivilege|PrivilegeNotHeld|privilege') { throw }
  'Audit preservation case skipped: this process lacks the Windows audit privilege.'
}
Set-PrivateBackupDirectory $root
Set-PrivateBackupDirectory $root
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
foreach ($path in @($root,$nested,$file)) {
  $acl = Get-Acl -LiteralPath $path
  if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $owners[$path]) { throw 'Owner metadata changed' }
  if (-not $acl.AreAccessRulesProtected) { throw 'Inheritance is still enabled' }
  $rules = @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
  if ($rules.Count -ne 1 -or $rules[0].IdentityReference.Value -ne $sid -or $rules[0].AccessControlType -ne 'Allow') { throw 'Unexpected access remains' }
}
if ($auditSupported) {
  $auditAfter = (Get-Acl -LiteralPath $file -Audit).GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Audit)
  if ($auditAfter -ne $auditBefore) { throw 'Audit metadata changed' }
  'Existing audit rule preserved.'
}
if ((Get-Content -LiteralPath $file) -ne 'synthetic fixture') { throw 'File contents changed' }
'Private ACL test passed for existing directory and child explicit grants.'
