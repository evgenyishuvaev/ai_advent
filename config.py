"""Модуль для управления конфигурацией приложения."""

import os
from dotenv import load_dotenv
from typing import Optional


class Config:
    """Класс для управления конфигурацией приложения из переменных окружения."""
    
    def __init__(self):
        """Инициализация конфигурации - загружает переменные окружения."""
        # Загружаем переменные окружения из .env файла
        load_dotenv()
        
        # Загружаем конфигурацию
        self._load_config()
        
        # Валидируем обязательные переменные
        self._validate_config()
    
    def _load_config(self) -> None:
        """Загружает все переменные окружения."""
        # Обязательные переменные
        self.bot_token: Optional[str] = os.getenv("BOT_TOKEN")
        self.yandex_api_key: Optional[str] = os.getenv("YANDEX_API_KEY")
        self.yandex_folder_id: Optional[str] = os.getenv("YANDEX_FOLDER_ID")
        
        # Опциональные переменные с значениями по умолчанию
        self.yandex_model: str = os.getenv("YANDEX_MODEL", "yandexgpt/latest")
        self.db_path: str = os.getenv("DB_PATH", "bot.db")
        self.mcp_server_url: str = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
    
    def _validate_config(self) -> None:
        """Валидирует обязательные переменные окружения."""
        if not self.bot_token:
            raise ValueError(
                "BOT_TOKEN не найден в переменных окружения. "
                "Создайте файл .env и добавьте BOT_TOKEN=ваш_токен"
            )
        
        if not self.yandex_api_key:
            raise ValueError(
                "YANDEX_API_KEY не найден в переменных окружения. "
                "Добавьте YANDEX_API_KEY=ваш_ключ в .env"
            )
        
        if not self.yandex_folder_id:
            raise ValueError(
                "YANDEX_FOLDER_ID не найден в переменных окружения. "
                "Добавьте YANDEX_FOLDER_ID=ваш_folder_id в .env"
            )


# Создаем глобальный экземпляр конфигурации
config = Config()

