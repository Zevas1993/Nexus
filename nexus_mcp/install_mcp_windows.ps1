# PowerShell script to install and configure the Nexus MCP server on Windows
# This script creates the necessary directories, installs dependencies, and configures the environment

# Define installation directory and paths
$InstallDir = "C:\Users\Chris Boyd\nexus_mcp_project"
$LogsDir = Join-Path -Path $InstallDir -ChildPath "logs"
$DataDir = Join-Path -Path $InstallDir -ChildPath "data"
$SrcDir = Join-Path -Path $InstallDir -ChildPath "src"

Write-Host "Nexus MCP Server Installation Script" -ForegroundColor Cyan
Write-Host "==================================="
Write-Host "Installation directory: $InstallDir"

# Create directories
Write-Host "Creating directory structure..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
New-Item -ItemType Directory -Force -Path $SrcDir | Out-Null

Write-Host "Directory structure created successfully."

# Set environment variables
Write-Host "Setting environment variables..." -ForegroundColor Green
[Environment]::SetEnvironmentVariable("MCP_HOST", "0.0.0.0", "User")
[Environment]::SetEnvironmentVariable("MCP_PORT", "8000", "User")
[Environment]::SetEnvironmentVariable("MCP_DEBUG", "false", "User")
[Environment]::SetEnvironmentVariable("MCP_SERVER_URL", "http://localhost:8000", "User")
[Environment]::SetEnvironmentVariable("NEXUS_API_URL", "http://localhost:5000/api/v1", "User")

Write-Host "Environment variables set successfully."

# Function to check if a package is installed
function Test-PackageInstalled {
    param (
        [string]$PackageName
    )
    
    $installed = pip list | Select-String -Pattern "^$PackageName\s"
    return $null -ne $installed
}

# Install required packages
Write-Host "Checking and installing Python dependencies..." -ForegroundColor Green
$packages = @("mcp", "pydantic", "fastapi", "uvicorn", "httpx", "psutil")

foreach ($package in $packages) {
    if (-not (Test-PackageInstalled -PackageName $package)) {
        Write-Host "Installing $package..."
        pip install $package
    } else {
        Write-Host "$package already installed."
    }
}

# Create hardware configuration file
Write-Host "Creating hardware configuration..." -ForegroundColor Green
$hardwareConfig = @{
    cpu = @{
        model = "Intel i7-13700k"
        cores = 16
        threads = 24
        parallel_workers = 12
    }
    gpu = @{
        model = "Gigabyte RTX 3070ti"
        vram = "8GB"
        cuda_enabled = $true
    }
    memory = @{
        total = "32GB"
        allocation = "16GB"
        buffer_size = "4GB"
    }
    optimization = @{
        parallel_processing = $true
        gpu_acceleration = $true
        memory_efficient = $true
        batch_size = 32
    }
}

$configPath = Join-Path -Path $InstallDir -ChildPath "hardware_config.json"
$hardwareConfig | ConvertTo-Json -Depth 4 | Set-Content -Path $configPath
Write-Host "Hardware configuration created at: $configPath"

# Create startup script
Write-Host "Creating startup script..." -ForegroundColor Green
$startupScript = @"
# PowerShell script to start the Nexus MCP server
Write-Host "Starting Nexus MCP server..." -ForegroundColor Cyan

# Start the MCP server in a new window
Start-Process -FilePath "python" -ArgumentList "$SrcDir\main.py" -NoNewWindow

# Wait for the server to start
Start-Sleep -Seconds 5

# Connect to Nexus
Write-Host "Connecting to Nexus..." -ForegroundColor Cyan
python "$SrcDir\nexus_mcp_connect.py"

Write-Host "Server is running. Press Enter to stop the server..." -ForegroundColor Green
`$null = Read-Host
"@

$startupPath = Join-Path -Path $InstallDir -ChildPath "start_mcp_server.ps1"
Set-Content -Path $startupPath -Value $startupScript
Write-Host "Startup script created at: $startupPath"

# Create instructions for copying files
Write-Host "`nInstallation completed!" -ForegroundColor Cyan
Write-Host "`nTo complete setup, please copy the following files to the appropriate locations:`n" -ForegroundColor Yellow

Write-Host "1. Copy the nexus_mcp directory to $SrcDir"
Write-Host "2. Copy main.py to $SrcDir"
Write-Host "3. Copy nexus_mcp_connect.py to $SrcDir"
Write-Host "4. Copy nexus_mcp_test.py to $SrcDir"
Write-Host "`nYou can do this with the following PowerShell commands:"
Write-Host "  Copy-Item -Path 'C:\Users\Chris Boyd\Desktop\nexus_mcp' -Destination '$SrcDir' -Recurse"
Write-Host "  Copy-Item -Path 'C:\Users\Chris Boyd\Desktop\main.py' -Destination '$SrcDir'"
Write-Host "  Copy-Item -Path 'C:\Users\Chris Boyd\Desktop\nexus_mcp_connect.py' -Destination '$SrcDir'"
Write-Host "  Copy-Item -Path 'C:\Users\Chris Boyd\Desktop\nexus_mcp_test.py' -Destination '$SrcDir'"

Write-Host "`nAfter copying the files, you can start the server by running:" -ForegroundColor Green
Write-Host "  $startupPath"
