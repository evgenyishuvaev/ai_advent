import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

# Словарь для хранения истории сообщений каждого пользователя
# Ключ: user_id, Значение: список сообщений в формате {"role": "user"/"assistant", "text": "..."}
user_histories: dict[int, list[dict[str, str]]] = {}

# Словарь для хранения системных промптов каждого пользователя
# Ключ: user_id, Значение: системный промпт (строка)
user_system_prompts: dict[int, str] = {}

# Словарь для хранения температуры каждого пользователя
# Ключ: user_id, Значение: температура (float, по умолчанию 0.6)
user_temperatures: dict[int, float] = {}
DEFAULT_TEMPERATURE = 0.6


class SystemPromptStates(StatesGroup):
    """Состояния FSM для запроса системного промпта"""
    waiting_for_prompt = State()


async def send_to_yandex_gpt(messages_history: list[dict[str, str]], system_prompt: str = None, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Отправляет историю сообщений в Yandex GPT и возвращает ответ модели
    
    Args:
        messages_history: Список сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
        system_prompt: Системный промпт (опционально)
        temperature: Коэффициент температуры для генерации (по умолчанию 0.6)
        
    Returns:
        Ответ от Yandex GPT
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        # "x-folder-id": f"{YANDEX_FOLDER_ID}"
    }
    
    # Формируем список сообщений с системным промптом в начале, если он есть
    messages = []
    if system_prompt:
        messages.append({
            "role": "system",
            "text": system_prompt
        })
    messages.extend(messages_history)
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": 2000
        },
        "messages": messages
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
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    # Очищаем историю при старте
    user_histories[user_id] = []
    
    # Проверяем наличие системного промпта
    if user_id not in user_system_prompts or not user_system_prompts[user_id]:
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
        user_system_prompts[user_id] = system_prompt
        await message.answer(
            f"Системный промпт установлен! ✅\n\n"
            f"Текущий промпт: {system_prompt[:100]}{'...' if len(system_prompt) > 100 else ''}"
        )
        await state.clear()
    else:
        # Если промпта нет, показываем текущий и запрашиваем новый
        if user_id in user_system_prompts and user_system_prompts[user_id]:
            current_prompt = user_system_prompts[user_id]
            await message.answer(
                f"Текущий системный промпт:\n\n{current_prompt}\n\n"
                "Отправь новый системный промпт для его замены, или /cancel для отмены."
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
            
            # Проверяем диапазон температуры (обычно 0.0 - 2.0)
            if temp_value < 0.0 or temp_value > 2.0:
                await message.answer(
                    "❌ Температура должна быть в диапазоне от 0.0 до 2.0.\n\n"
                    "Рекомендации:\n"
                    "• 0.0-0.3 - более детерминированные, точные ответы\n"
                    "• 0.4-0.7 - сбалансированные ответы (по умолчанию 0.6)\n"
                    "• 0.8-1.5 - более творческие и разнообразные ответы\n"
                    "• 1.6-2.0 - очень креативные, но менее предсказуемые ответы"
                )
                return
            
            # Сохраняем температуру
            user_temperatures[user_id] = temp_value
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
        current_temp = user_temperatures.get(user_id, DEFAULT_TEMPERATURE)
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
    if user_id in user_histories:
        user_histories[user_id] = []
        await message.answer("История сообщений очищена. ✅")
    else:
        await message.answer("История сообщений уже пуста.")


def escape_markdown(text: str) -> str:
    """Экранирует специальные символы Markdown для Telegram (обычный Markdown)"""
    # Экранируем основные символы, которые могут вызвать проблемы в Markdown
    # Для обычного Markdown нужно экранировать: *, _, [, ], `
    escape_chars = ['*', '_', '[', ']', '`']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    """Обработчик команды /history - показывает историю сообщений"""
    user_id = message.from_user.id
    
    # Проверяем наличие истории
    if user_id not in user_histories or not user_histories[user_id]:
        await message.answer("История сообщений пуста. Начни диалог, отправив сообщение боту.")
        return
    
    history = user_histories[user_id]
    
    # Формируем отформатированные сообщения
    formatted_messages = []
    
    for i, msg in enumerate(history):
        role = msg.get("role", "")
        text = msg.get("text", "")
        
        # Экранируем специальные символы Markdown
        text_escaped = escape_markdown(text)
        
        if i == 0:
            # Первое сообщение выделяем жирным
            if role == "user":
                formatted_messages.append(f"**👤 {text_escaped}**")
            elif role == "assistant":
                formatted_messages.append(f"**🤖 {text_escaped}**")
            else:
                formatted_messages.append(f"**{text_escaped}**")
        else:
            # Остальные сообщения с эмодзи
            if role == "user":
                formatted_messages.append(f"👤 {text_escaped}")
            elif role == "assistant":
                formatted_messages.append(f"🤖 {text_escaped}")
            else:
                formatted_messages.append(text_escaped)
    
    # Telegram ограничение на длину сообщения - 4096 символов
    max_length = 4096
    
    # Формируем заголовок
    header = f"📜 История сообщений ({len(history)} сообщений):\n\n"
    
    # Объединяем все сообщения
    full_history = "\n\n".join(formatted_messages)
    full_text = header + full_history
    
    # Проверяем, помещается ли всё в одно сообщение
    if len(full_text) <= max_length:
        # Отправляем одним сообщением
        await message.answer(full_text, parse_mode="Markdown")
    else:
        # Разбиваем на части
        parts = []
        current_part = []
        is_first_part = True
        
        for msg_text in formatted_messages:
            # Формируем текущую часть для проверки длины
            if is_first_part:
                # Для первой части учитываем заголовок
                test_part = header + "\n\n".join(current_part + [msg_text]) if current_part else header + msg_text
            else:
                # Для остальных частей заголовка нет
                test_part = "\n\n".join(current_part + [msg_text]) if current_part else msg_text
            
            # Проверяем, поместится ли сообщение в текущую часть
            if len(test_part) > max_length and current_part:
                # Сохраняем текущую часть и начинаем новую
                if is_first_part:
                    # Первая часть с заголовком
                    parts.append(header + "\n\n".join(current_part))
                    is_first_part = False
                else:
                    # Остальные части без заголовка
                    parts.append("\n\n".join(current_part))
                current_part = [msg_text]
            else:
                # Добавляем сообщение в текущую часть
                current_part.append(msg_text)
        
        # Добавляем последнюю часть
        if current_part:
            if is_first_part:
                # Если это единственная часть (не должно случиться, но на всякий случай)
                parts.append(header + "\n\n".join(current_part))
            else:
                # Продолжение истории
                parts.append("\n\n".join(current_part))
        
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
    user_system_prompts[user_id] = message.text
    await message.answer(
        f"Системный промпт установлен! ✅\n\n"
        f"Текущий промпт: {message.text[:100]}{'...' if len(message.text) > 100 else ''}\n\n"
        "Теперь можешь отправлять сообщения боту."
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
    
    # Проверяем наличие системного промпта
    if user_id not in user_system_prompts or not user_system_prompts[user_id]:
        await message.answer(
            "Системный промпт не установлен. Пожалуйста, используй команду /system для его установки."
        )
        return
    
    # Получаем или создаем историю для пользователя
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # Добавляем сообщение пользователя в историю
    user_histories[user_id].append({
        "role": "user",
        "text": message.text
    })
    
    # Показываем индикатор печати
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Получаем системный промпт пользователя
    system_prompt = user_system_prompts.get(user_id)
    
    # Получаем температуру пользователя (по умолчанию DEFAULT_TEMPERATURE)
    temperature = user_temperatures.get(user_id, DEFAULT_TEMPERATURE)
    
    # Отправляем всю историю сообщений в Yandex GPT с системным промптом и температурой
    response = await send_to_yandex_gpt(user_histories[user_id], system_prompt, temperature)
    
    # Добавляем ответ ассистента в историю
    user_histories[user_id].append({
        "role": "assistant",
        "text": response
    })
    
    # Отправляем ответ пользователю
    await message.answer(response)


async def main():
    """Главная функция для запуска бота"""
    print("Бот запущен...")
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
