import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.yandex_gpt_service import YandexGPTService
from services.user_service import UserService
from services.message_service import MessageService
from services.history_formatter_service import HistoryFormatterService
from services.token_service import TokenService
from utils import escape_markdown

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
token_service = TokenService()
message_service = MessageService(user_service, yandex_gpt_service, token_service)
history_formatter = HistoryFormatterService()


class SystemPromptStates(StatesGroup):
    """Состояния FSM для запроса системного промпта"""
    waiting_for_prompt = State()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    # Очищаем историю при старте
    user_service.clear_history(user_id)
    
    # Проверяем наличие системного промпта
    if not user_service.has_system_prompt(user_id):
        await message.answer(
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "Я бот с интеграцией Yandex GPT.\n\n"
            "Для начала работы необходимо задать системный промпт. "
            "Это инструкция для модели, которая определяет её поведение и стиль ответов.\n\n"
            "Пожалуйста, отправь системный промпт (или используй команду /system для его установки)."
        )
        await state.set_state(SystemPromptStates.waiting_for_prompt)
    else:
        await message.answer(
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "Я бот с интеграцией Yandex GPT. Просто отправь мне любое сообщение, "
            "и я передам его в Yandex GPT, а затем отправлю тебе ответ модели!\n\n"
            "Бот помнит контекст предыдущих сообщений. Используй /clear для очистки истории.\n"
            "Используй /system для изменения системного промпта.\n"
            "Используй /temperature для настройки коэффициента температуры."
        )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/clear - Очистить историю сообщений\n"
        "/system - Установить или просмотреть системный промпт\n"
        "/temperature - Установить коэффициент температуры (0.0-2.0)\n"
        "/history - Показать историю сообщений\n\n"
        "Просто отправь мне любое сообщение, и я передам его в Yandex GPT, "
        "а затем отправлю тебе ответ модели! Бот помнит контекст предыдущих сообщений."
    )


@dp.message(Command("system"))
async def cmd_system(message: types.Message, state: FSMContext):
    """Обработчик команды /system - установка системного промпта"""
    user_id = message.from_user.id
    
    # Проверяем, есть ли аргумент в команде
    command_args = message.text.split(maxsplit=1)
    if len(command_args) > 1:
        # Если промпт указан в команде
        system_prompt = command_args[1]
        user_service.set_system_prompt(user_id, system_prompt)
        # Экранируем промпт для безопасного отображения
        system_prompt_escaped = escape_markdown(system_prompt[:100] + ('...' if len(system_prompt) > 100 else ''))
        await message.answer(
            f"Системный промпт установлен! ✅\n\n"
            f"Текущий промпт: {system_prompt_escaped}",
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        # Если промпта нет, показываем текущий и запрашиваем новый
        current_prompt = user_service.get_system_prompt(user_id)
        if current_prompt:
            # Экранируем промпт для безопасного отображения
            current_prompt_escaped = escape_markdown(current_prompt)
            await message.answer(
                f"Текущий системный промпт:\n\n{current_prompt_escaped}\n\n"
                "Отправь новый системный промпт для его замены, или /cancel для отмены.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "Системный промпт не установлен.\n\n"
                "Отправь системный промпт (это инструкция для модели, которая определяет её поведение), "
                "или /cancel для отмены."
            )
        await state.set_state(SystemPromptStates.waiting_for_prompt)


@dp.message(Command("temperature"))
async def cmd_temperature(message: types.Message):
    """Обработчик команды /temperature - установка коэффициента температуры"""
    user_id = message.from_user.id
    
    # Проверяем, есть ли аргумент в команде
    command_args = message.text.split(maxsplit=1)
    if len(command_args) > 1:
        try:
            # Пытаемся преобразовать аргумент в float
            temp_value = float(command_args[1])
            
            # Валидируем температуру
            is_valid, error_message = user_service.validate_temperature(temp_value)
            if not is_valid:
                await message.answer(
                    f"❌ {error_message}\n\n"
                    "Рекомендации:\n"
                    "• 0.0-0.3 - более детерминированные, точные ответы\n"
                    "• 0.4-0.7 - сбалансированные ответы (по умолчанию 0.6)\n"
                    "• 0.8-1.5 - более творческие и разнообразные ответы\n"
                    "• 1.6-2.0 - очень креативные, но менее предсказуемые ответы"
                )
                return
            
            # Сохраняем температуру
            user_service.set_temperature(user_id, temp_value)
            await message.answer(
                f"✅ Температура установлена: {temp_value}\n\n"
                f"Следующие ответы будут генерироваться с этим коэффициентом температуры."
            )
        except ValueError:
            await message.answer(
                "❌ Неверный формат. Используй команду так:\n"
                "/temperature 0.6\n\n"
                "Температура должна быть числом от 0.0 до 2.0."
            )
    else:
        # Если температуры нет, показываем текущую
        current_temp = user_service.get_temperature(user_id)
        await message.answer(
            f"🌡 Текущая температура: {current_temp}\n\n"
            "Используй команду так:\n"
            "/temperature <значение>\n\n"
            "Диапазон: 0.0 - 2.0\n\n"
            "Рекомендации:\n"
            "• 0.0-0.3 - более детерминированные, точные ответы\n"
            "• 0.4-0.7 - сбалансированные ответы (по умолчанию 0.6)\n"
            "• 0.8-1.5 - более творческие и разнообразные ответы\n"
            "• 1.6-2.0 - очень креативные, но менее предсказуемые ответы"
        )


@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """Обработчик команды /clear - очищает историю сообщений пользователя"""
    user_id = message.from_user.id
    if user_service.clear_history(user_id):
        await message.answer("История сообщений очищена. ✅")
    else:
        await message.answer("История сообщений уже пуста.")


@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    """Обработчик команды /history - показывает историю сообщений"""
    user_id = message.from_user.id
    
    # Получаем историю
    history = user_service.get_history(user_id)
    
    # Проверяем наличие истории
    if not history:
        await message.answer("История сообщений пуста. Начни диалог, отправив сообщение боту.")
        return
    
    # Форматируем и разбиваем историю на части
    parts = history_formatter.format_and_split_history(history)
    
    # Отправляем все части
    for part in parts:
        await message.answer(part, parse_mode="Markdown")


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Обработчик команды /cancel - отменяет текущую операцию"""
    await state.clear()
    await message.answer("Операция отменена.")


@dp.message(StateFilter(SystemPromptStates.waiting_for_prompt))
async def process_system_prompt(message: types.Message, state: FSMContext):
    """Обработчик для получения системного промпта от пользователя"""
    user_id = message.from_user.id
    
    if not message.text:
        await message.answer("Пожалуйста, отправь текстовый системный промпт.")
        return
    
    # Сохраняем системный промпт
    user_service.set_system_prompt(user_id, message.text)
    # Экранируем промпт для безопасного отображения
    prompt_preview = message.text[:100] + ('...' if len(message.text) > 100 else '')
    prompt_preview_escaped = escape_markdown(prompt_preview)
    await message.answer(
        f"Системный промпт установлен! ✅\n\n"
        f"Текущий промпт: {prompt_preview_escaped}\n\n"
        "Теперь можешь отправлять сообщения боту.",
        parse_mode="Markdown"
    )
    await state.clear()


@dp.message()
async def handle_message(message: types.Message):
    """Обработчик всех сообщений - отправляет в Yandex GPT и возвращает ответ"""
    # Проверяем, что сообщение содержит текст
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    user_id = message.from_user.id
    
    # Показываем индикатор печати
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Подготавливаем сообщение: подсчитываем токены и добавляем в историю
    success, prompt_tokens, error_message = message_service.prepare_user_message(user_id, message.text)
    
    if not success:
        await message.answer(error_message)
        return
    
    # Отправляем информацию о количестве токенов в промпте сразу (параллельно с ожиданием ответа)
    await message.answer(f"Промпт состоит из: {prompt_tokens} токенов")
    
    # Получаем данные для запроса к LLM
    history, system_prompt, temperature = message_service.get_llm_request_data(user_id)
    
    # Отправляем запрос в YandexGPT
    response = await yandex_gpt_service.send_message(history, system_prompt, temperature)
    
    # Обрабатываем ответ: подсчитываем токены и добавляем в историю
    success, response_with_tokens, response_tokens = await message_service.process_llm_response(user_id, response)
    
    # Отправляем ответ пользователю с информацией о токенах
    await message.answer(response_with_tokens, parse_mode="Markdown")


async def main():
    """Главная функция для запуска бота"""
    print("Бот запущен...")
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
