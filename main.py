import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения. Создайте файл .env и добавьте BOT_TOKEN=ваш_токен")

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я эхо-бот. Просто отправь мне любое сообщение, и я отправлю его обратно!"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n\n"
        "Просто отправь мне любое сообщение, и я отправлю его обратно!"
    )


@dp.message()
async def echo_message(message: types.Message):
    """Обработчик всех остальных сообщений - отправляет сообщение обратно"""
    await message.answer(f"Вы написали: {message.text}")


async def main():
    """Главная функция для запуска бота"""
    print("Бот запущен...")
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
