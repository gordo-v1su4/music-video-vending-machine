function Set-PrivateBackupDirectory([string]$Path) {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
  New-Item -ItemType Directory -Force -Path $Path | Out-Null
  $items = @((Get-Item -LiteralPath $Path)) + @(Get-ChildItem -LiteralPath $Path -Recurse -Force)
  # Refuse links before changing permissions anywhere in this tree.
  foreach ($item in $items) {
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked destinations are not allowed' }
  }
  foreach ($item in $items) {
    if ($item.PSIsContainer) {
      $acl = [Security.AccessControl.DirectorySecurity]::new()
      $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
    } else {
      $acl = [Security.AccessControl.FileSecurity]::new()
      $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','Allow')
    }
    $acl.SetOwner($identity)
    $acl.SetAccessRuleProtection($true,$false)
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $item.FullName -AclObject $acl
  }
}
