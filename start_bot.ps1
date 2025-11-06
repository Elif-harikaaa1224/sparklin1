# PowerShell script to start the bot
$env:PYTHONIOENCODING="utf-8"
Set-Location $PSScriptRoot
Write-Host "Starting SPARK Wallet Bot..." -ForegroundColor Green
py telegram_bot.py

