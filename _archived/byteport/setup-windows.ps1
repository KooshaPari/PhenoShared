# BytePort Windows Setup Script
# Run as Administrator

param(
    [string]$Domain = "yourdomain.com",
    [string]$ProjectsPath = "C:\BytePort",
    [string]$TunnelName = "byteport-main",
    [switch]$SkipDocker = $false,
    [switch]$SkipCloudflare = $false
)

Write-Host "🚀 Setting up BytePort Windows Server..." -ForegroundColor Green

# Create directory structure
Write-Host "📁 Creating directory structure..." -ForegroundColor Yellow
$directories = @(
    "$ProjectsPath\projects",
    "$ProjectsPath\tunnels",
    "$ProjectsPath\nginx",
    "$ProjectsPath\logs",
    "$ProjectsPath\backups"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force
        Write-Host "Created: $dir" -ForegroundColor Gray
    }
}

# Require Chocolatey if not present
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Chocolatey is required before continuing." -ForegroundColor Yellow
    Write-Host "Install it from https://chocolatey.org/install, reopen PowerShell, then rerun this script." -ForegroundColor White
    exit 1
}

# Install required tools
Write-Host "🛠️ Installing required tools..." -ForegroundColor Yellow
$tools = @(
    "git",
    "golang",
    "nodejs"
)

if (!$SkipDocker) {
    $tools += "docker-desktop"
}

if (!$SkipCloudflare) {
    # Install cloudflared manually since it's not in chocolatey
    Write-Host "Installing cloudflared..." -ForegroundColor Gray
    $cloudflaredUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    $cloudflaredPath = "$env:ProgramFiles\cloudflared\cloudflared.exe"

    if (!(Test-Path $cloudflaredPath)) {
        New-Item -ItemType Directory -Path "$env:ProgramFiles\cloudflared" -Force
        Invoke-WebRequest -Uri $cloudflaredUrl -OutFile $cloudflaredPath

        # Add to PATH
        $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if ($currentPath -notlike "*$env:ProgramFiles\cloudflared*") {
            [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$env:ProgramFiles\cloudflared", "Machine")
        }
    }
}

foreach ($tool in $tools) {
    Write-Host "Installing $tool..." -ForegroundColor Gray
    choco install $tool -y
}

# Configure Docker (if not skipped)
if (!$SkipDocker) {
    Write-Host "🐳 Configuring Docker..." -ForegroundColor Yellow

    # Wait for Docker Desktop to start
    Write-Host "Waiting for Docker Desktop to start..." -ForegroundColor Gray
    $timeout = 120 # 2 minutes timeout
    $elapsed = 0
    do {
        Start-Sleep -Seconds 5
        $elapsed += 5
        try {
            $dockerStatus = docker version 2>$null
            if ($dockerStatus) { break }
        } catch {
            # Continue waiting
        }
    } while ($elapsed -lt $timeout)

    if ($elapsed -ge $timeout) {
        Write-Host "Warning: Docker Desktop may not be running. Please start it manually." -ForegroundColor Red
    } else {
        # Create Docker network for BytePort
        docker network create byteport-network 2>$null
        Write-Host "Created Docker network: byteport-network" -ForegroundColor Gray
    }
}

# Configure environment variables
Write-Host "⚙️ Setting up environment variables..." -ForegroundColor Yellow

$envVars = @{
    "BYTEPORT_ROOT" = $ProjectsPath
    "BYTEPORT_DOMAIN" = $Domain
    "BYTEPORT_API_PORT" = "8081"
    "BYTEPORT_NVMS_PORT" = "3000"
    "BYTEPORT_FRONTEND_PORT" = "5173"
    "DOCKER_NETWORK" = "byteport-network"
    "TUNNEL_CONFIG_PATH" = "$ProjectsPath\tunnels"
    "TUNNEL_NAME" = $TunnelName
    "PROJECTS_PATH" = "$ProjectsPath\projects"
}

foreach ($var in $envVars.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($var.Key, $var.Value, "Machine")
    Write-Host "Set $($var.Key) = $($var.Value)" -ForegroundColor Gray
}

# Create .env file for local development
$envContent = @"
# BytePort Windows Configuration
BYTEPORT_ROOT=$ProjectsPath
BYTEPORT_DOMAIN=$Domain
BYTEPORT_API_PORT=8081
BYTEPORT_NVMS_PORT=3000
BYTEPORT_FRONTEND_PORT=5173
DOCKER_NETWORK=byteport-network
TUNNEL_CONFIG_PATH=$ProjectsPath\tunnels
TUNNEL_NAME=$TunnelName
PROJECTS_PATH=$ProjectsPath\projects
"@

$envContent | Out-File -FilePath "$ProjectsPath\.env" -Encoding UTF8

# Configure Cloudflare Tunnel (if not skipped)
if (!$SkipCloudflare) {
    Write-Host "☁️ Configuring Cloudflare Tunnel..." -ForegroundColor Yellow

    Write-Host "Please run the following commands manually after this script completes:" -ForegroundColor Red
    Write-Host "1. cloudflared tunnel login" -ForegroundColor White
    Write-Host "2. cloudflared tunnel create $TunnelName" -ForegroundColor White
    Write-Host "3. Copy the tunnel credentials to $ProjectsPath\tunnels\" -ForegroundColor White

    # Create sample tunnel config
    $tunnelConfig = @"
tunnel: YOUR_TUNNEL_ID
credentials-file: $ProjectsPath\tunnels\YOUR_TUNNEL_ID.json

ingress:
  - hostname: $Domain
    service: http://localhost:8080
  - hostname: "*.$Domain"
    service: http://localhost:8080
  - service: http_status:404

logfile: $ProjectsPath\logs\tunnel.log
"@

    $tunnelConfig | Out-File -FilePath "$ProjectsPath\tunnels\config-template.yml" -Encoding UTF8
    Write-Host "Created tunnel config template at $ProjectsPath\tunnels\config-template.yml" -ForegroundColor Gray
}

# Create service management scripts
Write-Host "🔧 Creating service management scripts..." -ForegroundColor Yellow

$startScript = @"
@echo off
echo Starting BytePort Services...

echo Setting environment variables...
set BYTEPORT_ROOT=$ProjectsPath
set BYTEPORT_DOMAIN=$Domain
set PROJECTS_PATH=$ProjectsPath\projects
set TUNNEL_CONFIG_PATH=$ProjectsPath\tunnels
set TUNNEL_NAME=$TunnelName

echo Starting BytePort API...
cd /d "%~dp0backend\byteport"
start /B go run main.go

echo Starting NVMS Service...
cd /d "%~dp0backend\nvms"
start /B go run main.go

echo Starting Frontend...
cd /d "%~dp0frontend\web"
start /B npm run dev

echo All services started!
echo Access BytePort at: http://localhost:5173
pause
"@

$startScript | Out-File -FilePath "$ProjectsPath\start-services.bat" -Encoding ASCII

$stopScript = @"
@echo off
echo Stopping BytePort Services...

echo Stopping Go processes...
taskkill /F /IM go.exe 2>nul

echo Stopping Node processes...
taskkill /F /IM node.exe 2>nul

echo All services stopped!
pause
"@

$stopScript | Out-File -FilePath "$ProjectsPath\stop-services.bat" -Encoding ASCII

# Set up firewall rules
Write-Host "🔥 Configuring Windows Firewall..." -ForegroundColor Yellow

$ports = @(8081, 3000, 5173)
foreach ($port in $ports) {
    try {
        netsh advfirewall firewall add rule name="BytePort-$port" dir=in action=allow protocol=TCP localport=$port 2>$null
        Write-Host "Opened port $port" -ForegroundColor Gray
    } catch {
        Write-Host "Warning: Could not open port $port" -ForegroundColor Yellow
    }
}

# Create project template
Write-Host "📋 Creating project template..." -ForegroundColor Yellow

$projectTemplate = @"
NAME: "example-project"
DESCRIPTION: "Example project description"
SERVICES:
  - NAME: "main"
    PATH: "./frontend"
    PORT: 8080
  - NAME: "api"
    PATH: "./backend"
    PORT: 8081
"@

$projectTemplate | Out-File -FilePath "$ProjectsPath\odin.nvms.template" -Encoding UTF8

Write-Host "✅ BytePort Windows Server setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Your BytePort repository should be cloned to this directory" -ForegroundColor White
Write-Host "2. Configure Cloudflare tunnel (if not skipped)" -ForegroundColor White
Write-Host "3. Install frontend dependencies: cd frontend\web && npm install" -ForegroundColor White
Write-Host "4. Run start-services.bat to start all services" -ForegroundColor White
Write-Host ""
Write-Host "Configuration files created:" -ForegroundColor Yellow
Write-Host "- Environment: $ProjectsPath\.env" -ForegroundColor White
Write-Host "- Services: $ProjectsPath\start-services.bat" -ForegroundColor White
Write-Host "- Template: $ProjectsPath\odin.nvms.template" -ForegroundColor White
Write-Host ""
Write-Host "Access BytePort at: http://localhost:5173" -ForegroundColor Green
