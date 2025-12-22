"""Сервис для обработки файлов: разбивка на чанки и векторизация."""

import logging
import os
from typing import List
from repositories.document_repository import DocumentRepository
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Размер чанка по умолчанию (256 символов)
CHUNK_SIZE = 256


class DocumentService:
    """Сервис для обработки документов."""
    
    def __init__(
        self, 
        document_repository: DocumentRepository,
        embedding_service: EmbeddingService,
        chunk_size: int = CHUNK_SIZE
    ):
        """
        Инициализация сервиса.
        
        Args:
            document_repository: Репозиторий для работы с документами
            embedding_service: Сервис для векторизации текста
            chunk_size: Размер чанка в символах
        """
        self.document_repository = document_repository
        self.embedding_service = embedding_service
        self.chunk_size = chunk_size
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """
        Разбивает текст на чанки заданного размера.
        Старается разбивать по границам предложений для лучшего контекста.
        
        Args:
            text: Текст для разбивки
            
        Returns:
            Список чанков
        """
        chunks = []
        text_length = len(text)
        
        # Если текст короче размера чанка, возвращаем его целиком
        if text_length <= self.chunk_size:
            return [text] if text.strip() else []
        
        i = 0
        while i < text_length:
            # Определяем конец текущего чанка
            end = min(i + self.chunk_size, text_length)
            
            # Если это не последний чанк, пытаемся найти границу предложения
            if end < text_length:
                # Ищем точку, восклицательный или вопросительный знак в последних 50 символах
                search_start = max(i, end - 50)
                last_sentence_end = -1
                
                for j in range(end - 1, search_start - 1, -1):
                    if text[j] in '.!?\n':
                        # Проверяем, что после знака препинания идет пробел или конец строки
                        if j + 1 >= text_length or text[j + 1] in ' \n\t':
                            last_sentence_end = j + 1
                            break
                
                # Если нашли границу предложения, используем её
                if last_sentence_end > i:
                    end = last_sentence_end
            
            chunk = text[i:end].strip()
            if chunk:  # Добавляем только непустые чанки
                chunks.append(chunk)
            
            i = end
        
        return chunks
    
    async def process_file(
        self, 
        file_content: bytes, 
        filename: str, 
        user_id: int,
        file_path: str | None = None
    ) -> int:
        """
        Обрабатывает загруженный файл: читает содержимое, разбивает на чанки, векторизует и сохраняет.
        
        Args:
            file_content: Содержимое файла в байтах
            filename: Имя файла
            user_id: ID пользователя
            file_path: Путь к сохраненному файлу (опционально)
            
        Returns:
            ID сохраненного документа
            
        Raises:
            ValueError: Если файл не является текстовым или не может быть прочитан
        """
        # Определяем, является ли файл текстовым по расширению
        text_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv', '.log'}
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in text_extensions and file_ext:
            # Пытаемся декодировать как текст в любом случае
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError(f"Файл {filename} не является текстовым файлом. Поддерживаются только текстовые файлы.")
        else:
            # Пытаемся декодировать как UTF-8
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # Пытаемся другие кодировки
                try:
                    text = file_content.decode('latin-1')
                except UnicodeDecodeError:
                    raise ValueError(f"Не удалось декодировать файл {filename}. Убедитесь, что файл в текстовом формате.")
        
        if not text.strip():
            raise ValueError(f"Файл {filename} пуст или содержит только пробелы.")
        
        # Логируем информацию о прочитанном файле
        text_length = len(text)
        logger.info(f"Файл {filename} декодирован: {text_length} символов, {len(file_content)} байт исходных данных")
        
        # Сохраняем метаданные документа
        document_id = await self.document_repository.save_document(user_id, filename, file_path)
        logger.info(f"Документ {filename} сохранен с ID {document_id} для пользователя {user_id}")
        
        # Разбиваем текст на чанки
        chunks = self._split_text_into_chunks(text)
        total_chunks_length = sum(len(chunk) for chunk in chunks)
        logger.info(f"Текст разбит на {len(chunks)} чанков, общая длина чанков: {total_chunks_length} символов (исходный текст: {text_length} символов)")
        
        # Проверяем, что весь текст попал в чанки
        if total_chunks_length < text_length * 0.95:  # Допускаем небольшую потерю из-за strip()
            logger.warning(f"Возможна потеря данных: {text_length - total_chunks_length} символов не попали в чанки")
        
        # Векторизуем и сохраняем каждый чанк
        # Используем batch векторизацию для эффективности
        chunk_vectors = self.embedding_service.embed_texts(chunks)
        
        for chunk_index, (chunk_text, chunk_vector) in enumerate(zip(chunks, chunk_vectors)):
            await self.document_repository.save_chunk(document_id, chunk_index, chunk_text, chunk_vector)
        
        logger.info(f"Обработка документа {filename} завершена: {len(chunks)} чанков сохранено")
        return document_id

