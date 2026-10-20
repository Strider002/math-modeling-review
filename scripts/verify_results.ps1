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
$raw = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8
if (-not $raw.TrimStart().StartsWith('{')) { throw 'Manifest must be a JSON object.' }
$manifest = $raw | ConvertFrom-Json
if ($manifest -isnot [pscustomobject]) { throw 'Manifest must be a JSON object.' }
function Test-Timestamp {
    param($Value)
    if ($Value -is [datetime] -or $Value -is [DateTimeOffset]) { return $true }
    if ($Value -isnot [string] -or [string]::IsNullOrWhiteSpace($Value)) { return $false }
    $parsed = [DateTimeOffset]::MinValue
    return [DateTimeOffset]::TryParse($Value, [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::None, [ref]$parsed)
}
foreach ($field in @('schema_version', 'frozen_at', 'source_commit', 'entries')) {
    if ($null -eq $manifest.PSObject.Properties[$field]) { throw "Missing manifest field: $field" }
}
if ($manifest.schema_version -isnot [string] -or $manifest.schema_version -ne '1.0.0') {
    throw 'Unsupported or missing results-manifest schema_version.'
}
if (-not (Test-Timestamp $manifest.frozen_at)) { throw 'Invalid frozen_at.' }
if ($null -ne $manifest.source_commit -and
    ($manifest.source_commit -isnot [string] -or $manifest.source_commit -notmatch '\A(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\z')) { throw 'Invalid source_commit.' }
if ($manifest.entries -isnot [array] -or $manifest.entries.Count -eq 0) {
    throw 'A results manifest must contain at least one artifact entry.'
}
$comparer = if ($IsWindows) { [StringComparer]::OrdinalIgnoreCase } else { [StringComparer]::Ordinal }
$seen = [Collections.Generic.HashSet[string]]::new($comparer)
$failures = [Collections.Generic.List[string]]::new()
$verified = 0
foreach ($entry in @($manifest.entries)) {
    if ($entry -isnot [pscustomobject]) { throw 'Entry must be an object.' }
    foreach ($field in @('path', 'sha256', 'bytes', 'last_write_utc')) {
        if ($null -eq $entry -or $null -eq $entry.PSObject.Properties[$field]) { throw "Manifest entry missing field: $field" }
    }
    if ($entry.path -isnot [string] -or [string]::IsNullOrWhiteSpace($entry.path)) { throw 'Invalid path.' }
    if (-not (Test-Timestamp $entry.last_write_utc)) { throw 'Invalid last_write_utc.' }
    $path = $entry.path
    $file = Resolve-ProjectArtifact -Root $root -RelativePath $path
    if (-not $seen.Add($file)) { throw "Duplicate artifact: $path" }
    if ($file -eq $manifestFile) { throw 'A manifest cannot verify itself.' }
    if ($entry.sha256 -isnot [string] -or $entry.sha256 -notmatch '\A[A-Fa-f0-9]{64}\z') { throw "Invalid SHA-256 for artifact: $path" }
    if (($entry.bytes -isnot [int] -and $entry.bytes -isnot [long]) -or $entry.bytes -lt 0) {
        throw "Invalid artifact byte count: $path"
    }
    $expectedBytes = $entry.bytes
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { $failures.Add("MISSING $path"); continue }
    $before = $failures.Count
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne [string]$entry.sha256) {
        $failures.Add("HASH_MISMATCH $path")
    }
    if ((Get-Item -LiteralPath $file).Length -ne $expectedBytes) { $failures.Add("SIZE_MISMATCH $path") }
    if ($failures.Count -eq $before) { $verified++ }
}
foreach ($failure in $failures) { Write-Output $failure }
Write-Output "VERIFIED_ENTRIES=$verified"
Write-Output 'CHECK_SCOPE=manifest_structure_path_size_and_hash_only'
if ($failures.Count -gt 0) { Write-Output 'RESULT_FREEZE_STATUS=FAIL'; exit 1 }
Write-Output 'RESULT_FREEZE_STATUS=PASS'
exit 0
