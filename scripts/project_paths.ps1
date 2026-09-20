# Shared local path checks. No network access or file writes.
Set-StrictMode -Version Latest

function Assert-NoReparsePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $cursor = [IO.Path]::GetFullPath($Path)
    while (-not [string]::IsNullOrWhiteSpace($cursor)) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Refusing a symlink or reparse-point path: $cursor"
            }
        }
        $parent = [IO.Path]::GetDirectoryName($cursor)
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}

function Get-SafeProjectRoot {
    param([Parameter(Mandatory = $true)][string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    Assert-NoReparsePath -Path $full
    if (-not (Test-Path -LiteralPath $full -PathType Container)) { throw "Project directory not found: $full" }
    if ($full.TrimEnd('\', '/') -eq ([IO.Path]::GetPathRoot($full)).TrimEnd('\', '/')) {
        throw 'A filesystem root cannot be a modeling project.'
    }
    return $full.TrimEnd('\', '/')
}

function Resolve-ProjectArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [switch]$MustExist
    )
    if ([string]::IsNullOrWhiteSpace($RelativePath) -or [IO.Path]::IsPathRooted($RelativePath) -or
        $RelativePath -match '[:\x00-\x1f]' -or $RelativePath -match '(^|[/\\])\.\.([/\\]|$)') {
        throw "Artifact path must be a project-relative path without traversal: $RelativePath"
    }
    $normalized = $RelativePath.Replace('\', [IO.Path]::DirectorySeparatorChar).Replace('/', [IO.Path]::DirectorySeparatorChar)
    $full = [IO.Path]::GetFullPath((Join-Path $Root $normalized))
    $prefix = $Root.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    $comparison = if ($IsWindows) { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
    if (-not $full.StartsWith($prefix, $comparison)) { throw "Artifact escapes project: $RelativePath" }
    Assert-NoReparsePath -Path $full
    if ($MustExist -and -not (Test-Path -LiteralPath $full -PathType Leaf)) {
        throw "Artifact file not found: $RelativePath"
    }
    return $full
}
