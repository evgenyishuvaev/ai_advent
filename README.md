# AI Advent - Telegram Bot with Yandex GPT

Telegram бот на основе библиотеки aiogram с интеграцией Yandex GPT. Все сообщения пользователя отправляются в Yandex GPT, а ответ модели возвращается пользователю.

## Установка и настройка

1. Убедитесь, что у вас установлен `uv`:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Установите зависимости (уже установлены через `uv add`):
   ```bash
   uv sync
   ```

3. Получите токен Telegram бота:
   - Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
   - Отправьте команду `/newbot`
   - Следуйте инструкциям для создания бота
   - Скопируйте полученный токен

4. Настройте Yandex Cloud для работы с Yandex GPT:
   - Зарегистрируйтесь в [Yandex Cloud](https://cloud.yandex.ru/)
   - Создайте каталог в Yandex Cloud
   - Получите API ключ в разделе "Сервисные аккаунты" или "API ключи"
   - Найдите ID вашего каталога в консоли Yandex Cloud
   - Убедитесь, что у вас включен сервис Yandex GPT

5. Создайте файл `.env` в корне проекта:
   ```bash
   cp env.example .env
   ```
   
   Затем отредактируйте `.env` и заполните все необходимые переменные:
   ```
   BOT_TOKEN=your_telegram_bot_token
   YANDEX_API_KEY=your_yandex_api_key
   YANDEX_FOLDER_ID=your_folder_id
   YANDEX_MODEL=yandexgpt/latest  # опционально
   ```

## Запуск

Запустите бота командой:
```bash
uv run main.py
```

## Функциональность

- `/start` - Приветствие и начало работы с ботом
- `/help` - Справка по командам
- Любое текстовое сообщение - отправляется в Yandex GPT, ответ модели возвращается пользователю

## Структура проекта

```
ai_advent/
├── main.py           # Основной файл с кодом бота
├── pyproject.toml    # Конфигурация проекта и зависимости
├── README.md         # Этот файл
└── .env              # Файл с токеном бота (не коммитится в git)
```

## Технологии

- Python 3.12+
- [aiogram](https://docs.aiogram.dev/) - асинхронная библиотека для работы с Telegram Bot API
- [Yandex GPT](https://cloud.yandex.ru/docs/yandexgpt/) - языковая модель от Yandex
- [aiohttp](https://docs.aiohttp.org/) - асинхронная HTTP библиотека для работы с API
- [python-dotenv](https://github.com/theskumar/python-dotenv) - для работы с переменными окружения
- [uv](https://github.com/astral-sh/uv) - современный менеджер пакетов Python

## Настройка Yandex GPT

Для работы бота необходимо:
1. Создать каталог в Yandex Cloud
2. Получить API ключ (IAM токен или API ключ сервисного аккаунта)
3. Указать ID каталога в переменной окружения `YANDEX_FOLDER_ID`
4. Убедиться, что у вас есть доступ к сервису Yandex GPT

Подробная документация: https://cloud.yandex.ru/docs/yandexgpt/

