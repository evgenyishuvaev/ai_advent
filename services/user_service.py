"""Сервис для управления данными пользователей."""

from typing import Optional


class UserService:
    """Сервис для управления данными пользователей: история, системные промпты, температура."""
    
    DEFAULT_TEMPERATURE = 0.6
    DEFAULT_MAX_TOKENS = 2000
    
    def __init__(self):
        """Инициализация сервиса."""
        # Приватные словари для хранения данных пользователей
        self._histories: dict[int, list[dict[str, str]]] = {}
        self._system_prompts: dict[int, str] = {}
        self._temperatures: dict[int, float] = {}
        self._max_tokens: dict[int, int] = {}
    
    def clear_history(self, user_id: int) -> bool:
        """
        Очищает историю сообщений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если история была очищена, False если её не было
        """
        if user_id in self._histories:
            self._histories[user_id] = []
            return True
        return False
    
    def get_history(self, user_id: int) -> list[dict[str, str]]:
        """
        Получает историю сообщений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
        """
        if user_id not in self._histories:
            self._histories[user_id] = []
        return self._histories[user_id]
    
    def add_message(self, user_id: int, role: str, text: str, tokens: Optional[int] = None, response_time: Optional[float] = None) -> None:
        """
        Добавляет сообщение в историю пользователя.
        
        Args:
            user_id: ID пользователя
            role: Роль сообщения ("user" или "assistant")
            text: Текст сообщения
            tokens: Количество токенов в сообщении (опционально)
            response_time: Время ответа LLM в секундах (опционально, только для assistant)
        """
        if user_id not in self._histories:
            self._histories[user_id] = []
        message = {
            "role": role,
            "text": text
        }
        if tokens is not None:
            message["tokens"] = tokens
        if response_time is not None:
            message["response_time"] = response_time
        self._histories[user_id].append(message)
    
    def set_system_prompt(self, user_id: int, prompt: str) -> None:
        """
        Устанавливает системный промпт для пользователя.
        
        Args:
            user_id: ID пользователя
            prompt: Системный промпт
        """
        self._system_prompts[user_id] = prompt
    
    def get_system_prompt(self, user_id: int) -> Optional[str]:
        """
        Получает системный промпт пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Системный промпт или None, если не установлен
        """
        return self._system_prompts.get(user_id)
    
    def has_system_prompt(self, user_id: int) -> bool:
        """
        Проверяет, установлен ли системный промпт для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если промпт установлен, False иначе
        """
        return user_id in self._system_prompts and bool(self._system_prompts[user_id])
    
    def set_temperature(self, user_id: int, temperature: float) -> None:
        """
        Устанавливает температуру для пользователя.
        
        Args:
            user_id: ID пользователя
            temperature: Значение температуры
        """
        self._temperatures[user_id] = temperature
    
    def get_temperature(self, user_id: int) -> float:
        """
        Получает температуру пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Температура (по умолчанию DEFAULT_TEMPERATURE)
        """
        return self._temperatures.get(user_id, self.DEFAULT_TEMPERATURE)
    
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
    
    def set_max_tokens(self, user_id: int, max_tokens: int) -> None:
        """
        Устанавливает максимальное количество токенов для пользователя.
        
        Args:
            user_id: ID пользователя
            max_tokens: Максимальное количество токенов
        """
        self._max_tokens[user_id] = max_tokens
    
    def get_max_tokens(self, user_id: int) -> int:
        """
        Получает максимальное количество токенов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Максимальное количество токенов (по умолчанию DEFAULT_MAX_TOKENS)
        """
        return self._max_tokens.get(user_id, self.DEFAULT_MAX_TOKENS)
    
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
    
    def replace_history(self, user_id: int, new_history: list[dict[str, str]]) -> None:
        """
        Заменяет историю сообщений пользователя на новую.
        
        Args:
            user_id: ID пользователя
            new_history: Новая история сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
        """
        self._histories[user_id] = new_history

