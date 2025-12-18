"""Репозиторий для работы с историей сообщений."""

from typing import Optional, List, Dict
from repositories.database import Database


class MessageRepository:
    """Репозиторий для работы с историей сообщений в базе данных."""
    
    def __init__(self, database: Database):
        """
        Инициализация репозитория.
        
        Args:
            database: Экземпляр Database для работы с БД
        """
        self.db = database
    
    async def get_history(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает историю сообщений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список сообщений в формате [{"role": "user"/"assistant", "text": "...", ...}, ...]
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT role, text, tokens, response_time
                FROM messages
                WHERE user_id = ?
                ORDER BY created_at ASC
            """, (user_id,))
            rows = await cursor.fetchall()
            
            history = []
            for row in rows:
                message = {
                    "role": row["role"],
                    "text": row["text"]
                }
                if row["tokens"] is not None:
                    message["tokens"] = row["tokens"]
                if row["response_time"] is not None:
                    message["response_time"] = row["response_time"]
                history.append(message)
            
            return history
    
    async def add_message(
        self,
        user_id: int,
        role: str,
        text: str,
        tokens: Optional[int] = None,
        response_time: Optional[float] = None
    ) -> None:
        """
        Добавляет сообщение в историю пользователя.
        
        Args:
            user_id: ID пользователя
            role: Роль сообщения ("user" или "assistant")
            text: Текст сообщения
            tokens: Количество токенов в сообщении (опционально)
            response_time: Время ответа LLM в секундах (опционально, только для assistant)
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO messages (user_id, role, text, tokens, response_time)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, role, text, tokens, response_time))
            await self.db.connection.commit()
    
    async def clear_history(self, user_id: int) -> bool:
        """
        Очищает историю сообщений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если история была очищена, False если её не было
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM messages WHERE user_id = ?",
                (user_id,)
            )
            await self.db.connection.commit()
            return cursor.rowcount > 0
    
    async def replace_history(self, user_id: int, new_history: List[Dict[str, str]]) -> None:
        """
        Заменяет историю сообщений пользователя на новую.
        
        Args:
            user_id: ID пользователя
            new_history: Новая история сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
        """
        # Сначала очищаем старую историю
        await self.clear_history(user_id)
        
        # Затем добавляем новую историю
        for message in new_history:
            await self.add_message(
                user_id,
                message["role"],
                message["text"],
                message.get("tokens"),
                message.get("response_time")
            )
    
    async def get_today_messages(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает сообщения пользователя за сегодня.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список сообщений за сегодня в формате [{"role": "user"/"assistant", "text": "...", ...}, ...]
        """
        async with self.db.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT role, text, tokens, response_time
                FROM messages
                WHERE user_id = ? 
                AND DATE(created_at) = DATE('now')
                ORDER BY created_at ASC
            """, (user_id,))
            rows = await cursor.fetchall()
            
            history = []
            for row in rows:
                message = {
                    "role": row["role"],
                    "text": row["text"]
                }
                if row["tokens"] is not None:
                    message["tokens"] = row["tokens"]
                if row["response_time"] is not None:
                    message["response_time"] = row["response_time"]
                history.append(message)
            
            return history

