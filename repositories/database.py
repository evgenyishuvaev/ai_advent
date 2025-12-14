"""Модуль для работы с базой данных SQLite."""

import aiosqlite
from typing import Optional
import os


class Database:
    """Класс для управления подключением к базе данных и инициализации схемы."""
    
    def __init__(self, db_path: str = "bot.db"):
        """
        Инициализация базы данных.
        
        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Устанавливает подключение к базе данных."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._init_schema()
    
    async def close(self) -> None:
        """Закрывает подключение к базе данных."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def _init_schema(self) -> None:
        """Инициализирует схему базы данных."""
        async with self._connection.cursor() as cursor:
            # Таблица для хранения конфигурации пользователей
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    system_prompt TEXT,
                    temperature REAL DEFAULT 0.6,
                    max_tokens INTEGER DEFAULT 2000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для хранения истории сообщений
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    tokens INTEGER,
                    response_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Индекс для быстрого поиска сообщений по user_id
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id, created_at)
            """)
            
            await self._connection.commit()
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """Возвращает текущее подключение к базе данных."""
        if not self._connection:
            raise RuntimeError("База данных не подключена. Вызовите await database.connect()")
        return self._connection

