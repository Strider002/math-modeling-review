#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PaperPath,
    [ValidateSet('CUMCM', 'MCM-ICM', 'Generic')][string]$Profile = 'Generic',
    [string]$ControlNumber,
    [string]$DenyListPath,
    [ValidateSet('Unspecified', 'NotUsed', 'Used')][string]$CumcmAiUse = 'Unspecified',
    [string]$AiDetailsPath,
    [switch]$RequireTextExtraction
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()
$paper = (Resolve-Path -LiteralPath $PaperPath).Path
$item = Get-Item -LiteralPath $paper
if ($item.Extension -ne '.pdf') { $errors.Add('PAPER_EXTENSION expected=.pdf') }
$stream = [IO.File]::OpenRead($paper)
try {
    $buffer = New-Object byte[] 5
    $count = $stream.Read($buffer, 0, 5)
    $magic = if ($count -eq 5) { [Text.Encoding]::ASCII.GetString($buffer) } else { '' }
    if ($magic -ne '%PDF-') { $errors.Add('PAPER_MAGIC invalid_pdf_header') }
} finally { $stream.Dispose() }

$limit = switch ($Profile) { 'CUMCM' { 20000000 } 'MCM-ICM' { 25000000 } default { 0 } }
if ($limit -gt 0 -and ($item.Length -gt $limit -or ($Profile -eq 'MCM-ICM' -and $item.Length -eq $limit))) { $errors.Add("PAPER_SIZE bytes=$($item.Length) limit=$limit") }
if ($Profile -eq 'MCM-ICM') {
    if ([string]::IsNullOrWhiteSpace($ControlNumber)) {
        $errors.Add('CONTROL_NUMBER required_for_mcm_icm')
    } elseif ($item.BaseName -ne $ControlNumber) {
        $errors.Add("PAPER_FILENAME expected=$ControlNumber.pdf actual=$($item.Name)")
    }
}
if ($Profile -eq 'CUMCM') {
    if ($CumcmAiUse -eq 'Unspecified') {
        $errors.Add('CUMCM_AI_USE_STATUS required_values=NotUsed_or_Used')
    } elseif ($CumcmAiUse -eq 'Used') {
        if ([string]::IsNullOrWhiteSpace($AiDetailsPath)) {
            $errors.Add('CUMCM_AI_DETAILS required_when_ai_used')
        } elseif (-not (Test-Path -LiteralPath $AiDetailsPath -PathType Leaf)) {
            $errors.Add("CUMCM_AI_DETAILS missing=$AiDetailsPath")
        } else {
            $aiDetails = Get-Item -LiteralPath $AiDetailsPath
            if ($aiDetails.Name -cne 'AI工具使用详情.pdf') {
                $errors.Add("CUMCM_AI_DETAILS_FILENAME expected=AI工具使用详情.pdf actual=$($aiDetails.Name)")
            }
            $detailsStream = [IO.File]::OpenRead($aiDetails.FullName)
            try {
                $detailsBuffer = New-Object byte[] 5
                $detailsCount = $detailsStream.Read($detailsBuffer, 0, 5)
                $detailsMagic = if ($detailsCount -eq 5) { [Text.Encoding]::ASCII.GetString($detailsBuffer) } else { '' }
                if ($detailsMagic -ne '%PDF-') { $errors.Add('CUMCM_AI_DETAILS invalid_pdf_header') }
            } finally { $detailsStream.Dispose() }
        }
    } elseif (-not [string]::IsNullOrWhiteSpace($AiDetailsPath)) {
        $errors.Add('CUMCM_AI_DETAILS inconsistent_with_not_used')
    }
}

$pdfInfo = Get-Command pdfinfo -ErrorAction SilentlyContinue
if ($null -ne $pdfInfo) {
    $infoOutput = @(& $pdfInfo.Source $paper 2>&1)
    if ($LASTEXITCODE -ne 0) { $errors.Add('PDFINFO failed') }
    $pageLine = $infoOutput | Where-Object { $_ -match '^Pages:\s+(\d+)' } | Select-Object -First 1
    if ($null -ne $pageLine -and $pageLine -match '^Pages:\s+(\d+)') {
        $pages = [int]$Matches[1]
        Write-Output "PDF_PAGES=$pages"
        if ($Profile -eq 'CUMCM' -and $pages -gt 31) { $warnings.Add("CUMCM_PAGE_REVIEW pages=$pages includes_summary_and_possible_appendices") }
        if ($Profile -eq 'MCM-ICM' -and $pages -gt 25) { $warnings.Add("MCM_PAGE_REVIEW pages=$pages AI_report_may_be_outside_limit") }
    }
} else {
    $warnings.Add('PDFINFO unavailable_page_count_not_checked')
}

$denyTerms = @()
if (-not [string]::IsNullOrWhiteSpace($DenyListPath)) {
    $denyPath = (Resolve-Path -LiteralPath $DenyListPath).Path
    $denyTerms = @(Get-Content -LiteralPath $denyPath -Encoding UTF8 | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' -and -not $_.StartsWith('#') })
}
foreach ($term in $denyTerms) {
    if ($item.Name.IndexOf($term, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
        $errors.Add('ANONYMITY_FILENAME matched_private_term')
    }
}
$pdftotext = Get-Command pdftotext -ErrorAction SilentlyContinue
if ($denyTerms.Count -gt 0 -or $RequireTextExtraction) {
    if ($null -eq $pdftotext) {
        $errors.Add('PDFTOTEXT required_for_requested_text_or_denylist_check_but_unavailable')
    } else {
        $textLines = @(& $pdftotext.Source -enc UTF-8 $paper - 2>&1)
        if ($LASTEXITCODE -ne 0) {
            $errors.Add('PDFTOTEXT failed')
        } else {
            $text = $textLines -join "`n"
            foreach ($term in $denyTerms) {
                if ($text.IndexOf($term, [StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                    $item.Name.IndexOf($term, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
                    $errors.Add('ANONYMITY_DENYLIST matched_private_term')
                }
            }
        }
    }
}

Write-Output 'CHECK_SCOPE=mechanical_pdf_precheck_only; manual_rules_anonymity_and_scientific_review_required'
Write-Output 'RULE_SNAPSHOT=CUMCM_2026_MCM_ICM_2027; byte_limits_use_conservative_decimal_MB'
Write-Output "PAPER_BYTES=$($item.Length)"
Write-Output "PROFILE=$Profile"
if ($Profile -eq 'CUMCM') { Write-Output "CUMCM_AI_USE=$CumcmAiUse" }
Write-Output "WARNINGS=$($warnings.Count)"
foreach ($warning in $warnings) { Write-Output "WARNING $warning" }
Write-Output "ERRORS=$($errors.Count)"
foreach ($errorItem in $errors) { Write-Output "ERROR $errorItem" }
if ($errors.Count -gt 0) { Write-Output 'SUBMISSION_VALIDATION_STATUS=FAIL'; exit 1 }
Write-Output 'SUBMISSION_VALIDATION_STATUS=PASS'
exit 0
