$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = "C:\Users\elcan\AppData\Local\Programs\Python\Python312\python.exe"
$installDir = "$env:LOCALAPPDATA\Programs\SesYaz"

# Build frontend production bundle first
Set-Location "$root\frontend"
npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Stop any running SesYaz instances AND child QtWebEngineProcess processes holding DLLs
Get-CimInstance Win32_Process |
    Where-Object { $_.ExecutablePath -like "$installDir*" -or $_.CommandLine -like "*sesyaz*main.py*" -or $_.Name -eq "SesYaz.exe" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 1200

Set-Location $root
& $py -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name "SesYaz" `
    --icon "$root\app\sesyaz.ico" `
    --paths "$root\app" `
    --add-data "$root\app\ui_dist;ui_dist" `
    --collect-data "sounddevice" `
    --collect-data "_sounddevice_data" `
    --hidden-import "websockets" `
    --hidden-import "google.genai" `
    --distpath "$root\build_dist" `
    --workpath "$root\build_tmp" `
    --specpath "$root\build_tmp" `
    "$root\app\main.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Stop any running SesYaz tree right before swapping installed binaries
cmd /c "taskkill /F /IM SesYaz.exe /T >nul 2>&1"
Get-CimInstance Win32_Process |
    Where-Object { $_.ExecutablePath -like "$installDir*" -or $_.CommandLine -like "*sesyaz\app\main.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 1500
if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force }
New-Item -ItemType Directory -Path "$env:LOCALAPPDATA\Programs" -Force | Out-Null
Copy-Item "$root\build_dist\SesYaz" $installDir -Recurse -Force

Remove-Item "$root\build_dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$root\build_tmp" -Recurse -Force -ErrorAction SilentlyContinue

# Update Desktop & Start Menu shortcuts to native SesYaz.exe
$ws = New-Object -ComObject WScript.Shell
$desktop = "C:\Users\elcan\OneDrive\Desktop"
if (Test-Path $desktop) {
    $sc = $ws.CreateShortcut("$desktop\SesYaz.lnk")
    $sc.TargetPath = "$installDir\SesYaz.exe"
    $sc.WorkingDirectory = $installDir
    $sc.IconLocation = "$installDir\SesYaz.exe,0"
    $sc.Description = "SesYaz — Azerbaycanca + Texniki Sesli Yazi"
    $sc.Save()
}
$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
if (Test-Path $startMenu) {
    $sc2 = $ws.CreateShortcut("$startMenu\SesYaz.lnk")
    $sc2.TargetPath = "$installDir\SesYaz.exe"
    $sc2.WorkingDirectory = $installDir
    $sc2.IconLocation = "$installDir\SesYaz.exe,0"
    $sc2.Description = "SesYaz — Azerbaycanca + Texniki Sesli Yazi"
    $sc2.Save()
}

Write-Output "INSTALLED: $installDir\SesYaz.exe"
