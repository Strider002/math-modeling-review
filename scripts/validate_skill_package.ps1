#Requires -Version 7.0
[CmdletBinding()]
param(
    [string]$SkillRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$PrivateDenyListPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($SkillRoot).TrimEnd('\', '/')
$prefix = $root + [IO.Path]::DirectorySeparatorChar
$errors = [Collections.Generic.List[string]]::new()
$files = [Collections.Generic.List[object]]::new()
$stack = [Collections.Generic.Stack[string]]::new()
$stack.Push($root)
if (((Get-Item -LiteralPath $root -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'The package root must be a real directory, not a directory link.'
}
while ($stack.Count -gt 0) {
    foreach ($item in Get-ChildItem -LiteralPath ($stack.Pop()) -Force) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            $errors.Add("REPARSE_POINT $($item.FullName)"); continue
        }
        if ($item.PSIsContainer) {
            if ($item.Name -in @('.git', '__pycache__', 'node_modules', '.venv')) { $errors.Add("UNWANTED_DIRECTORY $($item.Name)") }
            else { $stack.Push($item.FullName) }
        } else { $files.Add($item) }
    }
}
$denied = @()
if ($PrivateDenyListPath) {
    $denied = @(Get-Content -LiteralPath $PrivateDenyListPath -Encoding UTF8 | Where-Object { $_ -ne '' })
}
$texts = @{}
$localLinks = 0
foreach ($file in $files) {
    $relative = [IO.Path]::GetRelativePath($root, $file.FullName).Replace('\', '/')
    if ($file.Length -eq 0) { $errors.Add("EMPTY_FILE $relative") }
    if ($file.Extension -notin @('.md','.json','.yaml','.yml','.ps1','.py','.cff') -and $file.Name -notin @('LICENSE','LICENSE-DOCS')) {
        $errors.Add("UNEXPECTED_FILE_TYPE $relative"); continue
    }
    $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    $texts[$relative] = $content
    foreach ($term in $denied) {
        if ($content.IndexOf($term, [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            $relative.IndexOf($term, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
            $errors.Add("PRIVATE_DENYLIST_MATCH $relative"); break
        }
    }
    if ($file.Extension -eq '.json' -or $file.Name -eq 'routing-manifest.yaml') {
        try { $null = $content | ConvertFrom-Json } catch { $errors.Add("INVALID_JSON $relative") }
    }
    if ($file.Extension -ne '.md') { continue }
    if ([regex]::Matches($content, '(?m)^# ').Count -ne 1) { $errors.Add("H1_COUNT $relative") }
    if ([regex]::Matches($content, '(?m)^```').Count % 2 -ne 0) { $errors.Add("CODE_FENCE $relative") }
    if ($content -match '(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|file://)') { $errors.Add("PERSONAL_ABSOLUTE_PATH $relative") }
    foreach ($match in [regex]::Matches($content, '\[[^\]\r\n]+\]\(([^\)\r\n]+)\)')) {
        $target = $match.Groups[1].Value.Trim('<','>')
        if ($target -match '^(https?://|mailto:|#)') { continue }
        $target = [Uri]::UnescapeDataString($target.Split('#')[0])
        if ([IO.Path]::IsPathRooted($target)) { $errors.Add("ABSOLUTE_LINK $relative"); continue }
        $full = [IO.Path]::GetFullPath((Join-Path $file.DirectoryName $target))
        if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            $errors.Add("LINK_OUTSIDE_PACKAGE $relative -> $target")
        } elseif (-not (Test-Path -LiteralPath $full)) { $errors.Add("MISSING_LINK_TARGET $relative -> $target") }
        $localLinks++
    }
}
foreach ($name in @('SKILL.md','AGENTS.md','agents/openai.yaml','LICENSE','LICENSE-DOCS','LICENSES.md')) {
    if (-not $texts.ContainsKey($name)) { $errors.Add("REQUIRED_FILE $name") }
}
if ($texts.ContainsKey('SKILL.md')) {
    $expectedName = Split-Path -Leaf $root
    if ($texts['SKILL.md'] -notmatch '(?s)^---\r?\n(.*?)\r?\n---') { $errors.Add('SKILL_FRONTMATTER') }
    elseif ($Matches[1] -notmatch '(?m)^name:\s*([a-z0-9-]+)\s*$' -or $Matches[1] -ne $expectedName) {
        $errors.Add('SKILL_NAME')
    }
}
if ($texts.ContainsKey('routing-manifest.yaml')) {
    $manifest = $texts['routing-manifest.yaml'] | ConvertFrom-Json
    foreach ($match in [regex]::Matches($texts['routing-manifest.yaml'], '"path"\s*:\s*"([^"]+)"')) {
        $path = $match.Groups[1].Value
        if ([IO.Path]::IsPathRooted($path) -or $path -match '(^|[/\\])\.\.([/\\]|$)') { $errors.Add("UNSAFE_ROUTE_PATH $path"); continue }
        if (-not (Test-Path -LiteralPath (Join-Path $root $path))) { $errors.Add("MISSING_ROUTE_RESOURCE $path") }
    }
    foreach ($group in @($manifest.routes | Group-Object id | Where-Object Count -gt 1)) { $errors.Add("DUPLICATE_ROUTE $($group.Name)") }
}
$sourceIndexKey = 'references/来源依据/来源索引.md'
if ($texts.ContainsKey($sourceIndexKey)) {
    $ids = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($match in [regex]::Matches($texts[$sourceIndexKey], '(?m)^\|\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*\|')) {
        $null = $ids.Add($match.Groups[1].Value)
    }
    foreach ($entry in $texts.GetEnumerator()) {
        if (-not $entry.Key.EndsWith('.md')) { continue }
        foreach ($match in [regex]::Matches($entry.Value, 'source:([A-Za-z0-9][A-Za-z0-9._-]*)')) {
            if (-not $ids.Contains($match.Groups[1].Value)) { $errors.Add("UNBOUND_SOURCE $($entry.Key) id=$($match.Groups[1].Value)") }
        }
    }
}
foreach ($file in $files | Where-Object Name -eq 'claims_registry.json') {
    $claims = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($claim in $claims.entries) {
        foreach ($location in $claim.locations) {
            $path = ([string]$location).Split('#')[0]
            if (-not $texts.ContainsKey($path)) { $errors.Add("MISSING_CLAIM_LOCATION $($claim.claim_id)"); continue }
            $bound = $false
            foreach ($evidence in $claim.evidence) {
                if ($texts[$path].Contains('source:' + [string]$evidence.source_id)) { $bound = $true }
            }
            if (-not $bound) { $errors.Add("UNBOUND_CLAIM_LOCATION $($claim.claim_id)") }
        }
    }
}
Write-Output "PACKAGE_FILES=$($files.Count)"
Write-Output "LOCAL_LINK_TARGETS_CHECKED=$localLinks"
Write-Output 'CHECK_SCOPE=package_structure_local_file_targets_route_paths_source_bindings_and_optional_private_terms'
Write-Output "ERRORS=$($errors.Count)"
foreach ($item in $errors) { Write-Output "ERROR $item" }
if ($errors.Count -gt 0) { Write-Output 'PACKAGE_STATUS=FAIL'; exit 1 }
Write-Output 'PACKAGE_STATUS=PASS'
exit 0
