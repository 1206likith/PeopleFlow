param(
    [switch]$NoBrowser,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 4173,
    [switch]$ReloadBackend,
    [string]$OpenPath = "/"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSCommandPath
$backendDir = Join-Path $repoRoot "apps\backend"
$frontendDir = Join-Path $repoRoot "apps\frontend"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$frontendPackage = Join-Path $frontendDir "package.json"
$frontendNodeModules = Join-Path $frontendDir "node_modules"
$launchInfoPath = Join-Path $repoRoot ".peopleflow-launch.json"

function Quote-ForSingleString {
    param([string]$Value)
    return ($Value -replace "'", "''")
}

function Test-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 3
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeconds
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Test-BackendCompatibility {
    param(
        [string]$BaseUrl,
        [int]$TimeoutSeconds = 3,
        [string]$ExpectedMode = "demo"
    )

    $normalizedBase = $BaseUrl.TrimEnd("/")
    $sessionUrl = "$normalizedBase/api/v3/simulation/sessions?limit=1"

    try {
        $response = Invoke-RestMethod -Uri $sessionUrl -TimeoutSec $TimeoutSeconds
        $version = $response.meta.version
        $mode = $response.meta.mode
        return ($version -eq "v3" -and $mode -eq $ExpectedMode)
    } catch {
        return $false
    }
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpReady -Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Test-PortListening {
    param([int]$Port)

    try {
        return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
    } catch {
        return $false
    }
}

function Get-NextAvailablePort {
    param(
        [int]$StartPort,
        [int[]]$ReservedPorts = @()
    )

    $port = $StartPort
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        if (($ReservedPorts -contains $port) -or (Test-PortListening -Port $port)) {
            $port += 1
            continue
        }
        return $port
    }

    throw "Could not find an available port after checking 100 candidates starting at $StartPort."
}

function Get-ListeningProcessInfo {
    param([int]$Port)

    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $connection) {
            return $null
        }

        $process = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $connection.OwningProcess) -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            return [pscustomobject]@{
                Port = $Port
                ProcessId = $connection.OwningProcess
                Name = $null
                CommandLine = $null
            }
        }

        return [pscustomobject]@{
            Port = $Port
            ProcessId = $connection.OwningProcess
            Name = $process.Name
            CommandLine = $process.CommandLine
        }
    } catch {
        return $null
    }
}

function Test-IsPeopleFlowBackendProcess {
    param([object]$ProcessInfo)

    if ($null -eq $ProcessInfo) {
        return $false
    }

    $commandLine = [string]$ProcessInfo.CommandLine
    if ([string]::IsNullOrWhiteSpace($commandLine)) {
        return $false
    }

    return $commandLine -match "(?i)-m\s+uvicorn\s+app\.main:app"
}

function Test-IsPeopleFlowFrontendProcess {
    param([object]$ProcessInfo)

    if ($null -eq $ProcessInfo) {
        return $false
    }

    $commandLine = [string]$ProcessInfo.CommandLine
    if ([string]::IsNullOrWhiteSpace($commandLine)) {
        return $false
    }

    $normalizedFrontendDir = $frontendDir.ToLowerInvariant()
    $normalizedCommandLine = $commandLine.ToLowerInvariant()

    return ($normalizedCommandLine.Contains("vite")) -and ($normalizedCommandLine.Contains($normalizedFrontendDir.ToLowerInvariant()))
}

function Stop-ListeningProcessIfOwnedByPeopleFlow {
    param(
        [int]$Port,
        [ValidateSet("backend", "frontend")]
        [string]$Role
    )

    $processInfo = Get-ListeningProcessInfo -Port $Port
    if ($null -eq $processInfo) {
        return $false
    }

    $isOwned = if ($Role -eq "backend") {
        Test-IsPeopleFlowBackendProcess -ProcessInfo $processInfo
    } else {
        Test-IsPeopleFlowFrontendProcess -ProcessInfo $processInfo
    }

    if (-not $isOwned) {
        return $false
    }

    try {
        Stop-Process -Id $processInfo.ProcessId -Force -ErrorAction Stop
        Start-Sleep -Milliseconds 800
        Write-Host "Reclaimed stale PeopleFlow $Role on port $Port (PID $($processInfo.ProcessId))." -ForegroundColor DarkYellow
        return $true
    } catch {
        Write-Warning "Could not stop existing PeopleFlow $Role on port $Port (PID $($processInfo.ProcessId)): $($_.Exception.Message)"
        return $false
    }
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$CommandText
    )

    $escapedTitle = Quote-ForSingleString $Title
    $escapedDirectory = Quote-ForSingleString $WorkingDirectory
    $wrappedCommand = "`$host.UI.RawUI.WindowTitle = '$escapedTitle'; Set-Location -LiteralPath '$escapedDirectory'; $CommandText"

    Start-Process `
        -FilePath "powershell.exe" `
        -WorkingDirectory $WorkingDirectory `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $wrappedCommand) `
        | Out-Null
}

function Normalize-OpenPath {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return "/"
    }

    if ($Value.StartsWith("/")) {
        return $Value
    }

    return "/$Value"
}

function Join-UrlPath {
    param(
        [string]$BaseUrl,
        [string]$Path
    )

    $normalizedPath = Normalize-OpenPath -Value $Path
    return "$($BaseUrl.TrimEnd('/'))$normalizedPath"
}

if (-not (Test-Path $backendPython)) {
    throw "Backend virtual environment not found at apps\backend\.venv. Run apps\backend\setup_backend.bat first."
}

if (-not (Test-Path $frontendPackage)) {
    throw "Frontend package.json not found at apps\frontend\package.json."
}

if (-not (Test-Path $frontendNodeModules)) {
    throw "Frontend dependencies are missing at apps\frontend\node_modules. Run npm install in apps\frontend first."
}

$npmCommand = (Get-Command "npm.cmd" -ErrorAction Stop).Source
$escapedBackendPython = Quote-ForSingleString $backendPython
$escapedNpmCommand = Quote-ForSingleString $npmCommand

$preferredBackendBaseUrl = "http://127.0.0.1:$BackendPort"
$preferredBackendHealthUrl = "$preferredBackendBaseUrl/api/health"
$backendPortToUse = $BackendPort
$backendBaseUrl = $preferredBackendBaseUrl
$backendHealthUrl = $preferredBackendHealthUrl
$backendRunning = $false
$backendCompatible = $false

if (Test-HttpReady -Url $preferredBackendHealthUrl) {
    $backendCompatible = Test-BackendCompatibility -BaseUrl $preferredBackendBaseUrl
    if ($backendCompatible) {
        $backendRunning = $true
        Write-Host "Backend already running at $preferredBackendBaseUrl" -ForegroundColor Cyan
    } else {
        if (Stop-ListeningProcessIfOwnedByPeopleFlow -Port $BackendPort -Role "backend") {
            Write-Warning "Backend on port $BackendPort was stale or incompatible. Restarting PeopleFlow backend on the preferred port."
        } else {
            Write-Warning "Backend on port $BackendPort responded to health checks but is not compatible with the current simulation/session API. A fresh PeopleFlow backend will be started on a new port."
            $backendPortToUse = Get-NextAvailablePort -StartPort ($BackendPort + 1)
        }
    }
} else {
    if (Test-PortListening -Port $BackendPort) {
        if (-not (Stop-ListeningProcessIfOwnedByPeopleFlow -Port $BackendPort -Role "backend")) {
            $backendPortToUse = Get-NextAvailablePort -StartPort ($BackendPort + 1)
            Write-Warning "Backend port $BackendPort is occupied by a non-ready listener. Starting PeopleFlow backend on port $backendPortToUse instead."
        }
    }

    $backendBaseUrl = "http://127.0.0.1:$backendPortToUse"
    $backendHealthUrl = "$backendBaseUrl/api/health"
    $reloadFlag = if ($ReloadBackend) { " --reload" } else { "" }

    Write-Host "Starting backend in a new window on port $backendPortToUse..." -ForegroundColor Yellow
    $backendCommand = @"
`$env:APP_MODE = 'demo'
`$env:DATABASE_MODE = 'sqlite'
`$env:DEBUG = 'false'
`$env:ADMIN_KEY_ENABLED = 'false'
& '$escapedBackendPython' -m uvicorn app.main:app --host 127.0.0.1 --port $backendPortToUse$reloadFlag
"@
    Start-ServiceWindow -Title "PeopleFlow Backend" -WorkingDirectory $backendDir -CommandText $backendCommand
}

$preferredFrontendUrl = "http://127.0.0.1:$FrontendPort/"
$frontendPortToUse = $FrontendPort
$frontendUrl = $preferredFrontendUrl
$frontendRunning = $false
$reusePreferredFrontend = $backendRunning -and ($backendPortToUse -eq $BackendPort) -and (Test-HttpReady -Url $preferredFrontendUrl)

if ($reusePreferredFrontend) {
    $frontendRunning = $true
    Write-Host "Frontend already running at $preferredFrontendUrl" -ForegroundColor Cyan
} else {
    if (Test-PortListening -Port $FrontendPort) {
        if (-not (Stop-ListeningProcessIfOwnedByPeopleFlow -Port $FrontendPort -Role "frontend")) {
            $frontendPortToUse = Get-NextAvailablePort -StartPort ($FrontendPort + 1) -ReservedPorts @($backendPortToUse)
            Write-Warning "Frontend port $FrontendPort is occupied. Starting PeopleFlow frontend on port $frontendPortToUse instead."
        }
    }

    $frontendUrl = "http://127.0.0.1:$frontendPortToUse/"
    Write-Host "Starting frontend in a new window on port $frontendPortToUse..." -ForegroundColor Yellow
$frontendCommand = @"
`$env:VITE_API_BASE_URL = '$backendBaseUrl'
`$env:VITE_WS_BASE_URL = 'ws://127.0.0.1:$backendPortToUse'
`$env:VITE_DEFAULT_ADMIN_KEY = 'change-me'
& '$escapedNpmCommand' run dev -- --host 127.0.0.1 --port $frontendPortToUse
"@
    Start-ServiceWindow -Title "PeopleFlow Frontend" -WorkingDirectory $frontendDir -CommandText $frontendCommand
}

if (-not $backendRunning) {
    if (Wait-HttpReady -Url $backendHealthUrl -TimeoutSeconds 90) {
        Write-Host "Backend is ready." -ForegroundColor Green
    } else {
        Write-Warning "Backend did not become ready within 90 seconds. Check the PeopleFlow Backend window."
    }
}

if (-not $frontendRunning) {
    if (Wait-HttpReady -Url $frontendUrl -TimeoutSeconds 90) {
        Write-Host "Frontend is ready." -ForegroundColor Green
    } else {
        Write-Warning "Frontend did not become ready within 90 seconds. Check the PeopleFlow Frontend window."
    }
}

$openPathToUse = Normalize-OpenPath -Value $OpenPath
$browserUrl = Join-UrlPath -BaseUrl $frontendUrl -Path $openPathToUse
$docsUrl = "$backendBaseUrl/api/v2/docs"
$launchInfo = [ordered]@{
    started_at = (Get-Date).ToString("o")
    repo_root = $repoRoot
    frontend_url = $frontendUrl
    frontend_open_url = $browserUrl
    backend_base_url = $backendBaseUrl
    backend_health_url = $backendHealthUrl
    backend_docs_url = $docsUrl
    api_base_url = $backendBaseUrl
    ws_base_url = "ws://127.0.0.1:$backendPortToUse"
    frontend_port = $frontendPortToUse
    backend_port = $backendPortToUse
    open_path = $openPathToUse
}
$launchInfo | ConvertTo-Json -Depth 5 | Set-Content -Path $launchInfoPath -Encoding UTF8

if (-not $NoBrowser -and (Test-HttpReady -Url $frontendUrl)) {
    Write-Host "Opening $browserUrl" -ForegroundColor Green
    Start-Process $browserUrl | Out-Null
}

Write-Host ""
Write-Host "PeopleFlow launcher complete." -ForegroundColor Green
Write-Host "Frontend: $frontendUrl"
Write-Host "Open:     $browserUrl"
Write-Host "Backend:  $docsUrl"
Write-Host "Launch info saved to: $launchInfoPath"
