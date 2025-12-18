import logging
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from handlers.states import SystemPromptStates
from utils import escape_markdown, escape_html

logger = logging.getLogger(__name__)


def register_command_handlers(dp, user_service, history_formatter, mcp_service=None, daily_task_service=None):
    """Регистрирует все командные хендлеры"""
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        """Обработчик команды /start"""
        user_id = message.from_user.id
        # Очищаем историю при старте
        await user_service.clear_history(user_id)
        
        await message.answer(
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "Я бот с интеграцией Yandex GPT. Просто отправь мне любое сообщение, "
            "и я передам его в Yandex GPT, а затем отправлю тебе ответ модели!\n\n"
            "Бот помнит контекст предыдущих сообщений. Используй /clear для очистки истории.\n"
            "Используй /system для установки или изменения системного промпта (опционально).\n"
            "Используй /temperature для настройки коэффициента температуры.\n"
            "Используй /set_max_tokens для настройки максимального количества токенов в ответе."
        )

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        """Обработчик команды /help"""
        await message.answer(
            "Доступные команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать эту справку\n"
            "/clear - Очистить историю сообщений\n"
            "/system - Установить или просмотреть системный промпт (опционально)\n"
            "/clear_system - Очистить системный промпт\n"
            "/temperature - Установить коэффициент температуры (0.0-2.0)\n"
            "/set_max_tokens - Установить максимальное количество токенов в ответе (1-8000)\n"
            "/history - Показать историю сообщений\n"
            "/mcp_tools - Показать доступные инструменты MCP сервера\n"
            "/daily_analysis - Получить ежедневный анализ задач (не дожидаясь планировщика)\n\n"
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
            system_prompt = command_args[1].strip()
            
            # Разрешаем пустой промпт (установка пустой строки)
            await user_service.set_system_prompt(user_id, system_prompt)
            
            if system_prompt:
                # Экранируем промпт для безопасного отображения (используем HTML)
                system_prompt_preview = system_prompt[:100] + ('...' if len(system_prompt) > 100 else '')
                system_prompt_escaped = escape_html(system_prompt_preview)
                await message.answer(
                    f"Системный промпт установлен! ✅\n\n"
                    f"Текущий промпт: <code>{system_prompt_escaped}</code>",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "Системный промпт очищен. ✅\n\n"
                    "Бот будет работать без системного промпта."
                )
            await state.clear()
        else:
            # Если промпта нет, показываем текущий и запрашиваем новый
            current_prompt = await user_service.get_system_prompt(user_id)
            if current_prompt:
                # Экранируем промпт для безопасного отображения (используем HTML)
                current_prompt_escaped = escape_html(current_prompt)
                await message.answer(
                    f"Текущий системный промпт:\n\n<code>{current_prompt_escaped}</code>\n\n"
                    "Отправь новый системный промпт для его замены, используй /clear_system для очистки, или /cancel для отмены.",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "Системный промпт не установлен.\n\n"
                    "Отправь системный промпт (это инструкция для модели, которая определяет её поведение), "
                    "или /cancel для отмены.\n\n"
                    "Примечание: системный промпт опционален, бот может работать и без него."
                )
            await state.set_state(SystemPromptStates.waiting_for_prompt)

    @dp.message(Command("clear_system"))
    async def cmd_clear_system(message: types.Message, state: FSMContext):
        """Обработчик команды /clear_system - очистка системного промпта"""
        user_id = message.from_user.id
        
        # Очищаем системный промпт (устанавливаем пустую строку)
        await user_service.set_system_prompt(user_id, "")
        
        await message.answer(
            "Системный промпт очищен. ✅\n\n"
            "Бот будет работать без системного промпта."
        )
        await state.clear()

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
                await user_service.set_temperature(user_id, temp_value)
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
            current_temp = await user_service.get_temperature(user_id)
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

    @dp.message(Command("set_max_tokens"))
    async def cmd_set_max_tokens(message: types.Message):
        """Обработчик команды /set_max_tokens - установка максимального количества токенов"""
        user_id = message.from_user.id
        
        # Проверяем, есть ли аргумент в команде
        command_args = message.text.split(maxsplit=1)
        if len(command_args) > 1:
            try:
                # Пытаемся преобразовать аргумент в int
                max_tokens_value = int(command_args[1])
                
                # Валидируем максимальное количество токенов
                is_valid, error_message = user_service.validate_max_tokens(max_tokens_value)
                if not is_valid:
                    await message.answer(
                        f"❌ {error_message}\n\n"
                        "Рекомендации:\n"
                        "• 100-500 - короткие ответы\n"
                        "• 500-1500 - средние ответы (по умолчанию 2000)\n"
                        "• 1500-4000 - длинные ответы\n"
                        "• 4000-8000 - очень длинные ответы"
                    )
                    return
                
                # Сохраняем максимальное количество токенов
                await user_service.set_max_tokens(user_id, max_tokens_value)
                await message.answer(
                    f"✅ Максимальное количество токенов установлено: {max_tokens_value}\n\n"
                    f"Следующие ответы будут ограничены этим количеством токенов."
                )
            except ValueError:
                await message.answer(
                    "❌ Неверный формат. Используй команду так:\n"
                    "/set_max_tokens 2000\n\n"
                    "Максимальное количество токенов должно быть целым числом от 1 до 8000."
                )
        else:
            # Если значения нет, показываем текущее
            current_max_tokens = await user_service.get_max_tokens(user_id)
            await message.answer(
                f"🔢 Текущее максимальное количество токенов: {current_max_tokens}\n\n"
                "Используй команду так:\n"
                "/set_max_tokens <значение>\n\n"
                "Диапазон: 1 - 8000\n\n"
                "Рекомендации:\n"
                "• 100-500 - короткие ответы\n"
                "• 500-1500 - средние ответы (по умолчанию 2000)\n"
                "• 1500-4000 - длинные ответы\n"
                "• 4000-8000 - очень длинные ответы"
            )

    @dp.message(Command("clear"))
    async def cmd_clear(message: types.Message):
        """Обработчик команды /clear - очищает историю сообщений пользователя"""
        user_id = message.from_user.id
        if await user_service.clear_history(user_id):
            await message.answer("История сообщений очищена. ✅")
        else:
            await message.answer("История сообщений уже пуста.")

    @dp.message(Command("history"))
    async def cmd_history(message: types.Message):
        """Обработчик команды /history - показывает историю сообщений"""
        user_id = message.from_user.id
        
        # Получаем историю
        history = await user_service.get_history(user_id)
        
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

    @dp.message(Command("mcp_tools"))
    async def cmd_mcp_tools(message: types.Message):
        """Обработчик команды /mcp_tools - показывает доступные инструменты MCP сервера(ов)"""
        if mcp_service is None:
            await message.answer(
                "❌ MCP сервис не инициализирован.\n\n"
                "Убедитесь, что MCP сервер настроен и доступен."
            )
            return
        
        # Проверяем подключение
        if not mcp_service.is_connected():
            await message.answer(
                "❌ MCP сервис не подключен к серверу(ам).\n\n"
                "Проверьте, что MCP сервер(ы) запущен(ы) и доступен(ы) по адресу(ам), указанному(ым) в конфигурации."
            )
            return
        
        try:
            # Получаем список инструментов
            tools = await mcp_service.list_tools()
            
            if not tools:
                await message.answer("📋 На MCP сервере(ах) нет доступных инструментов.")
                return
            
            # Определяем, сколько серверов подключено (для менеджера)
            from services.mcp_service_manager import MCPServiceManager
            if isinstance(mcp_service, MCPServiceManager):
                connected_servers = mcp_service.get_connected_servers()
                server_info = f" ({len(connected_servers)} сервер(ов))"
            else:
                server_info = ""
            
            # Форматируем список инструментов
            tools_text = f"🔧 Доступные инструменты MCP сервера(ов){server_info}:\n\n"
            
            for i, tool in enumerate(tools, 1):
                # Поддерживаем как словари, так и объекты с атрибутами
                if isinstance(tool, dict):
                    tool_name = tool.get("name", "Неизвестный инструмент")
                    tool_description = tool.get("description", "Описание отсутствует")
                else:
                    # Если это объект с атрибутами
                    tool_name = getattr(tool, "name", "Неизвестный инструмент")
                    tool_description = getattr(tool, "description", "Описание отсутствует")
                
                # Преобразуем в строки, если нужно
                tool_name = str(tool_name) if tool_name else "Неизвестный инструмент"
                tool_description = str(tool_description) if tool_description else "Описание отсутствует"
                
                # Ограничиваем длину описания для читаемости
                if len(tool_description) > 200:
                    tool_description = tool_description[:200] + "..."
                
                tools_text += f"{i}. *{escape_markdown(tool_name)}*\n"
                tools_text += f"   {escape_markdown(tool_description)}\n\n"
                
                # Если список слишком длинный, разбиваем на части
                if len(tools_text) > 3000:
                    # Отправляем текущую часть
                    await message.answer(tools_text, parse_mode="Markdown")
                    tools_text = ""
            
            # Отправляем оставшуюся часть
            if tools_text:
                await message.answer(tools_text, parse_mode="Markdown")
                
        except Exception as e:
            await message.answer(
                f"❌ Ошибка при получении списка инструментов:\n\n"
                f"`{escape_markdown(str(e))}`",
                parse_mode="Markdown"
            )

    @dp.message(Command("daily_analysis"))
    async def cmd_daily_analysis(message: types.Message):
        """Обработчик команды /daily_analysis - получение ежедневного анализа задач"""
        if daily_task_service is None:
            await message.answer(
                "❌ Сервис ежедневного анализа не инициализирован."
            )
            return
        
        user_id = message.from_user.id
        
        # Отправляем сообщение о начале анализа
        await message.answer("📊 Формирую ежедневный анализ задач... Пожалуйста, подождите.")
        
        # Вызываем метод анализа для текущего пользователя
        try:
            await daily_task_service.send_daily_analysis(user_id)
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /daily_analysis для пользователя {user_id}: {e}", exc_info=True)
            await message.answer(
                "❌ Произошла ошибка при формировании ежедневного анализа задач. Попробуйте позже."
            )

