"""Сервис для управления данными пользователей."""

from typing import Optional
from repositories.user_repository import UserRepository
from repositories.message_repository import MessageRepository


class UserService:
    """Сервис для управления данными пользователей: история, системные промпты, температура."""
    
    DEFAULT_TEMPERATURE = 0.6
    DEFAULT_MAX_TOKENS = 2000
    
    def __init__(self, user_repository: UserRepository, message_repository: MessageRepository):
        """
        Инициализация сервиса.
        
        Args:
            user_repository: Репозиторий для работы с конфигом пользователей
            message_repository: Репозиторий для работы с историей сообщений
        """
        self.user_repo = user_repository
        self.message_repo = message_repository
    
    async def clear_history(self, user_id: int) -> bool:
        """
        Очищает историю сообщений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если история была очищена, False если её не было
        """
        return await self.message_repo.clear_history(user_id)
    
    async def get_history(self, user_id: int) -> list[dict[str, str]]:
        """
        Получает историю сообщений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
        """
        return await self.message_repo.get_history(user_id)
    
    async def add_message(self, user_id: int, role: str, text: str, tokens: Optional[int] = None, response_time: Optional[float] = None) -> None:
        """
        Добавляет сообщение в историю пользователя.
        
        Args:
            user_id: ID пользователя
            role: Роль сообщения ("user" или "assistant")
            text: Текст сообщения
            tokens: Количество токенов в сообщении (опционально)
            response_time: Время ответа LLM в секундах (опционально, только для assistant)
        """
        await self.message_repo.add_message(user_id, role, text, tokens, response_time)
    
    async def set_system_prompt(self, user_id: int, prompt: str) -> None:
        """
        Устанавливает системный промпт для пользователя.
        
        Args:
            user_id: ID пользователя
            prompt: Системный промпт
        """
        await self.user_repo.set_system_prompt(user_id, prompt)
    
    async def get_system_prompt(self, user_id: int) -> Optional[str]:
        """
        Получает системный промпт пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Системный промпт или None, если не установлен
        """
        return await self.user_repo.get_system_prompt(user_id)
    
    async def has_system_prompt(self, user_id: int) -> bool:
        """
        Проверяет, установлен ли системный промпт для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если промпт установлен, False иначе
        """
        return await self.user_repo.has_system_prompt(user_id)
    
    async def set_temperature(self, user_id: int, temperature: float) -> None:
        """
        Устанавливает температуру для пользователя.
        
        Args:
            user_id: ID пользователя
            temperature: Значение температуры
        """
        await self.user_repo.set_temperature(user_id, temperature)
    
    async def get_temperature(self, user_id: int) -> float:
        """
        Получает температуру пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Температура (по умолчанию DEFAULT_TEMPERATURE)
        """
        return await self.user_repo.get_temperature(user_id)
    
    def validate_temperature(self, temperature: float) -> tuple[bool, Optional[str]]:
        """
        Валидирует значение температуры.
        
        Args:
            temperature: Значение температуры для проверки
            
        Returns:
            Кортеж (is_valid, error_message), где error_message = None если валидно
        """
        if temperature < 0.0 or temperature > 2.0:
            return False, "Температура должна быть в диапазоне от 0.0 до 2.0."
        return True, None
    
    async def set_max_tokens(self, user_id: int, max_tokens: int) -> None:
        """
        Устанавливает максимальное количество токенов для пользователя.
        
        Args:
            user_id: ID пользователя
            max_tokens: Максимальное количество токенов
        """
        await self.user_repo.set_max_tokens(user_id, max_tokens)
    
    async def get_max_tokens(self, user_id: int) -> int:
        """
        Получает максимальное количество токенов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Максимальное количество токенов (по умолчанию DEFAULT_MAX_TOKENS)
        """
        return await self.user_repo.get_max_tokens(user_id)
    
    def validate_max_tokens(self, max_tokens: int) -> tuple[bool, Optional[str]]:
        """
        Валидирует значение максимального количества токенов.
        
        Args:
            max_tokens: Значение максимального количества токенов для проверки
            
        Returns:
            Кортеж (is_valid, error_message), где error_message = None если валидно
        """
        if max_tokens < 1:
            return False, "Максимальное количество токенов должно быть положительным числом (минимум 1)."
        if max_tokens > 8000:
            return False, "Максимальное количество токенов не должно превышать 8000."
        return True, None
    
    async def replace_history(self, user_id: int, new_history: list[dict[str, str]]) -> None:
        """
        Заменяет историю сообщений пользователя на новую.
        
        Args:
            user_id: ID пользователя
            new_history: Новая история сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
        """
        await self.message_repo.replace_history(user_id, new_history)
    
    async def get_wiki_mode(self, user_id: int) -> bool:
        """
        Получает режим WIKI пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если режим WIKI включен, False иначе
        """
        return await self.user_repo.get_wiki_mode(user_id)
    
    async def set_wiki_mode(self, user_id: int, wiki_mode: bool) -> None:
        """
        Устанавливает режим WIKI для пользователя.
        
        Args:
            user_id: ID пользователя
            wiki_mode: True для включения режима WIKI, False для выключения
        """
        await self.user_repo.set_wiki_mode(user_id, wiki_mode)