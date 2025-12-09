"""Сервис для обработки сообщений пользователей."""

from typing import Optional
from services.user_service import UserService
from services.yandex_gpt_service import YandexGPTService
from services.token_service import TokenService
from utils import escape_markdown


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
    
    def prepare_user_message(self, user_id: int, text: str) -> tuple[bool, int, Optional[str]]:
        """
        Подготавливает сообщение пользователя: проверяет системный промпт, подсчитывает токены,
        добавляет в историю. Вызывается ПЕРЕД отправкой запроса в LLM.
        
        Args:
            user_id: ID пользователя
            text: Текст сообщения пользователя
            
        Returns:
            Кортеж (success, prompt_tokens, error_message), где:
            - success = True если подготовка успешна
            - prompt_tokens - количество токенов в промпте пользователя
            - error_message - сообщение об ошибке (None если успешно)
        """
        # Проверяем наличие системного промпта
        if not self.user_service.has_system_prompt(user_id):
            return False, 0, "Системный промпт не установлен. Пожалуйста, используй команду /system для его установки."
        
        # Подсчитываем токены для промпта пользователя
        prompt_tokens = self.token_service.count_tokens(text)
        
        # Добавляем сообщение пользователя в историю с количеством токенов
        self.user_service.add_message(user_id, "user", text, tokens=prompt_tokens)
        
        return True, prompt_tokens, None
    
    def get_llm_request_data(self, user_id: int) -> tuple[list[dict[str, str]], Optional[str], float]:
        """
        Получает данные для запроса к LLM: историю, системный промпт и температуру.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Кортеж (history, system_prompt, temperature)
        """
        history = self.user_service.get_history(user_id)
        system_prompt = self.user_service.get_system_prompt(user_id)
        temperature = self.user_service.get_temperature(user_id)
        return history, system_prompt, temperature
    
    async def process_llm_response(self, user_id: int, response: str) -> tuple[bool, str, int]:
        """
        Обрабатывает ответ от LLM: подсчитывает токены, добавляет в историю.
        
        Args:
            user_id: ID пользователя
            response: Ответ от LLM
            
        Returns:
            Кортеж (success, response_with_tokens, response_tokens), где:
            - success = True если обработка успешна
            - response_with_tokens - ответ с информацией о токенах в конце
            - response_tokens - количество токенов в ответе
        """
        # Подсчитываем токены для ответа LLM
        response_tokens = self.token_service.count_tokens(response)
        
        # Добавляем ответ ассистента в историю с количеством токенов
        self.user_service.add_message(user_id, "assistant", response, tokens=response_tokens)
        
        # Экранируем специальные символы Markdown в ответе перед добавлением разметки
        response_escaped = escape_markdown(response)
        
        # Формируем ответ с информацией о токенах
        response_with_tokens = f"{response_escaped}\n\n_Ответ состоит из: {response_tokens} токенов_"
        
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
        
        # Подсчитываем токены для промпта пользователя
        prompt_tokens = self.token_service.count_tokens(text)
        
        # Добавляем сообщение пользователя в историю с количеством токенов
        self.user_service.add_message(user_id, "user", text, tokens=prompt_tokens)
        
        # Получаем системный промпт и температуру
        system_prompt = self.user_service.get_system_prompt(user_id)
        temperature = self.user_service.get_temperature(user_id)
        
        # Получаем историю сообщений
        history = self.user_service.get_history(user_id)
        
        # Отправляем в YandexGPT (история уже содержит новое сообщение пользователя)
        response = await self.yandex_gpt_service.send_message(history, system_prompt, temperature)
        
        # Подсчитываем токены для ответа LLM
        response_tokens = self.token_service.count_tokens(response)
        
        # Добавляем ответ ассистента в историю с количеством токенов
        self.user_service.add_message(user_id, "assistant", response, tokens=response_tokens)
        
        return True, response, prompt_tokens, response_tokens

