#!/bin/bash
set -e  # Скрипт упадёт при любой ошибке

echo "📥 Обновляем код с GitHub..."
git pull

echo "🐍 Активируем виртуальное окружение..."
source venv/bin/activate

echo "🐍 Устанавливаем зависимости Python..."
pip install -r requirements.txt

echo "🧰 Устанавливаем зависимости Node.js..."
npm install

echo "📦 Собираем статику Django..."
python manage.py collectstatic --noinput

echo "📋 Накатываем миграции..."
python manage.py migrate

echo "🔁 Перезапускаем сервис star-burger.service..."
sudo systemctl restart star-burger

echo "🌍 Загружаем переменные окружения..."
# Защита от пробелов и переносов строк
export $(grep -v '^#' .env | xargs -d '\n')

echo "🔎 Получаем текущий хеш коммита..."
COMMIT_HASH=$(git rev-parse HEAD)

echo "🚀 Отправляем информацию о деплое в Rollbar..."
curl -s -X POST https://api.rollbar.com/api/1/deploy/ \
  -H "Content-Type: application/json" \
  -d "{
    \"access_token\": \"${ROLLBAR_TOKEN}\",
    \"environment\": \"production\",
    \"revision\": \"${COMMIT_HASH}\"
  }" > /dev/null

echo "✅ Деплой завершён успешно!"





