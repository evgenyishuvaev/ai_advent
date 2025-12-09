"""Сервис для работы с YandexGPT API."""

import asyncio
import aiohttp
from typing import Optional


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
        temperature: float = 0.6
    ) -> str:
        """
        Отправляет историю сообщений в Yandex GPT и возвращает ответ модели.
        
        Args:
            messages_history: Список сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
            system_prompt: Системный промпт (опционально)
            temperature: Коэффициент температуры для генерации (по умолчанию 0.6)
            
        Returns:
            Ответ от Yandex GPT
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
                "maxTokens": 2000
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
                        # Извлекаем текст ответа из структуры ответа Yandex GPT
                        if "result" in data and "alternatives" in data["result"]:
                            if len(data["result"]["alternatives"]) > 0:
                                return data["result"]["alternatives"][0]["message"]["text"]
                        return "Не удалось получить ответ от модели."
                    else:
                        error_text = await response.text()
                        return f"Ошибка API Yandex GPT (код {response.status}): {error_text}"
        except asyncio.TimeoutError:
            return "Превышено время ожидания ответа от Yandex GPT. Попробуйте позже."
        except Exception as e:
            return f"Произошла ошибка при обращении к Yandex GPT: {str(e)}"

