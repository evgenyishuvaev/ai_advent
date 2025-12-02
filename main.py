import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp

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

# URL для Yandex GPT API
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


async def send_to_yandex_gpt(user_message: str) -> str:
    """
    Отправляет сообщение пользователя в Yandex GPT и возвращает ответ модели
    
    Args:
        user_message: Сообщение пользователя
        
    Returns:
        Ответ от Yandex GPT
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        # "x-folder-id": f"{YANDEX_FOLDER_ID}"
    }
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "system",
                "text": 'не используй в ответе markdown. любой твой ответ должен быть возвращен в соответствии со схемой json: {"user_msg": "<сообщение пользователя>", "response": "<ответ на сообщение пользователя>"}.'
            },
            {
                "role": "user",
                "text": user_message
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                YANDEX_GPT_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Извлекаем текст ответа из структуры ответа Yandex GPT
                    if "result" in data and "alternatives" in data["result"]:
                        if len(data["result"]["alternatives"]) > 0:
                            return data["result"]["alternatives"][0]["message"]["text"]
                    return "Не удалось получить ответ от модели."
                else:
                    error_text = await response.text()
                    return f"Ошибка API Yandex GPT (код {response.status}): {error_text}"
    except asyncio.TimeoutError:
        return "Превышено время ожидания ответа от Yandex GPT. Попробуйте позже."
    except Exception as e:
        return f"Произошла ошибка при обращении к Yandex GPT: {str(e)}"


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот с интеграцией Yandex GPT. Просто отправь мне любое сообщение, "
        "и я передам его в Yandex GPT, а затем отправлю тебе ответ модели!"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n\n"
        "Просто отправь мне любое сообщение, и я передам его в Yandex GPT, "
        "а затем отправлю тебе ответ модели!"
    )


@dp.message()
async def handle_message(message: types.Message):
    """Обработчик всех сообщений - отправляет в Yandex GPT и возвращает ответ"""
    # Проверяем, что сообщение содержит текст
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Показываем индикатор печати
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Отправляем сообщение в Yandex GPT
    response = await send_to_yandex_gpt(message.text)
    
    # Отправляем ответ пользователю
    await message.answer(response)


async def main():
    """Главная функция для запуска бота"""
    print("Бот запущен...")
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
