#!/usr/bin/env pwsh
# specs/ci/Validate-SpecCompletion.ps1
#
# CI gate script (PowerShell): Validates that a feature branch has completed
# all Spec Kit workflow steps before merge is permitted.
#
# Usage:
#   .\specs\ci\Validate-SpecCompletion.ps1 [-BranchName "001-feature-name"]
#
# If -BranchName is omitted, uses the current Git branch.
#
# Exit codes:
#   0 — All validations pass
#   1 — Validation failure (blocks merge)

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$BranchName
)

$ErrorActionPreference = "Stop"
$SpecDir = "specs/features"

# ─── Step 1: Determine branch name ──────────────────────────────────────

if (-not $BranchName) {
    $BranchName = (git rev-parse --abbrev-ref HEAD).Trim()
}

if ($BranchName -in @("main", "master")) {
    Write-Host "✅ Branch is $BranchName — spec validation not required." -ForegroundColor Green
    exit 0
}

# ─── Step 2: Validate branch naming convention ──────────────────────────

if ($BranchName -notmatch '^\d{3}-.+') {
    Write-Host "❌ FAIL: Branch name '$BranchName' does not match required format: NNN-feature-name" -ForegroundColor Red
    Write-Host "   Example: 001-filename-parser-edge-cases"
    exit 1
}

Write-Host "✅ Branch name '$BranchName' follows NNN-feature-name convention." -ForegroundColor Green

$FeatureDir = Join-Path $SpecDir $BranchName

# ─── Step 3: Check that spec artifacts exist ─────────────────────────────

$RequiredFiles = @("spec.md", "clarify.md", "plan.md", "tasks.md", "checklist.md")
$Missing = 0

foreach ($file in $RequiredFiles) {
    $filePath = Join-Path $FeatureDir $file
    if (-not (Test-Path $filePath)) {
        Write-Host "❌ FAIL: Missing $filePath" -ForegroundColor Red
        $Missing++
    }
    else {
        Write-Host "✅ Found $filePath" -ForegroundColor Green
    }
}

if ($Missing -gt 0) {
    Write-Host ""
    Write-Host "❌ BLOCKED: Spec artifacts are incomplete. Complete the Spec Kit workflow:" -ForegroundColor Red
    Write-Host "   1. /speckit.specify  → spec.md"
    Write-Host "   2. /speckit.clarify  → clarify.md"
    Write-Host "   3. /speckit.plan     → plan.md"
    Write-Host "   4. /speckit.tasks    → tasks.md"
    Write-Host "   5. /speckit.checklist → checklist.md"
    exit 1
}

# ─── Step 4: Validate checklist completion ───────────────────────────────

$ChecklistPath = Join-Path $FeatureDir "checklist.md"
$Content = Get-Content $ChecklistPath -Raw
$Unchecked = ([regex]::Matches($Content, '^\- \[ \]', 'Multiline')).Count
$Checked = ([regex]::Matches($Content, '^\- \[x\]', 'Multiline')).Count
$Total = $Unchecked + $Checked

if ($Total -eq 0) {
    Write-Host "❌ FAIL: Checklist has no checkable items. Was it filled out?" -ForegroundColor Red
    exit 1
}

if ($Unchecked -gt 0) {
    Write-Host "❌ FAIL: Checklist has $Unchecked incomplete items out of $Total." -ForegroundColor Red
    Write-Host "   All checklist items must be checked before merge."
    exit 1
}

Write-Host "✅ Checklist complete: $Checked/$Total items checked." -ForegroundColor Green

# ─── Step 5: Validate commit message convention ─────────────────────────

$LastCommit = (git log -1 --pretty=format:"%s").Trim()
if ($LastCommit -notmatch '^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert|constitution)(\(.+\))?!?: .+') {
    Write-Host "⚠️  WARNING: Last commit does not follow Conventional Commits:" -ForegroundColor Yellow
    Write-Host "   `"$LastCommit`""
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ ALL SPEC VALIDATIONS PASSED for branch: $BranchName" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
exit 0
