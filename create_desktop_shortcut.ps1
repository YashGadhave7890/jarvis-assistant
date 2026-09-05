<#
.SYNOPSIS
    Creates a 1-Click Desktop Shortcut for JARVIS AI Assistant.
#>

$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "JARVIS AI Assistant.lnk"
$TargetBat = Join-Path $PSScriptRoot "run_jarvis.bat"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetBat
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "JARVIS AI Assistant — Quantum Intelligence HUD"
$Shortcut.IconLocation = "shell32.dll,14" # High-tech computer/chip icon
$Shortcut.Save()

Write-Host "[SUCCESS] Created Desktop Shortcut: $ShortcutPath" -ForegroundColor Green
Write-Host "You can now double-click 'JARVIS AI Assistant' on your desktop anytime!" -ForegroundColor Cyan
