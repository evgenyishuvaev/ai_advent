from handlers.states import SystemPromptStates
from handlers.commands import register_command_handlers
from handlers.messages import register_message_handlers


def setup_handlers(dp, user_service, message_service, yandex_gpt_service, history_formatter, bot, mcp_service=None, daily_task_service=None, document_service=None):
    """
    Регистрирует все хендлеры в диспетчере.
    
    Args:
        dp: Экземпляр Dispatcher
        user_service: Экземпляр UserService
        message_service: Экземпляр MessageService
        yandex_gpt_service: Экземпляр YandexGPTService
        history_formatter: Экземпляр HistoryFormatterService
        bot: Экземпляр Bot
        mcp_service: Экземпляр MCPService (опционально)
        daily_task_service: Экземпляр DailyTaskService (опционально)
        document_service: Экземпляр DocumentService (опционально)
    """
    register_command_handlers(dp, user_service, history_formatter, mcp_service, daily_task_service, document_service)
    register_message_handlers(dp, user_service, message_service, yandex_gpt_service, bot, document_service)


__all__ = ['setup_handlers', 'SystemPromptStates']

