"""Сервис для обработки сообщений пользователей."""

from typing import Optional
from services.user_service import UserService
from services.yandex_gpt_service import YandexGPTService
from utils import escape_markdown


class MessageService:
    """Сервис для координации обработки сообщений между UserService и YandexGPTService."""
    
    def __init__(self, user_service: UserService, yandex_gpt_service: YandexGPTService):
        """
        Инициализация сервиса.
        
        Args:
            user_service: Сервис для работы с данными пользователей
            yandex_gpt_service: Сервис для работы с YandexGPT API
        """
        self.user_service = user_service
        self.yandex_gpt_service = yandex_gpt_service
    
    def prepare_user_message(self, user_id: int, text: str) -> tuple[bool, Optional[str]]:
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
        # Проверяем наличие системного промпта
        if not self.user_service.has_system_prompt(user_id):
            return False, "Системный промпт не установлен. Пожалуйста, используй команду /system для его установки."
        
        # Добавляем сообщение пользователя в историю (токены будут получены из API ответа)
        self.user_service.add_message(user_id, "user", text)
        
        return True, None
    
    def get_llm_request_data(self, user_id: int) -> tuple[list[dict[str, str]], Optional[str], float, int]:
        """
        Получает данные для запроса к LLM: историю, системный промпт, температуру и максимальное количество токенов.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Кортеж (history, system_prompt, temperature, max_tokens)
        """
        history = self.user_service.get_history(user_id)
        system_prompt = self.user_service.get_system_prompt(user_id)
        temperature = self.user_service.get_temperature(user_id)
        max_tokens = self.user_service.get_max_tokens(user_id)
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
        self.user_service.add_message(user_id, "assistant", response, tokens=response_tokens, response_time=response_time)
        
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
        # Проверяем наличие системного промпта
        if not self.user_service.has_system_prompt(user_id):
            return False, "Системный промпт не установлен. Пожалуйста, используй команду /system для его установки.", 0, 0
        
        # Добавляем сообщение пользователя в историю (токены будут получены из API ответа)
        self.user_service.add_message(user_id, "user", text)
        
        # Получаем информацию о токенах из API (будет использовано inputTextTokens из ответа)
        prompt_tokens = 0  # Будет обновлено после получения ответа от API
        
        # Получаем системный промпт, температуру и максимальное количество токенов
        system_prompt = self.user_service.get_system_prompt(user_id)
        temperature = self.user_service.get_temperature(user_id)
        max_tokens = self.user_service.get_max_tokens(user_id)
        
        # Получаем историю сообщений
        history = self.user_service.get_history(user_id)
        
        # Отправляем в YandexGPT (история уже содержит новое сообщение пользователя)
        response, usage = await self.yandex_gpt_service.send_message(history, system_prompt, temperature, max_tokens)
        
        # Используем информацию о токенах из API ответа
        response_tokens = usage.get("completionTokens", 0)
        # Преобразуем в int на случай, если значение пришло как строка
        response_tokens = int(response_tokens) if response_tokens else 0
        
        # Добавляем ответ ассистента в историю с количеством токенов
        self.user_service.add_message(user_id, "assistant", response, tokens=response_tokens)
        
        return True, response, prompt_tokens, response_tokens

