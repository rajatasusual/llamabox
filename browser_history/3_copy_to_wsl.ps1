# Check if WSL is running
$wslStatus = wsl --list --running 2>&1
if ($wslStatus -match "There are no running distributions") {
    Write-Host "WSL is not running. Starting WSL..."
    wsl.exe --start
}

# Define the WSL path
$wslPath = "\\wsl$\Debian\home\box\data"

# Create the data directory if it doesn't exist
if (-not (Test-Path $wslPath)) {
    try {
        New-Item -Path $wslPath -ItemType Directory -Force
        Write-Host "Created directory: $wslPath"
    }
    catch {
        Write-Error "Failed to create directory: $_"
        exit 1
    }
}

# Get the latest CSV file that starts with "clean"
$csvPath = Join-Path $PSScriptRoot "data"
$latestCsv =  Get-ChildItem -Path $csvPath -Filter "clean*.csv" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1

if ($latestCsv) {
    try {
        Copy-Item -Path $latestCsv.FullName -Destination $wslPath -Force
        Write-Host "Successfully copied $($latestCsv.Name) to $wslPath"
    }
    catch {
        Write-Error "Failed to copy file: $_"
        exit 1
    }
}
else {
    Write-Warning "No CSV files found with 'clean' prefix"
}