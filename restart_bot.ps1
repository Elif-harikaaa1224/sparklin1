# Script to restart Telegram Bot
# Kills all Python processes and restarts the bot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Restarting SPARK Wallet Bot..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop any running Python processes
Write-Host "[1/3] Stopping running Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Clear Python cache
Write-Host "[2/3] Clearing Python cache..." -ForegroundColor Yellow
Remove-Item -Path "__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "*.pyc" -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   Cache cleared!" -ForegroundColor Green

# Start the bot
Write-Host "[3/3] Starting Telegram bot..." -ForegroundColor Green
Write-Host ""
Write-Host "Bot is starting..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the bot" -ForegroundColor Yellow
Write-Host ""

# Run the bot
py telegram_bot.py
