import asyncio
from aiogram import Bot, Dispatcher
from config import config
from services.yandex_gpt_service import YandexGPTService
from services.user_service import UserService
from services.message_service import MessageService
from services.history_formatter_service import HistoryFormatterService
from services.token_service import TokenService
from repositories.database import Database
from repositories.user_repository import UserRepository
from repositories.message_repository import MessageRepository
from handlers import setup_handlers

# Инициализируем базу данных
database = Database(db_path=config.db_path)

# Инициализируем репозитории
user_repository = UserRepository(database)
message_repository = MessageRepository(database)

# Инициализируем бота и диспетчер
bot = Bot(token=config.bot_token)
dp = Dispatcher()

# Инициализируем сервисы
yandex_gpt_service = YandexGPTService(
    api_key=config.yandex_api_key,
    folder_id=config.yandex_folder_id,
    model=config.yandex_model
)
user_service = UserService(user_repository, message_repository)
token_service = TokenService()
message_service = MessageService(user_service, yandex_gpt_service, token_service)
history_formatter = HistoryFormatterService()

# Регистрируем все хендлеры
setup_handlers(dp, user_service, message_service, yandex_gpt_service, history_formatter, bot)


async def main():
    """Главная функция для запуска бота"""
    # Подключаемся к базе данных
    await database.connect()
    try:
        print("Бот запущен...")
        # Запускаем polling
        await dp.start_polling(bot)
    finally:
        # Закрываем подключение к базе данных
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
