"""Сервис для реранкинга найденных чанков с использованием cross-encoder модели."""

import logging
from typing import List, Dict
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class RerankingService:
    """Сервис для реранкинга чанков по релевантности к запросу."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Инициализация сервиса.
        
        Args:
            model_name: Название cross-encoder модели для использования
        """
        self.model_name = model_name
        self._model: CrossEncoder | None = None
        logger.info(f"Инициализация RerankingService с моделью: {model_name}")
    
    def _get_model(self) -> CrossEncoder:
        """
        Получает модель, загружая её при первом обращении (ленивая загрузка).
        
        Returns:
            Экземпляр CrossEncoder
        """
        if self._model is None:
            logger.info(f"Загрузка модели {self.model_name}...")
            self._model = CrossEncoder(self.model_name)
            logger.info(f"Модель {self.model_name} загружена успешно")
        return self._model
    
    def rerank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Реранкит чанки по релевантности к запросу.
        
        Args:
            query: Текст запроса пользователя
            chunks: Список словарей с информацией о чанках (должен содержать ключ 'text')
            
        Returns:
            Отсортированный по убыванию релевантности список чанков
        """
        if not chunks:
            return []
        
        model = self._get_model()
        
        # Формируем пары (query, chunk_text) для оценки
        pairs = [(query, chunk.get("text", "")) for chunk in chunks]
        
        # Вычисляем scores через cross-encoder
        scores = model.predict(pairs)
        
        # Добавляем score к каждому чанку и сортируем по убыванию
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])
        
        # Сортируем по убыванию score
        reranked_chunks = sorted(chunks, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        
        logger.debug(f"Реранкинг выполнен для {len(chunks)} чанков")
        return reranked_chunks

