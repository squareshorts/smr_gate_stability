# Reproducible Windows figure-rendering entry point.
# Public command:
#   powershell -ExecutionPolicy Bypass -File .\scripts\conjunctive_gate_stability\render_figures_windows.ps1
#
# This script:
#   1. locates Rscript.exe;
#   2. uses a repository-local R library;
#   3. installs/verifies ggplot2 and patchwork without treating normal R stderr as failure;
#   4. invokes only render_all_figures.R;
#   5. verifies every manifest-listed PDF and PNG;
#   6. writes logs and R session information;
#   7. returns a nonzero exit code on a real failure.

[CmdletBinding()]
param(
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $Here "..\..")).Path
}
else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

$RenderScript = Join-Path $Here "render_all_figures.R"
$ManifestPath = Join-Path $ProjectRoot "configs\conjunctive_gate_stability\final_figures.csv"
$FigureDir = Join-Path $ProjectRoot "results\conjunctive_gate_final\figures"
$LogDir = Join-Path $FigureDir "logs"
$EnvironmentDir = Join-Path $ProjectRoot "environments\r_figures"
$RLibrary = Join-Path $EnvironmentDir ".Rlib"

New-Item -ItemType Directory -Force -Path $FigureDir, $LogDir, $EnvironmentDir, $RLibrary | Out-Null

if (-not (Test-Path $RenderScript)) {
    throw "Missing render orchestrator: $RenderScript"
}

if (-not (Test-Path $ManifestPath)) {
    throw "Missing figure manifest: $ManifestPath"
}

# Locate Rscript.exe.
$Rscript = $null
$Command = Get-Command Rscript.exe -ErrorAction SilentlyContinue
if ($Command) {
    $Rscript = $Command.Source
}

if (-not $Rscript) {
    $Candidates = @(
        Get-ChildItem "C:\Program Files\R\R-*\bin\x64\Rscript.exe" -ErrorAction SilentlyContinue
        Get-ChildItem "C:\Program Files\R\R-*\bin\Rscript.exe" -ErrorAction SilentlyContinue
    ) | Sort-Object FullName -Descending

    if ($Candidates.Count -gt 0) {
        $Rscript = $Candidates[0].FullName
    }
}

if (-not $Rscript -or -not (Test-Path $Rscript)) {
    throw "Rscript.exe was not found. Install R or add Rscript.exe to PATH."
}

Write-Host "Using Rscript: $Rscript"
Write-Host "Project root: $ProjectRoot"

$env:R_FIG_LIB = $RLibrary
$env:R_LIBS_USER = $RLibrary
$env:CGS_PROJECT_ROOT = $ProjectRoot

function Invoke-RProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$StdoutPath,

        [Parameter(Mandatory = $true)]
        [string]$StderrPath,

        [Parameter(Mandatory = $true)]
        [string]$StepName
    )

    Remove-Item $StdoutPath, $StderrPath -Force -ErrorAction SilentlyContinue

    $Process = Start-Process `
        -FilePath $Rscript `
        -ArgumentList $Arguments `
        -Wait `
        -PassThru `
        -NoNewWindow `
        -RedirectStandardOutput $StdoutPath `
        -RedirectStandardError $StderrPath

    if (Test-Path $StdoutPath) {
        Get-Content $StdoutPath | ForEach-Object { Write-Host $_ }
    }

    if (Test-Path $StderrPath) {
        Get-Content $StderrPath | ForEach-Object { Write-Host $_ }
    }

    if ($Process.ExitCode -ne 0) {
        throw "$StepName failed with exit code $($Process.ExitCode). See $StdoutPath and $StderrPath."
    }
}

# Verify/install plotting packages in the repository-local library.
$PackageScript = Join-Path $EnvironmentDir "ensure_figure_packages.R"

@'
libp <- Sys.getenv("R_FIG_LIB")
if (!nzchar(libp)) stop("R_FIG_LIB is empty")

dir.create(libp, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(libp, .libPaths()))

project_root <- Sys.getenv("CGS_PROJECT_ROOT")
if (!nzchar(project_root)) stop("CGS_PROJECT_ROOT is empty")

lockfile <- file.path(project_root, "renv.lock")
activate <- file.path(project_root, "renv", "activate.R")

if (file.exists(lockfile)) {
  if (!requireNamespace("renv", quietly = TRUE)) {
    install.packages(
      "renv",
      repos = "https://cloud.r-project.org",
      lib = libp
    )
  }

  renv::restore(project = project_root, prompt = FALSE)

  if (file.exists(activate)) {
    source(activate)
  }
}

packages <- c("ggplot2", "patchwork")
missing <- packages[
  !vapply(packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing) > 0L) {
  install.packages(
    missing,
    repos = "https://cloud.r-project.org",
    lib = libp
  )
}

still_missing <- packages[
  !vapply(packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(still_missing) > 0L) {
  stop(
    "Missing R packages after installation: ",
    paste(still_missing, collapse = ", ")
  )
}

cat("Figure packages ready\n")
cat("renv lock used: ", file.exists(lockfile), "\n", sep = "")
for (pkg in packages) {
  cat(pkg, ": ", as.character(packageVersion(pkg)), "\n", sep = "")
}
cat("Library paths:\n")
cat(paste(.libPaths(), collapse = "\n"), "\n")
'@ | Set-Content -Path $PackageScript -Encoding ASCII

Invoke-RProcess `
    -Arguments @("--vanilla", "`"$PackageScript`"") `
    -StdoutPath (Join-Path $LogDir "packages_stdout.log") `
    -StderrPath (Join-Path $LogDir "packages_stderr.log") `
    -StepName "R package preparation"

# IMPORTANT: Rscript receives the script as a positional argument.
# Do not call Rscript with "--file=<script>".
Invoke-RProcess `
    -Arguments @("--vanilla", "`"$RenderScript`"") `
    -StdoutPath (Join-Path $LogDir "render_stdout.log") `
    -StderrPath (Join-Path $LogDir "render_stderr.log") `
    -StepName "Figure rendering"

# Verify every manifest-listed output.
$Manifest = Import-Csv $ManifestPath

if (-not $Manifest -or -not ($Manifest[0].PSObject.Properties.Name -contains "figure")) {
    throw "Figure manifest must contain a nonempty 'figure' column: $ManifestPath"
}

$Validation = foreach ($Row in $Manifest) {
    $Stem = $Row.figure

    foreach ($Extension in @("pdf", "png")) {
        $Path = Join-Path $FigureDir "$Stem.$Extension"
        $Exists = Test-Path $Path
        $Bytes = if ($Exists) { (Get-Item $Path).Length } else { 0 }

        [PSCustomObject]@{
            figure = $Stem
            extension = $Extension
            path = $Path
            exists = $Exists
            bytes = $Bytes
            sha256 = if ($Exists -and $Bytes -gt 0) {
                (Get-FileHash $Path -Algorithm SHA256).Hash
            }
            else {
                ""
            }
        }
    }
}

$ValidationPath = Join-Path $FigureDir "rendered_output_validation.csv"
$Validation | Export-Csv $ValidationPath -NoTypeInformation -Encoding UTF8
$Validation | Format-Table figure, extension, exists, bytes -AutoSize

$Invalid = $Validation | Where-Object { -not $_.exists -or $_.bytes -le 0 }
if ($Invalid) {
    $Invalid | Format-Table -AutoSize
    throw "Figure verification failed. Missing or zero-byte outputs are listed in $ValidationPath"
}

# Record R session information using the same local library.
$SessionInfoScript = Join-Path $EnvironmentDir "write_session_info.R"

@'
libp <- Sys.getenv("R_FIG_LIB")
if (nzchar(libp)) .libPaths(c(libp, .libPaths()))
writeLines(capture.output(sessionInfo()), commandArgs(trailingOnly = TRUE)[1])
'@ | Set-Content -Path $SessionInfoScript -Encoding ASCII

$SessionInfoPath = Join-Path $FigureDir "R_sessionInfo.txt"

Invoke-RProcess `
    -Arguments @("--vanilla", "`"$SessionInfoScript`"", "`"$SessionInfoPath`"") `
    -StdoutPath (Join-Path $LogDir "session_stdout.log") `
    -StderrPath (Join-Path $LogDir "session_stderr.log") `
    -StepName "R session-information capture"

Write-Host ""
Write-Host "SUCCESS: all manifest-listed figures were rendered and verified."
Write-Host "Figure directory: $FigureDir"
Write-Host "Validation manifest: $ValidationPath"
