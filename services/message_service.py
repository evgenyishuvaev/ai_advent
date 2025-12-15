"""Сервис для обработки сообщений пользователей."""

from typing import Optional
from services.user_service import UserService
from services.yandex_gpt_service import YandexGPTService
from services.token_service import TokenService
from utils import escape_markdown


# Константы для суммаризации контекста
CONTEXT_TOKEN_LIMIT = 1000
KEEP_RECENT_MESSAGES = 2
SUMMARIZATION_PROMPT = "Сделай краткое техническое резюме диалога, сохрани факты, решения, договорённости, предпочтения. Не пересказывай каждую реплику."


class MessageService:
    """Сервис для координации обработки сообщений между UserService и YandexGPTService."""
    
    def __init__(self, user_service: UserService, yandex_gpt_service: YandexGPTService, token_service: TokenService):
        """
        Инициализация сервиса.
        
        Args:
            user_service: Сервис для работы с данными пользователей
            yandex_gpt_service: Сервис для работы с YandexGPT API
            token_service: Сервис для подсчета токенов
        """
        self.user_service = user_service
        self.yandex_gpt_service = yandex_gpt_service
        self.token_service = token_service
    
    async def prepare_user_message(self, user_id: int, text: str) -> tuple[bool, Optional[str]]:
        """
        Подготавливает сообщение пользователя: проверяет системный промпт, добавляет в историю.
        Вызывается ПЕРЕД отправкой запроса в LLM.
        
        Args:
            user_id: ID пользователя
            text: Текст сообщения пользователя
            
        Returns:
            Кортеж (success, error_message), где:
            - success = True если подготовка успешна
            - error_message - сообщение об ошибке (None если успешно)
        """
        # Системный промпт опционален, можно работать без него
        # Добавляем сообщение пользователя в историю (токены будут получены из API ответа)
        await self.user_service.add_message(user_id, "user", text)
        
        return True, None
    
    def _count_context_tokens(self, history: list[dict[str, str]], system_prompt: Optional[str]) -> int:
        """
        Подсчитывает общее количество токенов в контексте (история + системный промпт).
        
        Args:
            history: История сообщений
            system_prompt: Системный промпт (опционально)
            
        Returns:
            Общее количество токенов в контексте
        """
        total_tokens = 0
        
        # Подсчитываем токены в истории
        for message in history:
            text = message.get("text", "")
            if text:
                total_tokens += self.token_service.count_tokens(text)
        
        # Подсчитываем токены в системном промпте
        if system_prompt:
            total_tokens += self.token_service.count_tokens(system_prompt)
        
        return total_tokens
    
    async def _summarize_history(self, history_to_summarize: list[dict[str, str]]) -> str:
        """
        Создает суммаризацию истории через отдельный запрос к LLM.
        
        Args:
            history_to_summarize: История сообщений для суммаризации
            
        Returns:
            Текст суммаризации
        """
        # Формируем историю для суммаризации: добавляем системный промпт с инструкцией
        summarization_history = history_to_summarize.copy()
        
        # Отправляем запрос к LLM для суммаризации
        # Используем стандартную температуру и max_tokens для суммаризации
        summary, _ = await self.yandex_gpt_service.send_message(
            messages_history=summarization_history,
            system_prompt=SUMMARIZATION_PROMPT,
            temperature=0.3,  # Низкая температура для более точной суммаризации
            max_tokens=500  # Ограничиваем длину суммаризации
        )
        
        return summary
    
    async def get_llm_request_data(self, user_id: int) -> tuple[list[dict[str, str]], Optional[str], float, int]:
        """
        Получает данные для запроса к LLM: историю, системный промпт, температуру и максимальное количество токенов.
        Автоматически выполняет суммаризацию при достижении лимита токенов.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Кортеж (history, system_prompt, temperature, max_tokens)
        """
        history = await self.user_service.get_history(user_id)
        system_prompt = await self.user_service.get_system_prompt(user_id)
        temperature = await self.user_service.get_temperature(user_id)
        max_tokens = await self.user_service.get_max_tokens(user_id)
        
        # Проверяем количество токенов в контексте
        context_tokens = self._count_context_tokens(history, system_prompt)
        
        # Если достигли лимита, выполняем суммаризацию
        if context_tokens >= CONTEXT_TOKEN_LIMIT:
            # Сохраняем последние KEEP_RECENT_MESSAGES сообщений
            if len(history) > KEEP_RECENT_MESSAGES:
                recent_messages = history[-KEEP_RECENT_MESSAGES:]
                history_to_summarize = history[:-KEEP_RECENT_MESSAGES]
                
                # Выполняем суммаризацию старой части истории
                try:
                    summary = await self._summarize_history(history_to_summarize)
                    # Проверяем, что суммаризация не является сообщением об ошибке
                    if summary.startswith("Ошибка") or summary.startswith("Превышено"):
                        # Если суммаризация не удалась, оставляем историю неизменной
                        pass
                    else:
                        # Формируем новую историю: суммаризация + последние сообщения
                        new_history = [
                            {
                                "role": "assistant",
                                "text": f"[Резюме предыдущего диалога]: {summary}"
                            }
                        ]
                        new_history.extend(recent_messages)
                        
                        # Заменяем историю в UserService
                        await self.user_service.replace_history(user_id, new_history)
                        
                        # Обновляем history для возврата
                        history = new_history
                except Exception:
                    # В случае ошибки оставляем историю неизменной
                    pass
        
        return history, system_prompt, temperature, max_tokens
    
    async def process_llm_response(
        self, 
        user_id: int, 
        response: str, 
        response_time: float,
        usage: dict
    ) -> tuple[bool, str, int]:
        """
        Обрабатывает ответ от LLM: использует информацию о токенах из API, добавляет в историю.
        
        Args:
            user_id: ID пользователя
            response: Ответ от LLM
            response_time: Время выполнения запроса к LLM в секундах
            usage: Словарь с информацией о токенах из API {"inputTextTokens": int, "completionTokens": int, "totalTokens": int}
            
        Returns:
            Кортеж (success, response_with_tokens, response_tokens), где:
            - success = True если обработка успешна
            - response_with_tokens - ответ с информацией о токенах и времени в конце
            - response_tokens - количество токенов в ответе (completionTokens из API)
        """
        # Используем информацию о токенах из API ответа
        response_tokens = usage.get("completionTokens", 0)
        # Преобразуем в int на случай, если значение пришло как строка
        response_tokens = int(response_tokens) if response_tokens else 0
        
        # Добавляем ответ ассистента в историю с количеством токенов и временем ответа
        await self.user_service.add_message(user_id, "assistant", response, tokens=response_tokens, response_time=response_time)
        
        # Экранируем специальные символы Markdown в ответе перед добавлением разметки
        response_escaped = escape_markdown(response)
        
        # Формируем ответ с информацией о токенах и времени под чертой
        response_with_tokens = f"{response_escaped}\n\n---\nОтвет: {response_tokens} токенов | Время: {response_time:.2f}с"
        
        return True, response_with_tokens, response_tokens
    
    async def process_user_message(self, user_id: int, text: str) -> tuple[bool, str, int, int]:
        """
        Обрабатывает сообщение пользователя: проверяет системный промпт, добавляет в историю,
        вызывает GPT и сохраняет ответ. Устаревший метод, используйте prepare_user_message и process_llm_response.
        
        Args:
            user_id: ID пользователя
            text: Текст сообщения пользователя
            
        Returns:
            Кортеж (success, message, prompt_tokens, response_tokens)
        """
        # Системный промпт опционален, можно работать без него
        
        # Добавляем сообщение пользователя в историю (токены будут получены из API ответа)
        await self.user_service.add_message(user_id, "user", text)
        
        # Получаем информацию о токенах из API (будет использовано inputTextTokens из ответа)
        prompt_tokens = 0  # Будет обновлено после получения ответа от API
        
        # Получаем системный промпт, температуру и максимальное количество токенов
        system_prompt = await self.user_service.get_system_prompt(user_id)
        temperature = await self.user_service.get_temperature(user_id)
        max_tokens = await self.user_service.get_max_tokens(user_id)
        
        # Получаем историю сообщений
        history = await self.user_service.get_history(user_id)
        
        # Отправляем в YandexGPT (история уже содержит новое сообщение пользователя)
        response, usage = await self.yandex_gpt_service.send_message(history, system_prompt, temperature, max_tokens)
        
        # Используем информацию о токенах из API ответа
        response_tokens = usage.get("completionTokens", 0)
        # Преобразуем в int на случай, если значение пришло как строка
        response_tokens = int(response_tokens) if response_tokens else 0
        
        # Добавляем ответ ассистента в историю с количеством токенов
        await self.user_service.add_message(user_id, "assistant", response, tokens=response_tokens)
        
        return True, response, prompt_tokens, response_tokens

