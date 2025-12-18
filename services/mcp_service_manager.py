"""Менеджер для работы с несколькими MCP серверами."""

import logging
from typing import Optional, Dict, Any, List
from services.mcp_service import MCPService

logger = logging.getLogger(__name__)


class MCPServiceManager:
    """Менеджер для управления несколькими MCP серверами."""
    
    def __init__(self, mcp_server_urls: List[str]):
        """
        Инициализация менеджера MCP серверов.
        
        Args:
            mcp_server_urls: Список URL MCP серверов
        """
        self.mcp_server_urls = mcp_server_urls
        self.services: List[MCPService] = []
        
        # Создаем сервис для каждого URL
        for url in mcp_server_urls:
            service = MCPService(mcp_server_url=url)
            self.services.append(service)
    
    async def connect(self) -> None:
        """
        Подключается ко всем MCP серверам.
        Продолжает подключение к остальным серверам даже если некоторые не доступны.
        
        Raises:
            Exception: Если не удалось подключиться ни к одному серверу
        """
        connected_count = 0
        errors = []
        
        for i, service in enumerate(self.services):
            try:
                await service.connect()
                connected_count += 1
                logger.info(f"MCP сервис {i+1}/{len(self.services)} подключен к {service.mcp_server_url}")
            except Exception as e:
                error_msg = f"Не удалось подключиться к {service.mcp_server_url}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        if connected_count == 0:
            error_message = "Не удалось подключиться ни к одному MCP серверу:\n" + "\n".join(errors)
            raise Exception(error_message)
        
        if errors:
            logger.warning(f"Подключено {connected_count}/{len(self.services)} серверов. Ошибки:\n" + "\n".join(errors))
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Вызывает инструмент на первом доступном MCP сервере, который его поддерживает.
        
        Args:
            tool_name: Имя инструмента для вызова
            parameters: Параметры для передачи инструменту
            
        Returns:
            Результат выполнения инструмента
            
        Raises:
            RuntimeError: Если инструмент не найден ни на одном сервере или произошла ошибка при вызове
        """
        last_error = None
        
        # Пробуем найти инструмент на каждом сервере
        for service in self.services:
            if not service.is_connected():
                continue
            
            try:
                # Проверяем, есть ли этот инструмент на сервере
                tools = await service.list_tools()
                tool_names = []
                for tool in tools:
                    if isinstance(tool, dict):
                        tool_names.append(tool.get("name", ""))
                    else:
                        tool_names.append(getattr(tool, "name", ""))
                
                if tool_name in tool_names:
                    # Нашли инструмент, вызываем его
                    try:
                        return await service.call_tool(tool_name, parameters)
                    except Exception as e:
                        # Сохраняем ошибку, но продолжаем искать на других серверах
                        last_error = e
                        logger.warning(f"Ошибка при вызове инструмента {tool_name} на сервере {service.mcp_server_url}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Ошибка при проверке инструмента {tool_name} на сервере {service.mcp_server_url}: {e}")
                continue
        
        # Инструмент не найден ни на одном сервере или все вызовы завершились ошибкой
        if last_error:
            raise RuntimeError(f"Инструмент '{tool_name}' найден, но произошла ошибка при вызове: {last_error}")
        else:
            raise RuntimeError(f"Инструмент '{tool_name}' не найден ни на одном из доступных MCP серверов")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Получает список всех доступных инструментов со всех MCP серверов.
        Удаляет дубликаты по имени инструмента (приоритет у первого найденного).
        
        Returns:
            Список всех доступных инструментов
        """
        all_tools = []
        seen_tool_names = set()
        
        for service in self.services:
            if not service.is_connected():
                continue
            
            try:
                tools = await service.list_tools()
                for tool in tools:
                    # Извлекаем имя инструмента
                    if isinstance(tool, dict):
                        tool_name = tool.get("name", "")
                        tool_dict = tool
                    else:
                        tool_name = getattr(tool, "name", "")
                        tool_dict = {
                            "name": tool_name,
                            "description": getattr(tool, "description", ""),
                            "inputSchema": getattr(tool, "inputSchema", {})
                        }
                    
                    # Добавляем только если еще не видели инструмент с таким именем
                    if tool_name and tool_name not in seen_tool_names:
                        all_tools.append(tool_dict)
                        seen_tool_names.add(tool_name)
            except Exception as e:
                logger.warning(f"Ошибка при получении инструментов с сервера {service.mcp_server_url}: {e}")
                continue
        
        return all_tools
    
    def is_connected(self) -> bool:
        """
        Проверяет, подключен ли хотя бы один клиент к серверу.
        
        Returns:
            True, если хотя бы один клиент подключен, False в противном случае
        """
        return any(service.is_connected() for service in self.services)
    
    def get_connected_servers(self) -> List[str]:
        """
        Возвращает список URL подключенных серверов.
        
        Returns:
            Список URL подключенных серверов
        """
        return [service.mcp_server_url for service in self.services if service.is_connected()]
    
    async def close(self) -> None:
        """
        Закрывает подключения ко всем MCP серверам.
        """
        for service in self.services:
            if service.is_connected():
                await service.close()

