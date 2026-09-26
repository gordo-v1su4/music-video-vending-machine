function Set-PrivateBackupDirectory([string]$Path) {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
  New-Item -ItemType Directory -Force -Path $Path | Out-Null
  $items = @((Get-Item -LiteralPath $Path)) + @(Get-ChildItem -LiteralPath $Path -Recurse -Force)
  # Refuse links before changing permissions anywhere in this tree.
  foreach ($item in $items) {
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked destinations are not allowed' }
    if ((Get-Acl -LiteralPath $item.FullName).GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $identity.Value) { throw 'Backup paths must be owned by the current user' }
  }
  foreach ($item in $items) {
    # Modify only the DACL. A fresh descriptor can request SACL/owner writes
    # requiring SeSecurityPrivilege on existing files even when we own them.
    $acl = Get-Acl -LiteralPath $item.FullName
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($existing in @($acl.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))) {
      $acl.RemoveAccessRuleSpecific($existing)
    }
    if ($item.PSIsContainer) {
      $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
    } else {
      $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','Allow')
    }
    $acl.AddAccessRule($rule)
    [IO.FileSystemAclExtensions]::SetAccessControl($item,$acl)
  }
}
