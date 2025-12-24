"""Модуль для управления конфигурацией приложения."""

import os
import json
from dotenv import load_dotenv
from typing import Optional, List


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
        
        # Поддержка списка MCP серверов
        # Если указан MCP_SERVERS (JSON массив), используем его
        # Иначе, если указан MCP_SERVER_URL, используем его как единственный сервер
        # Иначе используем значение по умолчанию
        mcp_servers_env = os.getenv("MCP_SERVERS")
        mcp_server_url_env = os.getenv("MCP_SERVER_URL")
        
        if mcp_servers_env:
            # Пытаемся распарсить JSON массив
            try:
                self.mcp_server_urls: List[str] = json.loads(mcp_servers_env)
                if not isinstance(self.mcp_server_urls, list):
                    raise ValueError("MCP_SERVERS должен быть JSON массивом")
                if not self.mcp_server_urls:
                    raise ValueError("MCP_SERVERS не может быть пустым массивом")
            except json.JSONDecodeError as e:
                raise ValueError(f"Неверный формат MCP_SERVERS (должен быть JSON массив): {e}")
        elif mcp_server_url_env:
            # Обратная совместимость: один сервер
            self.mcp_server_urls: List[str] = [mcp_server_url_env]
        else:
            # Значение по умолчанию
            self.mcp_server_urls: List[str] = ["http://127.0.0.1:8000/mcp"]
        
        # Для обратной совместимости сохраняем первый URL
        self.mcp_server_url: str = self.mcp_server_urls[0]
        
        # Параметры для RAG реранкинга
        self.rag_retrieve_k: int = int(os.getenv("RAG_RETRIEVE_K", "20"))
        self.rag_rerank_top_k: int = int(os.getenv("RAG_RERANK_TOP_K", "5"))
        self.rag_rerank_model: str = os.getenv("RAG_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    
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

