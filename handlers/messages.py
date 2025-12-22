import time
import os
import io
import logging
from aiogram import types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from handlers.states import SystemPromptStates
from utils import escape_markdown, escape_html

logger = logging.getLogger(__name__)


def register_message_handlers(dp, user_service, message_service, yandex_gpt_service, bot, document_service=None):
    """Регистрирует обработчики обычных сообщений"""
    
    @dp.message(StateFilter(SystemPromptStates.waiting_for_prompt))
    async def process_system_prompt(message: types.Message, state: FSMContext):
        """Обработчик для получения системного промпта от пользователя"""
        user_id = message.from_user.id
        
        if not message.text:
            await message.answer(
                "Пожалуйста, отправь текстовый системный промпт.\n\n"
                "Для очистки системного промпта используй команду /clear_system."
            )
            return
        
        # Сохраняем системный промпт
        system_prompt = message.text.strip()
        await user_service.set_system_prompt(user_id, system_prompt)
        
        # Экранируем промпт для безопасного отображения (используем HTML)
        prompt_preview = system_prompt[:100] + ('...' if len(system_prompt) > 100 else '')
        prompt_preview_escaped = escape_html(prompt_preview)
        await message.answer(
            f"Системный промпт установлен! ✅\n\n"
            f"Текущий промпт: <code>{prompt_preview_escaped}</code>\n\n"
            "Теперь можешь отправлять сообщения боту.",
            parse_mode="HTML"
        )
        
        await state.clear()

    @dp.message()
    async def handle_message(message: types.Message):
        """Обработчик всех сообщений - отправляет в Yandex GPT и возвращает ответ"""
        # Проверяем, есть ли документ в сообщении (обработка загрузки файлов)
        if message.document and document_service is not None:
            user_id = message.from_user.id
            document = message.document
            filename = document.file_name or "unknown.txt"
            
            # Проверяем размер файла (ограничиваем до 10MB)
            max_file_size = 10 * 1024 * 1024  # 10MB
            if document.file_size and document.file_size > max_file_size:
                await message.answer(
                    f"❌ Файл слишком большой. Максимальный размер: 10MB.\n"
                    f"Размер вашего файла: {document.file_size / 1024 / 1024:.2f}MB"
                )
                return
            
            # Отправляем сообщение о начале обработки
            processing_msg = await message.answer("📄 Обрабатываю файл... Пожалуйста, подождите.")
            
            try:
                # Скачиваем файл
                file = await bot.get_file(document.file_id)
                file_path = file.file_path
                logger.info(f"Скачивание файла {filename}, размер: {document.file_size} байт")
                
                # Скачиваем содержимое файла
                # В aiogram 3.x download_file может возвращать разные типы
                file_destination = await bot.download_file(file_path)
                
                # Читаем содержимое файла
                # Если это bytes, используем напрямую
                if isinstance(file_destination, bytes):
                    file_bytes = file_destination
                elif hasattr(file_destination, 'read'):
                    # Если это файловый объект, читаем его полностью
                    try:
                        # Пытаемся прочитать весь файл
                        file_bytes = file_destination.read()
                        # Если read() вернул не все, читаем остальное
                        if hasattr(file_destination, 'seek'):
                            file_destination.seek(0)
                            chunks = []
                            while True:
                                chunk = file_destination.read(8192)  # Читаем по 8KB
                                if not chunk:
                                    break
                                chunks.append(chunk)
                            file_bytes = b''.join(chunks)
                    except Exception as e:
                        logger.error(f"Ошибка при чтении файла: {e}")
                        # Пытаемся альтернативный способ
                        if hasattr(file_destination, 'getvalue'):
                            file_bytes = file_destination.getvalue()
                        else:
                            raise
                    finally:
                        # Закрываем файл, если нужно
                        if hasattr(file_destination, 'close'):
                            try:
                                file_destination.close()
                            except:
                                pass
                elif hasattr(file_destination, 'getvalue'):
                    # Если это BytesIO или подобный объект
                    file_bytes = file_destination.getvalue()
                else:
                    # Пытаемся преобразовать в bytes
                    file_bytes = bytes(file_destination)
                
                # Проверяем размер файла
                expected_size = document.file_size if document.file_size else None
                actual_size = len(file_bytes)
                logger.info(f"Файл {filename} прочитан: {actual_size} байт" + 
                          (f" (ожидалось: {expected_size} байт)" if expected_size else ""))
                
                # Предупреждение, если размер не совпадает
                if expected_size and abs(actual_size - expected_size) > 10:
                    logger.warning(f"Размер файла не совпадает: ожидалось {expected_size}, получено {actual_size}")
                
                # Обрабатываем файл
                document_id = await document_service.process_file(
                    file_content=file_bytes,
                    filename=filename,
                    user_id=user_id,
                    file_path=file_path
                )
                
                await processing_msg.edit_text(
                    f"✅ Файл '{escape_markdown(filename)}' успешно загружен и обработан!\n\n"
                    f"Документ добавлен в базу знаний и будет использоваться при ответах на ваши вопросы.",
                    parse_mode="Markdown"
                )
                return
            except ValueError as e:
                await processing_msg.edit_text(f"❌ Ошибка: {str(e)}")
                return
            except Exception as e:
                logger.error(f"Ошибка при обработке файла {filename} для пользователя {user_id}: {e}", exc_info=True)
                await processing_msg.edit_text(
                    f"❌ Произошла ошибка при обработке файла. Попробуйте позже или проверьте формат файла."
                )
                return
        
        # Проверяем, что сообщение содержит текст
        if not message.text:
            await message.answer("Пожалуйста, отправьте текстовое сообщение.")
            return
        
        user_id = message.from_user.id
        
        # Показываем индикатор печати
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Подготавливаем сообщение: добавляем в историю
        success, error_message = await message_service.prepare_user_message(user_id, message.text)
        
        if not success:
            await message.answer(error_message)
            return
        
        # Получаем данные для запроса к LLM
        # Передаем текущий запрос для режима WIKI
        history, system_prompt, temperature, max_tokens = await message_service.get_llm_request_data(user_id, current_query=message.text)
        
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

