"""Сервис для подсчета токенов в тексте."""

import tiktoken


class TokenService:
    """Сервис для подсчета токенов в тексте с использованием tiktoken."""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Инициализация сервиса подсчета токенов.
        
        Args:
            encoding_name: Название encoding для tiktoken (по умолчанию "cl100k_base" - используется в GPT-3.5/GPT-4)
        """
        self.encoding = tiktoken.get_encoding(encoding_name)
    
    def count_tokens(self, text: str) -> int:
        """
        Подсчитывает количество токенов в тексте.
        
        Args:
            text: Текст для подсчета токенов
            
        Returns:
            Количество токенов в тексте
        """
        if not text:
            return 0
        return len(self.encoding.encode(text))

