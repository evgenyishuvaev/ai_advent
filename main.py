import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from services.yandex_gpt_service import YandexGPTService
from services.user_service import UserService
from services.message_service import MessageService
from services.history_formatter_service import HistoryFormatterService
from handlers import setup_handlers

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токены и настройки из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt/latest")

# Проверяем наличие обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения. Создайте файл .env и добавьте BOT_TOKEN=ваш_токен")

if not YANDEX_API_KEY:
    raise ValueError("YANDEX_API_KEY не найден в переменных окружения. Добавьте YANDEX_API_KEY=ваш_ключ в .env")

if not YANDEX_FOLDER_ID:
    raise ValueError("YANDEX_FOLDER_ID не найден в переменных окружения. Добавьте YANDEX_FOLDER_ID=ваш_folder_id в .env")

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализируем сервисы
yandex_gpt_service = YandexGPTService(
    api_key=YANDEX_API_KEY,
    folder_id=YANDEX_FOLDER_ID,
    model=YANDEX_MODEL
)
user_service = UserService()
message_service = MessageService(user_service, yandex_gpt_service)
history_formatter = HistoryFormatterService()

# Регистрируем все хендлеры
setup_handlers(dp, user_service, message_service, yandex_gpt_service, history_formatter, bot)


async def main():
    """Главная функция для запуска бота"""
    print("Бот запущен...")
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
