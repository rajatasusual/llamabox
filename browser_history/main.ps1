$scripts = @(
    "1_get_history.ps1",
    "2_clean_history.ps1",
    "3_copy_to_wsl.ps1"
)

foreach ($script in $scripts) {
    $scriptPath = Join-Path $PSScriptRoot $script
    Write-Host "Executing $script..."
    
    & $scriptPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Script $script failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Write-Host "All scripts completed successfully."