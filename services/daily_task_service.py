"""Сервис для выполнения ежедневных задач."""

import logging
from datetime import datetime
from typing import Optional
from aiogram import Bot
from repositories.user_repository import UserRepository
from repositories.message_repository import MessageRepository
from services.yandex_gpt_service import YandexGPTService
from services.mcp_service import MCPService

logger = logging.getLogger(__name__)


class DailyTaskService:
    """Сервис для выполнения ежедневных задач в определенное время."""
    
    DAILY_ANALYSIS_PROMPT = (
        "Используй доступные MCP инструменты для получения списка моих задач за сегодня. "
        "Посмотри сколько задач я выполнил за сегодня и сколько не выполнил. "
        "Проанализируй с чем были связаны задачи которые я не выполнил. "
        "Заверши мотивирующей цитатой"
    )
    
    def __init__(
        self,
        bot: Bot,
        user_repository: UserRepository,
        message_repository: MessageRepository,
        yandex_gpt_service: YandexGPTService,
        mcp_service: Optional[MCPService] = None
    ):
        """
        Инициализация сервиса ежедневных задач.
        
        Args:
            bot: Экземпляр Bot для отправки сообщений
            user_repository: Репозиторий для работы с пользователями
            message_repository: Репозиторий для работы с сообщениями
            yandex_gpt_service: Сервис для работы с YandexGPT
            mcp_service: Сервис для работы с MCP сервером (опционально)
        """
        self.bot = bot
        self.user_repository = user_repository
        self.message_repository = message_repository
        self.yandex_gpt_service = yandex_gpt_service
        self.mcp_service = mcp_service
    
    async def send_daily_analysis(self, user_id: int) -> None:
        """
        Отправляет ежедневный анализ задач пользователю.
        Использует MCP Tools для получения задач из стороннего сервиса.
        
        Args:
            user_id: ID пользователя
        """
        try:
            # Проверяем доступность MCP сервиса
            if not self.mcp_service or not self.mcp_service.is_connected():
                logger.warning(f"MCP сервис недоступен для пользователя {user_id}, пропускаем анализ")
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text="⚠️ MCP сервис недоступен. Ежедневный анализ задач не может быть выполнен."
                    )
                except Exception:
                    pass
                return
            
            # Формируем промпт для анализа задач через MCP Tools
            analysis_messages = [
                {
                    "role": "user",
                    "text": self.DAILY_ANALYSIS_PROMPT
                }
            ]
            
            # Получаем системный промпт пользователя, если есть
            system_prompt = await self.user_repository.get_system_prompt(user_id)
            
            # Отправляем запрос в LLM с включенными MCP Tools
            # LLM сам вызовет нужные инструменты для получения задач
            response, _ = await self.yandex_gpt_service.send_message(
                messages_history=analysis_messages,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2000,
                use_mcp_tools=True  # Включаем использование MCP Tools
            )
            
            # Отправляем результат пользователю
            await self.bot.send_message(
                chat_id=user_id,
                text=f"📊 Ежедневный анализ задач:\n\n{response}"
            )
            
            logger.info(f"Ежедневный анализ отправлен пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке ежедневного анализа пользователю {user_id}: {e}", exc_info=True)
            # Пытаемся отправить сообщение об ошибке пользователю
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text="❌ Произошла ошибка при формировании ежедневного анализа задач. Попробуйте позже."
                )
            except Exception as send_error:
                logger.error(f"Не удалось отправить сообщение об ошибке пользователю {user_id}: {send_error}")
    
    async def send_daily_analysis_to_all_users(self) -> None:
        """
        Отправляет ежедневный анализ всем пользователям.
        """
        logger.info("=" * 50)
        logger.info("НАЧАЛО ВЫПОЛНЕНИЯ ЕЖЕДНЕВНОГО АНАЛИЗА ЗАДАЧ")
        logger.info(f"Время запуска: {datetime.now()}")
        logger.info("=" * 50)
        
        try:
            # Получаем список всех пользователей
            user_ids = await self.user_repository.get_all_users()
            
            if not user_ids:
                logger.warning("Нет пользователей в базе данных. Анализ не будет выполнен.")
                return
            
            logger.info(f"Найдено пользователей: {len(user_ids)}")
            logger.info(f"Начинаем отправку ежедневного анализа для {len(user_ids)} пользователей")
            
            # Отправляем анализ каждому пользователю
            success_count = 0
            error_count = 0
            
            for user_id in user_ids:
                try:
                    logger.info(f"Обработка пользователя {user_id}...")
                    await self.send_daily_analysis(user_id)
                    success_count += 1
                    logger.info(f"✓ Анализ успешно отправлен пользователю {user_id}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"✗ Ошибка при отправке анализа пользователю {user_id}: {e}", exc_info=True)
            
            logger.info("=" * 50)
            logger.info(f"ЗАВЕРШЕНИЕ ЕЖЕДНЕВНОГО АНАЛИЗА ЗАДАЧ")
            logger.info(f"Успешно: {success_count}, Ошибок: {error_count}")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error("=" * 50)
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при отправке ежедневного анализа всем пользователям: {e}", exc_info=True)
            logger.error("=" * 50)

