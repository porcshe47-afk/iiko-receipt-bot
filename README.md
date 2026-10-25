# Telegram Mini App & Bot: iiko-receipt-bot

## Project Overview
Проект представляет собой Telegram-бот и сопутствующее Mini App для работы с чеками и накладными. Ранее проект зависел от временных локальных туннелей (ngrok/localtunnel), что приводило к ошибкам `503 Tunnel Unavailable`. В текущей версии фронтенд полностью перенесен на стабильный статический хостинг Cloudflare Pages.

## Core URLs & Infrastructure
- **Frontend (Telegram Mini App)**: Hosted on Cloudflare Pages at `https://iiko-receipt-bot.pages.dev`
- **Backend / Bot Runtime**: Long-polling via Python (aiogram), communicating directly with the stable frontend URL.

## Project Structure
- `src/bot/main.py` — Главная точка входа для запуска бота.
- `src/bot/handlers.py` — Обработчики команд и кнопок Telegram, содержащие ссылки на Mini App.
- `src/static/` — Статические файлы интерфейса.
- `venv/` — Виртуальное окружение Python.

## How to Run Locally
1. Активируйте виртуальное окружение:
   ```bash
   source venv/bin/activate
   ```
