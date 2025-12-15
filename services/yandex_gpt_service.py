"""Сервис для работы с YandexGPT API."""

import asyncio
import aiohttp
import json
from typing import Optional, Tuple, List, Dict, Any


class YandexGPTService:
    """Сервис для взаимодействия с YandexGPT API."""
    
    # URL для Yandex GPT API
    DEFAULT_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str = "yandexgpt/latest",
        api_url: Optional[str] = None,
        mcp_service: Optional[Any] = None
    ):
        """
        Инициализация сервиса YandexGPT.
        
        Args:
            api_key: API ключ для Yandex Cloud
            folder_id: ID каталога в Yandex Cloud
            model: Модель для использования (по умолчанию "yandexgpt/latest")
            api_url: URL API (по умолчанию используется стандартный)
            mcp_service: Сервис для работы с MCP сервером (опционально)
        """
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model
        self.api_url = api_url or self.DEFAULT_API_URL
        self.mcp_service = mcp_service
    
    def _convert_mcp_tool_to_yandex_format(self, mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Преобразует tool из формата MCP в формат YandexGPT API.
        
        Args:
            mcp_tool: Tool в формате MCP (словарь с полями name, description, inputSchema)
            
        Returns:
            Tool в формате YandexGPT API
        """
        # Извлекаем данные из MCP tool
        tool_name = mcp_tool.get("name", "")
        tool_description = mcp_tool.get("description", "")
        input_schema = mcp_tool.get("inputSchema", {})
        
        # YandexGPT использует формат: { "function": { "name": ..., "description": ..., "parameters": ... } }
        # Без обертки "type": "function"
        yandex_tool = {
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": input_schema if input_schema else {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        return yandex_tool
    
    async def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Получает список tools от MCP сервера и преобразует их в формат YandexGPT.
        
        Returns:
            Список tools в формате YandexGPT API
        """
        if not self.mcp_service:
            return []
        
        try:
            # Получаем список tools от MCP сервера
            mcp_tools = await self.mcp_service.list_tools()
            
            # Преобразуем каждый tool в формат YandexGPT
            yandex_tools = []
            for mcp_tool in mcp_tools:
                # Поддерживаем как словари, так и объекты с атрибутами
                if isinstance(mcp_tool, dict):
                    tool_dict = mcp_tool
                else:
                    # Преобразуем объект в словарь
                    tool_dict = {
                        "name": getattr(mcp_tool, "name", ""),
                        "description": getattr(mcp_tool, "description", ""),
                        "inputSchema": getattr(mcp_tool, "inputSchema", {})
                    }
                
                yandex_tool = self._convert_mcp_tool_to_yandex_format(tool_dict)
                yandex_tools.append(yandex_tool)
            
            return yandex_tools
        except Exception as e:
            # В случае ошибки возвращаем пустой список
            print(f"Ошибка при получении tools от MCP сервера: {e}")
            return []
    
    async def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Выполняет вызов tool через MCP сервис.
        
        Args:
            tool_name: Имя tool для вызова
            arguments: Аргументы для передачи в tool
            
        Returns:
            Результат выполнения tool в виде строки JSON
        """
        if not self.mcp_service:
            return json.dumps({"error": "MCP сервис не доступен"})
        
        try:
            result = await self.mcp_service.call_tool(tool_name, arguments)
            # Преобразуем результат в строку JSON
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"Ошибка при выполнении tool {tool_name}: {str(e)}"})
    
    async def send_message(
        self,
        messages_history: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 2000,
        use_mcp_tools: bool = True,
        max_tool_iterations: int = 5
    ) -> Tuple[str, dict]:
        """
        Отправляет историю сообщений в Yandex GPT и возвращает ответ модели и информацию о токенах.
        Поддерживает автоматическое использование tools от MCP сервера.
        
        Args:
            messages_history: Список сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
            system_prompt: Системный промпт (опционально)
            temperature: Коэффициент температуры для генерации (по умолчанию 0.6)
            max_tokens: Максимальное количество токенов в ответе (по умолчанию 2000)
            use_mcp_tools: Использовать ли tools от MCP сервера (по умолчанию True)
            max_tool_iterations: Максимальное количество итераций вызова tools (по умолчанию 5)
            
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
        
        # Получаем tools от MCP сервера, если нужно
        tools = []
        if use_mcp_tools and self.mcp_service:
            tools = await self._get_mcp_tools()
        
        # Формируем список сообщений с системным промптом в начале, если он есть
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "text": system_prompt
            })
        messages.extend(messages_history)
        
        # Выполняем итерации с обработкой tool calls
        total_usage = {}
        iteration = 0
        
        while iteration < max_tool_iterations:
            payload = {
                "modelUri": f"gpt://{self.folder_id}/{self.model}",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": max_tokens
                },
                "messages": messages
            }
            
            # Добавляем tools в payload, если они есть
            if tools:
                payload["tools"] = tools
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Извлекаем информацию о токенах
                            if "result" in data and "usage" in data["result"]:
                                usage_data = data["result"]["usage"]
                                # Суммируем токены по всем итерациям
                                total_usage = {
                                    "inputTextTokens": total_usage.get("inputTextTokens", 0) + int(usage_data.get("inputTextTokens", 0) or 0),
                                    "completionTokens": total_usage.get("completionTokens", 0) + int(usage_data.get("completionTokens", 0) or 0),
                                    "totalTokens": total_usage.get("totalTokens", 0) + int(usage_data.get("totalTokens", 0) or 0)
                                }
                            
                            if "result" not in data:
                                return "Не удалось получить ответ от модели.", total_usage
                            
                            result = data["result"]
                            
                            # Проверяем наличие tool calls в ответе
                            if "alternatives" in result and len(result["alternatives"]) > 0:
                                alternative = result["alternatives"][0]
                                message = alternative.get("message", {})
                                status = alternative.get("status", "")
                                
                                # Проверяем наличие tool calls в формате YandexGPT API
                                # tool calls находятся в message.toolCallList.toolCalls
                                tool_call_list = message.get("toolCallList", {})
                                tool_calls = tool_call_list.get("toolCalls", [])
                                
                                # Также проверяем статус для определения tool calls
                                has_tool_calls = tool_calls or status == "ALTERNATIVE_STATUS_TOOL_CALLS"
                                
                                if has_tool_calls and tool_calls:
                                    # Выполняем все tool calls
                                    tool_results = []
                                    for tool_call in tool_calls:
                                        # В YandexGPT формат: toolCall.functionCall.name и toolCall.functionCall.arguments
                                        function_call = tool_call.get("functionCall", {})
                                        tool_name = function_call.get("name", "")
                                        tool_args = function_call.get("arguments", {})
                                        
                                        # arguments уже должен быть словарем, но проверяем
                                        if isinstance(tool_args, str):
                                            try:
                                                tool_args = json.loads(tool_args)
                                            except json.JSONDecodeError:
                                                tool_args = {}
                                        
                                        # Выполняем tool call
                                        tool_result = await self._execute_tool_call(tool_name, tool_args)
                                        
                                        # Добавляем результат в список
                                        tool_results.append({
                                            "name": tool_name,
                                            "content": tool_result
                                        })
                                    
                                    # Добавляем сообщение ассистента в историю (если есть текст)
                                    assistant_text = message.get("text", "")
                                    if assistant_text:
                                        messages.append({
                                            "role": "assistant",
                                            "text": assistant_text
                                        })
                                    
                                    # Добавляем результаты tool calls в историю
                                    # YandexGPT не поддерживает роль 'tool', поэтому передаем результаты как сообщение от пользователя
                                    # Формируем текст с результатами всех tool calls
                                    tool_results_text = "Результаты выполнения инструментов:\n\n"
                                    for tool_result in tool_results:
                                        tool_results_text += f"Инструмент '{tool_result['name']}':\n{tool_result['content']}\n\n"
                                    
                                    # Добавляем результаты как сообщение от пользователя
                                    messages.append({
                                        "role": "user",
                                        "text": tool_results_text.strip()
                                    })
                                    
                                    # Продолжаем итерацию для получения финального ответа
                                    iteration += 1
                                    continue
                                else:
                                    # Нет tool calls, возвращаем финальный ответ
                                    text = message.get("text", "Не удалось получить ответ от модели.")
                                    return text, total_usage
                            else:
                                return "Не удалось получить ответ от модели.", total_usage
                        else:
                            error_text = await response.text()
                            return f"Ошибка API Yandex GPT (код {response.status}): {error_text}", total_usage
            except asyncio.TimeoutError:
                return "Превышено время ожидания ответа от Yandex GPT. Попробуйте позже.", total_usage
            except Exception as e:
                return f"Произошла ошибка при обращении к Yandex GPT: {str(e)}", total_usage
            
            iteration += 1
        
        # Если достигли максимального количества итераций, возвращаем последний ответ
        if messages:
            last_message = messages[-1]
            if last_message.get("role") == "assistant":
                return last_message.get("text", "Достигнуто максимальное количество итераций вызова tools."), total_usage
        
        return "Не удалось получить ответ от модели.", total_usage

