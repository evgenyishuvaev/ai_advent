"""Сервис для работы с YandexGPT API."""

import asyncio
import aiohttp
from typing import Optional, Tuple


class YandexGPTService:
    """Сервис для взаимодействия с YandexGPT API."""
    
    # URL для Yandex GPT API
    DEFAULT_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str = "yandexgpt/latest",
        api_url: Optional[str] = None
    ):
        """
        Инициализация сервиса YandexGPT.
        
        Args:
            api_key: API ключ для Yandex Cloud
            folder_id: ID каталога в Yandex Cloud
            model: Модель для использования (по умолчанию "yandexgpt/latest")
            api_url: URL API (по умолчанию используется стандартный)
        """
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model
        self.api_url = api_url or self.DEFAULT_API_URL
    
    async def send_message(
        self,
        messages_history: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 2000
    ) -> Tuple[str, dict]:
        """
        Отправляет историю сообщений в Yandex GPT и возвращает ответ модели и информацию о токенах.
        
        Args:
            messages_history: Список сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
            system_prompt: Системный промпт (опционально)
            temperature: Коэффициент температуры для генерации (по умолчанию 0.6)
            max_tokens: Максимальное количество токенов в ответе (по умолчанию 2000)
            
        Returns:
            Кортеж (text, usage), где:
            - text: Ответ от Yandex GPT
            - usage: Словарь с информацией о токенах {"inputTextTokens": int, "completionTokens": int, "totalTokens": int}
                    или пустой словарь, если информация недоступна
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
        }
        
        # Формируем список сообщений с системным промптом в начале, если он есть
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "text": system_prompt
            })
        messages.extend(messages_history)
        
        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": max_tokens
            },
            "messages": messages
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(data)
                        # Извлекаем текст ответа из структуры ответа Yandex GPT
                        text = "Не удалось получить ответ от модели."
                        usage = {}
                        
                        if "result" in data:
                            # Извлекаем текст ответа
                            if "alternatives" in data["result"] and len(data["result"]["alternatives"]) > 0:
                                text = data["result"]["alternatives"][0]["message"]["text"]
                            
                            # Извлекаем информацию о токенах
                            if "usage" in data["result"]:
                                usage_data = data["result"]["usage"]
                                # Преобразуем значения в int, так как они могут приходить как строки
                                usage = {
                                    "inputTextTokens": int(usage_data.get("inputTextTokens", 0) or 0),
                                    "completionTokens": int(usage_data.get("completionTokens", 0) or 0),
                                    "totalTokens": int(usage_data.get("totalTokens", 0) or 0)
                                }
                        
                        return text, usage
                    else:
                        error_text = await response.text()
                        return f"Ошибка API Yandex GPT (код {response.status}): {error_text}", {}
        except asyncio.TimeoutError:
            return "Превышено время ожидания ответа от Yandex GPT. Попробуйте позже.", {}
        except Exception as e:
            return f"Произошла ошибка при обращении к Yandex GPT: {str(e)}", {}

