#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [string]$ManifestPath = 'results/results-manifest.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'project_paths.ps1')

# Intentionally read-only: do not create directories, repair entries, or refreeze.
$root = Get-SafeProjectRoot -Path $ProjectRoot
$manifestFile = Resolve-ProjectArtifact -Root $root -RelativePath $ManifestPath -MustExist
$manifest = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($null -eq $manifest.PSObject.Properties['schema_version'] -or [string]$manifest.schema_version -ne '1.0.0') {
    throw 'Unsupported or missing results-manifest schema_version.'
}
if ($null -eq $manifest.PSObject.Properties['entries'] -or @($manifest.entries).Count -eq 0 -or $null -eq $manifest.entries) {
    throw 'A results manifest must contain at least one artifact entry.'
}
$comparer = if ($IsWindows) { [StringComparer]::OrdinalIgnoreCase } else { [StringComparer]::Ordinal }
$seen = [Collections.Generic.HashSet[string]]::new($comparer)
$failures = [Collections.Generic.List[string]]::new()
foreach ($entry in @($manifest.entries)) {
    foreach ($field in @('path', 'sha256', 'bytes')) {
        if ($null -eq $entry -or $null -eq $entry.PSObject.Properties[$field]) { throw "Manifest entry missing field: $field" }
    }
    $path = [string]$entry.path
    $file = Resolve-ProjectArtifact -Root $root -RelativePath $path
    if (-not $seen.Add($file)) { throw "Duplicate artifact: $path" }
    if ($file -eq $manifestFile) { throw 'A manifest cannot verify itself.' }
    if ([string]$entry.sha256 -notmatch '^[A-Fa-f0-9]{64}$') { throw "Invalid SHA-256 for artifact: $path" }
    $expectedBytes = 0L
    if (-not [long]::TryParse([string]$entry.bytes, [ref]$expectedBytes) -or $expectedBytes -lt 0) {
        throw "Invalid artifact byte count: $path"
    }
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { $failures.Add("MISSING $path"); continue }
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne [string]$entry.sha256) {
        $failures.Add("HASH_MISMATCH $path")
    }
    if ((Get-Item -LiteralPath $file).Length -ne $expectedBytes) { $failures.Add("SIZE_MISMATCH $path") }
}
foreach ($failure in $failures) { Write-Output $failure }
Write-Output "VERIFIED_ENTRIES=$($seen.Count)"
Write-Output 'CHECK_SCOPE=manifest_structure_path_size_and_hash_only'
if ($failures.Count -gt 0) { Write-Output 'RESULT_FREEZE_STATUS=FAIL'; exit 1 }
Write-Output 'RESULT_FREEZE_STATUS=PASS'
exit 0
