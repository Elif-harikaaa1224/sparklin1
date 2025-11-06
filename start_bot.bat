@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting SPARK Wallet Bot...
py telegram_bot.py
pause

