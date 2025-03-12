# Get the latest CSV file in the current directory
$csvPath = Join-Path $PSScriptRoot "data"
$latestCsv = Get-ChildItem -Path $csvPath -Filter "*.csv" | 
    Where-Object { $_.Name -notlike "clean_*" } |
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1

if ($latestCsv) {
    # Read the CSV file
    $data = Import-Csv -Path $latestCsv.FullName

    # Function to clean URLs by removing parameters
    function Format-Url {
        param([string]$url)
        try {
            $uri = [System.Uri]$url
            return "$($uri.Scheme)://$($uri.Host)$($uri.AbsolutePath)"
        }
        catch {
            return $url
        }
    }

    # Clean URLs and remove duplicates
    $uniqueData = $data | ForEach-Object {
        $_ | Add-Member -MemberType NoteProperty -Name 'CleanURL' -Value (Format-Url $_.URL) -Force
        $_
    } | Sort-Object CleanURL, Date -Unique | Select-Object User, Browser, Profile, Date, URL

    # Save to new file with '-clean' suffix
    $newFileName = "clean_" + $latestCsv.BaseName + ".csv"
    $newFilePath = Join-Path $csvPath $newFileName
    $uniqueData | Export-Csv -Path $newFilePath -NoTypeInformation


    Write-Host "Processed $($data.Count) entries to $($uniqueData.Count) unique entries"
    Write-Host "Saved to: $newFileName"
}
else {
    Write-Host "No CSV files found in the current directory"
}