# Reference the System.Data.SQLite .NET library
Add-Type -Path "$PSScriptRoot\System.Data.SQLite.dll"

function Get-LastLogon {
    param (
        [Parameter(Mandatory=$true)]
        [string]$UserName
    )

    $ntuserPath = "$Env:systemdrive\Users\$UserName\NTUSER.DAT"
    if (Test-Path $ntuserPath) {
        return [System.IO.File]::GetLastWriteTime($ntuserPath)
    }
    else {
        return $null
    }
}

function Get-EdgeHistory {
    param (
        [Parameter(Mandatory=$true)]
        [string]$UserName
    )

    $baseProfilePath = "$Env:systemdrive\Users\$UserName\AppData\Local\Microsoft\Edge\User Data" 
    $profiles = Get-ChildItem -Path $baseProfilePath -Directory | 
                Where-Object { $_.Name -match "^Profile \d+$|^Default$" } |
                ForEach-Object { $_.Name }

    foreach ($profile in $profiles) {
        $Path = Join-Path $baseProfilePath $profile
        $Path = Join-Path $Path 'History'

        if (-not (Test-Path -Path $Path)) { 
            Write-Host "[!] Could not find Edge History for username: $UserName and profile: $profile" -ForegroundColor Yellow
            Write-Output "[!] Could not find Edge History for username: $UserName and profile: $profile" | Out-File "${PSScriptRoot}\log.txt" -Append
            continue
        } 

        Write-Host "[+] Trying to extract history for username: $UserName and profile: $profile" -ForegroundColor Green

        $startCheckTime = Get-Date
        while (((Get-Date) - $startCheckTime).TotalMinutes -lt 15) {
            try {
                $connection = New-Object -TypeName System.Data.SQLite.SQLiteConnection -ArgumentList "Data Source=$Path;"
                $connection.Open()

                $command = $connection.CreateCommand()
                $command.CommandText = "SELECT datetime(last_visit_time / 1000000 + (strftime('%s', '1601-01-01')), 'unixepoch'), url FROM urls WHERE datetime(last_visit_time / 1000000 + (strftime('%s', '1601-01-01')), 'unixepoch') > datetime('now', '-7 days');"

                $reader = $command.ExecuteReader()
                $dataList = New-Object System.Collections.Generic.List[object]

                while ($reader.Read()) {
                    $dataList.Add([PSCustomObject]@{
                        User     = $UserName
                        Browser  = 'Edge'
                        Profile  = $profile
                        Date     = $reader.GetString(0)
                        URL      = $reader.GetString(1)
                    })
                }

                $reader.Close()
                $connection.Close()

                $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
                $csvPath = Join-Path $PSScriptRoot "data\${timestamp}_${UserName}.csv"
                $dataList | Export-Csv -Path $csvPath -NoTypeInformation

                Write-Host "[+] History extraction successful for username: $UserName and profile: $profile" -ForegroundColor Green
                                
                break
            }
            catch {
                Write-Host "[-] Error: $($_.Exception.Message)" -ForegroundColor Red
                Write-Host "[-] Retrying in 30 seconds..." -ForegroundColor Yellow
                Start-Sleep -Seconds 30
            }
        }
    }
}

# Get all unique users using wmic
$users = Get-LocalUser | 
         Where-Object {$_.Enabled -eq $true -and $_.Name -notin ('SYSTEM', 'Guest', 'DefaultAccount', 'Administrator', 'WDAGUtilityAccount', 'DevToolsUser')} |
         Select-Object -ExpandProperty Name |
         Sort-Object -Unique

$last7Days = (Get-Date).AddDays(-7)

foreach ($user in $users) {
    $lastLogon = Get-LastLogon -UserName $user
    # Call the function if the last logon was within the last 7 days
    if ($lastLogon -gt $last7Days) {
        Get-EdgeHistory -UserName $user
    }
}