"""Сервис для работы с MCP сервером через FastMCP."""

from fastmcp import Client
from typing import Optional, Dict, Any
import contextlib


class MCPService:
    """Сервис для взаимодействия с MCP сервером."""
    
    def __init__(self, mcp_server_url: str = "http://127.0.0.1:8000/mcp"):
        """
        Инициализация MCP сервиса.
        
        Args:
            mcp_server_url: URL MCP сервера (по умолчанию http://127.0.0.1:8000/mcp)
        """
        self.mcp_server_url = mcp_server_url
        self._client: Optional[Client] = None
        self._is_connected = False
    
    @contextlib.asynccontextmanager
    async def _get_client(self):
        """
        Контекстный менеджер для получения клиента.
        Создает новое подключение при каждом использовании.
        """
        async with Client(self.mcp_server_url) as client:
            yield client
    
    async def connect(self) -> None:
        """
        Проверяет доступность MCP сервера.
        Фактическое подключение происходит при каждом вызове через контекстный менеджер.
        
        Raises:
            Exception: Если не удалось подключиться к серверу
        """
        try:
            # Проверяем подключение, получая список инструментов
            async with self._get_client() as client:
                await client.list_tools()
            self._is_connected = True
        except Exception as e:
            self._is_connected = False
            raise e
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Вызывает инструмент на MCP сервере.
        
        Args:
            tool_name: Имя инструмента для вызова
            parameters: Параметры для передачи инструменту
            
        Returns:
            Результат выполнения инструмента
            
        Raises:
            RuntimeError: Если клиент не подключен
        """
        async with self._get_client() as client:
            return await client.call_tool(tool_name, parameters)
    
    async def list_tools(self) -> list:
        """
        Получает список доступных инструментов на MCP сервере.
        
        Returns:
            Список доступных инструментов
            
        Raises:
            RuntimeError: Если клиент не подключен
        """
        async with self._get_client() as client:
            return await client.list_tools()
    
    def is_connected(self) -> bool:
        """
        Проверяет, подключен ли клиент к серверу.
        
        Returns:
            True, если клиент подключен, False в противном случае
        """
        return self._is_connected
    
    async def close(self) -> None:
        """
        Закрывает подключение к MCP серверу.
        В текущей реализации подключения создаются при каждом вызове,
        поэтому этот метод просто сбрасывает флаг подключения.
        """
        self._is_connected = False
        self._client = None

