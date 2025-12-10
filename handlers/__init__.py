from handlers.states import SystemPromptStates
from handlers.commands import register_command_handlers
from handlers.messages import register_message_handlers


def setup_handlers(dp, user_service, message_service, yandex_gpt_service, history_formatter, bot):
    """
    Регистрирует все хендлеры в диспетчере.
    
    Args:
        dp: Экземпляр Dispatcher
        user_service: Экземпляр UserService
        message_service: Экземпляр MessageService
        yandex_gpt_service: Экземпляр YandexGPTService
        history_formatter: Экземпляр HistoryFormatterService
        bot: Экземпляр Bot
    """
    register_command_handlers(dp, user_service, history_formatter)
    register_message_handlers(dp, user_service, message_service, yandex_gpt_service, bot)


__all__ = ['setup_handlers', 'SystemPromptStates']

