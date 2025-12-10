import time
from aiogram import types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from handlers.states import SystemPromptStates
from utils import escape_markdown


def register_message_handlers(dp, user_service, message_service, yandex_gpt_service, bot):
    """Регистрирует обработчики обычных сообщений"""
    
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
        
        # Подготавливаем сообщение: добавляем в историю
        success, error_message = message_service.prepare_user_message(user_id, message.text)
        
        if not success:
            await message.answer(error_message)
            return
        
        # Получаем данные для запроса к LLM
        history, system_prompt, temperature, max_tokens = message_service.get_llm_request_data(user_id)
        
        # Измеряем время выполнения запроса к LLM
        start_time = time.time()
        # Отправляем запрос в YandexGPT
        response, usage = await yandex_gpt_service.send_message(history, system_prompt, temperature, max_tokens)
        end_time = time.time()
        response_time = end_time - start_time
        
        # Отправляем информацию о токенах во входном промпте (если доступна)
        input_tokens = usage.get("inputTextTokens", 0)
        # Преобразуем в int на случай, если значение пришло как строка
        input_tokens = int(input_tokens) if input_tokens else 0
        if input_tokens > 0:
            await message.answer(f"Промпт состоит из: {input_tokens} токенов")
        
        # Обрабатываем ответ: используем информацию о токенах из API и добавляем в историю
        success, response_with_tokens, response_tokens = await message_service.process_llm_response(user_id, response, response_time, usage)
        
        # Отправляем ответ пользователю с информацией о токенах
        await message.answer(response_with_tokens, parse_mode="Markdown")

