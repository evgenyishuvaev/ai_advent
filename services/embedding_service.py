"""Сервис для векторизации текста с использованием sentence-transformers."""

import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Сервис для векторизации текста."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Инициализация сервиса.
        
        Args:
            model_name: Название модели sentence-transformers для использования
        """
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        logger.info(f"Инициализация EmbeddingService с моделью: {model_name}")
    
    def _get_model(self) -> SentenceTransformer:
        """
        Получает модель, загружая её при первом обращении (ленивая загрузка).
        
        Returns:
            Экземпляр SentenceTransformer
        """
        if self._model is None:
            logger.info(f"Загрузка модели {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Модель {self.model_name} загружена успешно")
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """
        Векторизует текст.
        
        Args:
            text: Текст для векторизации
            
        Returns:
            Список чисел с float (векторное представление текста)
        """
        model = self._get_model()
        # Получаем embedding как numpy array и преобразуем в список
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Векторизует список текстов (более эффективно, чем вызов embed_text для каждого).
        
        Args:
            texts: Список текстов для векторизации
            
        Returns:
            Список векторов (каждый вектор - список float)
        """
        if not texts:
            return []
        
        model = self._get_model()
        # Получаем embeddings как numpy array и преобразуем в список списков
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

