<#
.SYNOPSIS
PyKaraoke NG — build script for Windows (PowerShell).
.DESCRIPTION
Builds, tests, and packages the native Rust desktop app without Python.
.EXAMPLE
.\build.ps1 -Target Build
.\build.ps1 -Target Test
.\build.ps1 -Target Run
#>

param(
    [ValidateSet("Build", "BuildEngine", "Clean", "CleanEngine", "CleanAll",
                  "Install", "Uninstall", "Test", "TestRust", "TestJs",
                  "Run", "Dist", "Help")]
    [string]$Target = "Help"
)

$TAURI_DIR    = "src\runtimes\tauri"
$TAURI_SRC    = "$TAURI_DIR\src-tauri"
$ENGINE_DIR   = "crates\pykaraoke-engine"
$BINARY_NAME  = "PyKaraoke NG"
$BINARY       = "$TAURI_SRC\target\release\$BINARY_NAME.exe"
$MSI          = "$TAURI_SRC\target\release\bundle\msi\$BINARY_NAME`_0.7.5_x64_en-US.msi"
$NSIS         = "$TAURI_SRC\target\release\bundle\nsis\$BINARY_NAME`_0.7.5_x64-setup.exe"

function Invoke-Build {
    Write-Host "=== Building Tauri desktop app ===" -ForegroundColor Cyan
    Push-Location $TAURI_DIR
    try {
        npx @tauri-apps/cli@1 build
        if ($LASTEXITCODE -ne 0) { throw "Tauri build failed" }
        Write-Host "Build successful!" -ForegroundColor Green
        Write-Host "  Binary: $BINARY" -ForegroundColor Gray
        Write-Host "  MSI:    $MSI" -ForegroundColor Gray
        Write-Host "  NSIS:   $NSIS" -ForegroundColor Gray
    } finally {
        Pop-Location
    }
}

function Invoke-BuildEngine {
    Write-Host "=== Building Rust engine crate ===" -ForegroundColor Cyan
    cargo build --release --manifest-path "$ENGINE_DIR\Cargo.toml"
    if ($LASTEXITCODE -ne 0) { throw "Engine build failed" }
}

function Invoke-Clean {
    Write-Host "=== Cleaning Tauri build artifacts ===" -ForegroundColor Yellow
    Push-Location $TAURI_SRC
    try { cargo clean } finally { Pop-Location }
    Remove-Item -Recurse -Force "$TAURI_DIR\node_modules\.cache" -ErrorAction SilentlyContinue
}

function Invoke-CleanEngine {
    Write-Host "=== Cleaning engine crate artifacts ===" -ForegroundColor Yellow
    Push-Location $ENGINE_DIR
    try { cargo clean } finally { Pop-Location }
}

function Invoke-CleanAll {
    Invoke-Clean
    Invoke-CleanEngine
}

function Invoke-Install {
    if (-not (Test-Path $MSI) -and -not (Test-Path $NSIS)) {
        Write-Host "No installer found — building first..." -ForegroundColor Yellow
        Invoke-Build
    }
    if (Test-Path $MSI) {
        Write-Host "=== Installing via MSI ===" -ForegroundColor Cyan
        Start-Process -Wait -FilePath $MSI
    } elseif (Test-Path $NSIS) {
        Write-Host "=== Installing via NSIS ===" -ForegroundColor Cyan
        Start-Process -Wait -FilePath $NSIS
    } else {
        Write-Host "Build completed but no installer was produced." -ForegroundColor Red
        exit 1
    }
}

function Invoke-Uninstall {
    Write-Host 'Uninstall via: Settings > Apps > PyKaraoke NG' -ForegroundColor Yellow
}

function Invoke-Test {
    Invoke-TestRust
    Invoke-TestJs
}

function Invoke-TestRust {
    Write-Host "=== Running Rust engine tests ===" -ForegroundColor Cyan
    cargo test --release --manifest-path "$ENGINE_DIR\Cargo.toml"
    if ($LASTEXITCODE -ne 0) { throw "Rust tests failed" }
}

function Invoke-TestJs {
    Write-Host "=== Running frontend JS tests ===" -ForegroundColor Cyan
    node "$TAURI_DIR\src\app.test.js"
    if ($LASTEXITCODE -ne 0) { throw "JS tests failed" }
}

function Invoke-Run {
    Write-Host "=== Launching app in dev mode ===" -ForegroundColor Cyan
    Push-Location $TAURI_DIR
    try {
        npx @tauri-apps/cli@1 dev
    } finally {
        Pop-Location
    }
}

function Invoke-Dist {
    if (-not (Test-Path $BINARY)) {
        Write-Host "No build artifacts found — building first..." -ForegroundColor Yellow
        Invoke-Build
    }
    if (Test-Path $BINARY) {
        Write-Host "=== Distribution bundles ===" -ForegroundColor Cyan
        Write-Host "  Binary: $BINARY"
        Write-Host "  MSI:    $MSI"
        Write-Host "  NSIS:   $NSIS"
    } else {
        Write-Host "Build completed but no binary was produced." -ForegroundColor Yellow
    }
}

function Show-Help {
    Write-Host @"
PyKaraoke NG — build.ps1

  Targets:
    Build         Build the Tauri desktop app (Rust engine + frontend)
    BuildEngine   Build only the Rust engine crate (faster)
    Clean         Clean Tauri build artifacts
    CleanEngine   Clean engine crate artifacts
    CleanAll      Clean all build artifacts
    Install       Install via platform installer (MSI/NSIS)
    Uninstall     Instructions for uninstalling
    Test          Run all tests (Rust engine + frontend JS)
    TestRust      Run Rust engine tests only
    TestJs        Run frontend JS tests only
    Run           Launch app in development mode
    Dist          Show built distribution bundles
    Help          Show this message (default)

  Examples:
    .\build.ps1 -Target Build
    .\build.ps1 -Target Test
    .\build.ps1 -Target Run

"@ -ForegroundColor Cyan
}

# ── Dispatch ─────────────────────────────────────────────────────────────

switch ($Target) {
    "Build"        { Invoke-Build }
    "BuildEngine"  { Invoke-BuildEngine }
    "Clean"        { Invoke-Clean }
    "CleanEngine"  { Invoke-CleanEngine }
    "CleanAll"     { Invoke-CleanAll }
    "Install"      { Invoke-Install }
    "Uninstall"    { Invoke-Uninstall }
    "Test"         { Invoke-Test }
    "TestRust"     { Invoke-TestRust }
    "TestJs"       { Invoke-TestJs }
    "Run"          { Invoke-Run }
    "Dist"         { Invoke-Dist }
    "Help"         { Show-Help }
}
