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
            # Инициализация sqlite-vss расширения
            try:
                await cursor.execute("SELECT load_extension('sqlite_vss')")
            except Exception as e:
                # Если расширение не загружено, пытаемся загрузить через другой способ
                # sqlite-vss может быть встроен в Python пакет
                try:
                    import sqlite_vss
                    sqlite_vss.load(self._connection)
                except ImportError:
                    # Если sqlite-vss не установлен, пропускаем инициализацию
                    # Это позволит приложению работать без RAG функциональности
                    pass
            
            # Таблица для хранения конфигурации пользователей
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    system_prompt TEXT,
                    temperature REAL DEFAULT 0.6,
                    max_tokens INTEGER DEFAULT 2000,
                    wiki_mode INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем колонку wiki_mode, если её нет (для существующих БД)
            try:
                await cursor.execute("ALTER TABLE users ADD COLUMN wiki_mode INTEGER DEFAULT 0")
            except Exception:
                # Колонка уже существует, игнорируем ошибку
                pass
            
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
            
            # Таблица для хранения метаданных документов
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Таблица для хранения чанков документов
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # Индекс для быстрого поиска сообщений по user_id
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id, created_at)
            """)
            
            # Индексы для документов
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id, uploaded_at)
            """)
            
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id, chunk_index)
            """)
            
            # Создание векторной таблицы для embeddings (только если sqlite-vss доступен)
            try:
                # Проверяем, существует ли уже таблица document_vectors
                await cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_vectors'")
                table_exists = await cursor.fetchone()
                
                if not table_exists:
                    # Создаем векторную таблицу для хранения embeddings
                    # Используем размерность 384 (для модели all-MiniLM-L6-v2)
                    # sqlite-vss использует BLOB для хранения векторов
                    await cursor.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS document_vectors USING vss0(
                            vector(384),
                            chunk_id INTEGER
                        )
                    """)
            except Exception:
                # Если sqlite-vss не доступен, создаем обычную таблицу для хранения векторов как BLOB
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_vectors (
                        chunk_id INTEGER PRIMARY KEY,
                        vector BLOB NOT NULL,
                        FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE CASCADE
                    )
                """)
            
            await self._connection.commit()
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """Возвращает текущее подключение к базе данных."""
        if not self._connection:
            raise RuntimeError("База данных не подключена. Вызовите await database.connect()")
        return self._connection

