"""Репозиторий для работы с конфигурацией пользователей."""

from typing import Optional, List
from repositories.database import Database


class UserRepository:
    """Репозиторий для работы с данными пользователей в базе данных."""
    
    DEFAULT_TEMPERATURE = 0.6
    DEFAULT_MAX_TOKENS = 2000
    
    def __init__(self, database: Database):
        """
        Инициализация репозитория.
        
        Args:
            database: Экземпляр Database для работы с БД
        """
        self.db = database
    
    async def get_system_prompt(self, user_id: int) -> Optional[str]:
        """
        Получает системный промпт пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Системный промпт или None, если не установлен
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute(
                "SELECT system_prompt FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row["system_prompt"] if row and row["system_prompt"] else None
    
    async def set_system_prompt(self, user_id: int, prompt: str) -> None:
        """
        Устанавливает системный промпт для пользователя.
        
        Args:
            user_id: ID пользователя
            prompt: Системный промпт
        """
        async with self.db.connection.cursor() as cursor:
            # Проверяем, существует ли пользователь
            await cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = await cursor.fetchone()
            
            if exists:
                # Обновляем только system_prompt
                await cursor.execute("""
                    UPDATE users 
                    SET system_prompt = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (prompt, user_id))
            else:
                # Создаем нового пользователя с дефолтными значениями
                await cursor.execute("""
                    INSERT INTO users (user_id, system_prompt, temperature, max_tokens, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, prompt, self.DEFAULT_TEMPERATURE, self.DEFAULT_MAX_TOKENS))
            await self.db.connection.commit()
    
    async def get_temperature(self, user_id: int) -> float:
        """
        Получает температуру пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Температура (по умолчанию DEFAULT_TEMPERATURE)
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute(
                "SELECT temperature FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if row and row["temperature"] is not None:
                return float(row["temperature"])
            return self.DEFAULT_TEMPERATURE
    
    async def set_temperature(self, user_id: int, temperature: float) -> None:
        """
        Устанавливает температуру для пользователя.
        
        Args:
            user_id: ID пользователя
            temperature: Значение температуры
        """
        async with self.db.connection.cursor() as cursor:
            # Проверяем, существует ли пользователь
            await cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = await cursor.fetchone()
            
            if exists:
                # Обновляем только temperature
                await cursor.execute("""
                    UPDATE users 
                    SET temperature = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (temperature, user_id))
            else:
                # Создаем нового пользователя с дефолтными значениями
                await cursor.execute("""
                    INSERT INTO users (user_id, temperature, max_tokens, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, temperature, self.DEFAULT_MAX_TOKENS))
            await self.db.connection.commit()
    
    async def get_max_tokens(self, user_id: int) -> int:
        """
        Получает максимальное количество токенов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Максимальное количество токенов (по умолчанию DEFAULT_MAX_TOKENS)
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute(
                "SELECT max_tokens FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if row and row["max_tokens"] is not None:
                return int(row["max_tokens"])
            return self.DEFAULT_MAX_TOKENS
    
    async def set_max_tokens(self, user_id: int, max_tokens: int) -> None:
        """
        Устанавливает максимальное количество токенов для пользователя.
        
        Args:
            user_id: ID пользователя
            max_tokens: Максимальное количество токенов
        """
        async with self.db.connection.cursor() as cursor:
            # Проверяем, существует ли пользователь
            await cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = await cursor.fetchone()
            
            if exists:
                # Обновляем только max_tokens
                await cursor.execute("""
                    UPDATE users 
                    SET max_tokens = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (max_tokens, user_id))
            else:
                # Создаем нового пользователя с дефолтными значениями
                await cursor.execute("""
                    INSERT INTO users (user_id, max_tokens, temperature, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, max_tokens, self.DEFAULT_TEMPERATURE))
            await self.db.connection.commit()
    
    async def has_system_prompt(self, user_id: int) -> bool:
        """
        Проверяет, установлен ли системный промпт для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если промпт установлен, False иначе
        """
        prompt = await self.get_system_prompt(user_id)
        return prompt is not None and bool(prompt.strip())
    
    async def get_all_users(self) -> List[int]:
        """
        Получает список всех пользователей из базы данных.
        
        Returns:
            Список user_id всех пользователей
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
            return [row["user_id"] for row in rows]
    
    async def get_wiki_mode(self, user_id: int) -> bool:
        """
        Получает режим WIKI пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если режим WIKI включен, False иначе
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute(
                "SELECT wiki_mode FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if row and row["wiki_mode"] is not None:
                return bool(row["wiki_mode"])
            return False
    
    async def set_wiki_mode(self, user_id: int, wiki_mode: bool) -> None:
        """
        Устанавливает режим WIKI для пользователя.
        
        Args:
            user_id: ID пользователя
            wiki_mode: True для включения режима WIKI, False для выключения
        """
        async with self.db.connection.cursor() as cursor:
            # Проверяем, существует ли пользователь
            await cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = await cursor.fetchone()
            
            wiki_mode_int = 1 if wiki_mode else 0
            
            if exists:
                # Обновляем только wiki_mode
                await cursor.execute("""
                    UPDATE users 
                    SET wiki_mode = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (wiki_mode_int, user_id))
            else:
                # Создаем нового пользователя с дефолтными значениями
                await cursor.execute("""
                    INSERT INTO users (user_id, wiki_mode, temperature, max_tokens, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, wiki_mode_int, self.DEFAULT_TEMPERATURE, self.DEFAULT_MAX_TOKENS))
            await self.db.connection.commit()

