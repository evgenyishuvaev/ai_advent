"""Сервис для поиска релевантных документов по запросу пользователя (RAG)."""

import logging
from typing import List, Dict, Optional
from repositories.document_repository import DocumentRepository
from services.embedding_service import EmbeddingService
from services.reranking_service import RerankingService

logger = logging.getLogger(__name__)

# Количество релевантных чанков по умолчанию
DEFAULT_TOP_K = 10


class RAGService:
    """Сервис для поиска релевантных документов."""
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_service: EmbeddingService,
        top_k: int = DEFAULT_TOP_K,
        reranking_service: Optional[RerankingService] = None,
        retrieve_k: int = 20,
        rerank_top_k: int = 10
    ):
        """
        Инициализация сервиса.
        
        Args:
            document_repository: Репозиторий для работы с документами
            embedding_service: Сервис для векторизации текста
            top_k: Количество наиболее релевантных чанков для возврата (используется если не указан rerank_top_k)
            reranking_service: Опциональный сервис для реранкинга чанков
            retrieve_k: Количество чанков для извлечения перед реранкингом
            rerank_top_k: Количество чанков для возврата после реранкинга
        """
        self.document_repository = document_repository
        self.embedding_service = embedding_service
        self.reranking_service = reranking_service
        self.top_k = top_k
        self.retrieve_k = retrieve_k
        self.rerank_top_k = rerank_top_k
    
    async def search_relevant_chunks(
        self, 
        user_id: int, 
        query: str, 
        top_k: int | None = None
    ) -> List[Dict]:
        """
        Ищет релевантные чанки документов по запросу пользователя.
        
        Args:
            user_id: ID пользователя
            query: Текст запроса пользователя
            top_k: Количество наиболее релевантных чанков (если None, используется значение по умолчанию)
            
        Returns:
            Список словарей с информацией о найденных чанках:
            - id: ID чанка
            - document_id: ID документа
            - chunk_index: Индекс чанка в документе
            - text: Текст чанка
            - filename: Имя файла документа
        """
        # Определяем количество чанков для извлечения
        retrieve_k = self.retrieve_k if self.reranking_service else (top_k or self.top_k)
        
        # Векторизуем запрос пользователя
        query_vector = self.embedding_service.embed_text(query)
        
        # Ищем релевантные чанки (извлекаем больше, если используется реранкинг)
        relevant_chunks = await self.document_repository.search_relevant_chunks(
            user_id=user_id,
            query_vector=query_vector,
            top_k=retrieve_k
        )
        
        # Если есть reranking_service, применяем реранкинг
        if self.reranking_service:
            relevant_chunks = self.reranking_service.rerank_chunks(query, relevant_chunks)
            # Оставляем только rerank_top_k лучших
            relevant_chunks = relevant_chunks[:self.rerank_top_k]
            logger.info(f"После реранкинга оставлено {len(relevant_chunks)} чанков из {retrieve_k} для запроса пользователя {user_id}")
        else:
            # Если реранкинг не используется, ограничиваем top_k
            if top_k is not None:
                relevant_chunks = relevant_chunks[:top_k]
            else:
                relevant_chunks = relevant_chunks[:self.top_k]
        
        logger.info(f"Найдено {len(relevant_chunks)} релевантных чанков для запроса пользователя {user_id}")
        return relevant_chunks
    
    def format_chunks_as_context(self, chunks: List[Dict]) -> str:
        """
        Форматирует найденные чанки как контекст для LLM.
        
        Args:
            chunks: Список словарей с информацией о чанках
            
        Returns:
            Отформатированная строка с контекстом
        """
        if not chunks:
            return ""
        
        context_parts = ["Релевантные фрагменты из загруженных документов:"]
        for i, chunk in enumerate(chunks, 1):
            filename = chunk.get("filename", "Неизвестный файл")
            text = chunk.get("text", "")
            context_parts.append(f"\n[{i}] Из документа '{filename}':\n{text}")
        
        return "\n".join(context_parts)

