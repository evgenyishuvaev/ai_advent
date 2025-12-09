"""Утилиты для работы с Telegram ботом."""


def escape_markdown(text: str) -> str:
    """
    Экранирует специальные символы Markdown для Telegram (обычный Markdown).
    
    Args:
        text: Текст для экранирования
        
    Returns:
        Экранированный текст
    """
    # Экранируем основные символы, которые могут вызвать проблемы в Markdown
    # Для обычного Markdown нужно экранировать: *, _, [, ], `
    escape_chars = ['*', '_', '[', ']', '`']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

