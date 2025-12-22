"""Репозиторий для работы с документами и векторами в базе данных."""

import aiosqlite
import json
import numpy as np
from typing import List, Dict, Optional
from repositories.database import Database


class DocumentRepository:
    """Класс для работы с документами и их векторами в базе данных."""
    
    def __init__(self, database: Database):
        """
        Инициализация репозитория.
        
        Args:
            database: Экземпляр Database для работы с БД
        """
        self.database = database
    
    async def save_document(self, user_id: int, filename: str, file_path: Optional[str] = None) -> int:
        """
        Сохраняет метаданные документа в БД.
        
        Args:
            user_id: ID пользователя
            filename: Имя файла
            file_path: Путь к файлу (опционально)
            
        Returns:
            ID сохраненного документа
        """
        async with self.database.connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO documents (user_id, filename, file_path)
                VALUES (?, ?, ?)
            """, (user_id, filename, file_path))
            await self.database.connection.commit()
            return cursor.lastrowid
    
    async def save_chunk(self, document_id: int, chunk_index: int, text: str, vector: List[float]) -> int:
        """
        Сохраняет чанк документа с его вектором в БД.
        
        Args:
            document_id: ID документа
            chunk_index: Индекс чанка в документе
            text: Текст чанка
            vector: Векторное представление чанка
            
        Returns:
            ID сохраненного чанка
        """
        async with self.database.connection.cursor() as cursor:
            # Сохраняем чанк в таблицу document_chunks
            await cursor.execute("""
                INSERT INTO document_chunks (document_id, chunk_index, text)
                VALUES (?, ?, ?)
            """, (document_id, chunk_index, text))
            chunk_id = cursor.lastrowid
            
            # Сохраняем вектор в векторную таблицу (если sqlite-vss доступен)
            try:
                # Преобразуем вектор в numpy array и затем в BLOB для sqlite-vss
                vector_array = np.array(vector, dtype=np.float32)
                vector_blob = vector_array.tobytes()
                
                await cursor.execute("""
                    INSERT INTO document_vectors (vector, chunk_id)
                    VALUES (?, ?)
                """, (vector_blob, chunk_id))
            except Exception:
                # Если sqlite-vss не доступен, просто пропускаем сохранение вектора
                pass
            
            await self.database.connection.commit()
            return chunk_id
    
    async def get_user_documents(self, user_id: int) -> List[Dict]:
        """
        Получает список всех документов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список словарей с информацией о документах
        """
        async with self.database.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT id, filename, file_path, uploaded_at
                FROM documents
                WHERE user_id = ?
                ORDER BY uploaded_at DESC
            """, (user_id,))
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "uploaded_at": row["uploaded_at"]
                }
                for row in rows
            ]
    
    async def delete_document(self, document_id: int) -> bool:
        """
        Удаляет документ и все его чанки из БД.
        
        Args:
            document_id: ID документа
            
        Returns:
            True если документ был удален, False если не найден
        """
        async with self.database.connection.cursor() as cursor:
            # Получаем ID всех чанков документа перед удалением
            await cursor.execute("""
                SELECT id FROM document_chunks WHERE document_id = ?
            """, (document_id,))
            chunk_rows = await cursor.fetchall()
            chunk_ids = [row["id"] for row in chunk_rows]
            
            # Удаляем векторы чанков (если sqlite-vss доступен)
            if chunk_ids:
                try:
                    placeholders = ','.join('?' * len(chunk_ids))
                    await cursor.execute(f"""
                        DELETE FROM document_vectors WHERE chunk_id IN ({placeholders})
                    """, chunk_ids)
                except Exception:
                    # Если sqlite-vss не доступен, пропускаем удаление векторов
                    pass
            
            # Удаляем чанки (каскадное удаление должно удалить их автоматически)
            # Удаляем документ
            await cursor.execute("""
                DELETE FROM documents WHERE id = ?
            """, (document_id,))
            await self.database.connection.commit()
            
            return cursor.rowcount > 0
    
    async def search_relevant_chunks(
        self, 
        user_id: int, 
        query_vector: List[float], 
        top_k: int = 10
    ) -> List[Dict]:
        """
        Ищет релевантные чанки по вектору запроса используя sqlite-vss или Python fallback.
        
        Args:
            user_id: ID пользователя
            query_vector: Векторное представление запроса
            top_k: Количество наиболее релевантных чанков
            
        Returns:
            Список словарей с информацией о найденных чанках
        """
        try:
            async with self.database.connection.cursor() as cursor:
                # Преобразуем вектор запроса в numpy array и затем в BLOB
                query_vector_array = np.array(query_vector, dtype=np.float32)
                query_vector_blob = query_vector_array.tobytes()
                
                # Пытаемся использовать sqlite-vss для поиска
                try:
                    # sqlite-vss может использовать разные функции в зависимости от версии
                    # Пробуем несколько вариантов
                    await cursor.execute("""
                        SELECT 
                            dc.id,
                            dc.document_id,
                            dc.chunk_index,
                            dc.text,
                            d.filename
                        FROM document_vectors dv
                        JOIN document_chunks dc ON dv.chunk_id = dc.id
                        JOIN documents d ON dc.document_id = d.id
                        WHERE d.user_id = ?
                        ORDER BY vss_distance_cosine(dv.vector, ?) ASC
                        LIMIT ?
                    """, (user_id, query_vector_blob, top_k))
                    
                    rows = await cursor.fetchall()
                    return [
                        {
                            "id": row["id"],
                            "document_id": row["document_id"],
                            "chunk_index": row["chunk_index"],
                            "text": row["text"],
                            "filename": row["filename"]
                        }
                        for row in rows
                    ]
                except Exception:
                    # Если sqlite-vss не работает, используем Python fallback
                    # Получаем все чанки пользователя с векторами
                    await cursor.execute("""
                        SELECT 
                            dc.id,
                            dc.document_id,
                            dc.chunk_index,
                            dc.text,
                            d.filename,
                            dv.vector
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        LEFT JOIN document_vectors dv ON dv.chunk_id = dc.id
                        WHERE d.user_id = ?
                    """, (user_id,))
                    
                    rows = await cursor.fetchall()
                    
                    # Вычисляем косинусное сходство для каждого чанка
                    similarities = []
                    query_norm = np.linalg.norm(query_vector_array)
                    
                    for row in rows:
                        vector_blob = row["vector"]
                        if vector_blob:
                            # Преобразуем BLOB обратно в numpy array  
                            chunk_vector = np.frombuffer(vector_blob, dtype=np.float32)
                            
                            # Вычисляем косинусное сходство
                            dot_product = np.dot(query_vector_array, chunk_vector)
                            chunk_norm = np.linalg.norm(chunk_vector)
                            
                            if chunk_norm > 0 and query_norm > 0:
                                similarity = dot_product / (query_norm * chunk_norm)
                                similarities.append((similarity, row))
                    
                    # Сортируем по убыванию сходства и берем top_k
                    similarities.sort(key=lambda x: x[0], reverse=True)
                    
                    return [
                        {
                            "id": row["id"],
                            "document_id": row["document_id"],
                            "chunk_index": row["chunk_index"],
                            "text": row["text"],
                            "filename": row["filename"]
                        }
                        for _, row in similarities[:top_k]
                    ]
        except Exception as e:
            # Если произошла ошибка, возвращаем пустой список
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при поиске релевантных чанков: {e}", exc_info=True)
            return []

