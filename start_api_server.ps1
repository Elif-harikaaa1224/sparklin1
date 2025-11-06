#!/usr/bin/env pwsh
# Скрипт для запуска Spark SDK API сервера
# Запускает Node.js API сервер для высокопроизводительной обработки запросов

Write-Host "🚀 Запуск Spark SDK API Server..." -ForegroundColor Green
Write-Host ""

# Проверяем что находимся в правильной директории
if (-not (Test-Path "nodejs")) {
    Write-Host "❌ Ошибка: Папка nodejs не найдена!" -ForegroundColor Red
    Write-Host "Запустите скрипт из корневой папки проекта" -ForegroundColor Yellow
    exit 1
}

# Переходим в nodejs директорию
Set-Location nodejs

# Проверяем что package.json существует
if (-not (Test-Path "package.json")) {
    Write-Host "❌ Ошибка: package.json не найден!" -ForegroundColor Red
    exit 1
}

# Проверяем установлены ли зависимости
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Устанавливаю зависимости..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка установки зависимостей!" -ForegroundColor Red
        exit 1
    }
}

# Запускаем API сервер
Write-Host "🌐 Запускаю API сервер на http://127.0.0.1:3000" -ForegroundColor Cyan
Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Gray
Write-Host ""

npm start
