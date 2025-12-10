"""Сервис для форматирования истории сообщений."""

from utils import escape_markdown


class HistoryFormatterService:
    """Сервис для форматирования истории сообщений для отображения."""
    
    MAX_MESSAGE_LENGTH = 4096  # Ограничение Telegram на длину сообщения
    
    @classmethod
    def format_history(cls, history: list[dict[str, str]]) -> list[str]:
        """
        Форматирует историю сообщений для отображения.
        
        Args:
            history: Список сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
            
        Returns:
            Список отформатированных строк сообщений
        """
        formatted_messages = []
        
        for i, msg in enumerate(history):
            role = msg.get("role", "")
            text = msg.get("text", "")
            tokens = msg.get("tokens")
            response_time = msg.get("response_time")
            
            # Экранируем специальные символы Markdown
            text_escaped = escape_markdown(text)
            
            # Формируем строку с токенами и временем
            if tokens is not None:
                if response_time is not None and role == "assistant":
                    # Для сообщений ассистента показываем токены и время
                    tokens_str = f" _({tokens} токенов, {response_time:.2f}с)_"
                else:
                    # Для пользовательских сообщений только токены
                    tokens_str = f" _({tokens} токенов)_"
            else:
                tokens_str = ""
            
            if i == 0:
                # Первое сообщение выделяем жирным
                if role == "user":
                    formatted_messages.append(f"**👤 {text_escaped}**{tokens_str}")
                elif role == "assistant":
                    formatted_messages.append(f"**🤖 {text_escaped}**{tokens_str}")
                else:
                    formatted_messages.append(f"**{text_escaped}**{tokens_str}")
            else:
                # Остальные сообщения с эмодзи
                if role == "user":
                    formatted_messages.append(f"👤 {text_escaped}{tokens_str}")
                elif role == "assistant":
                    formatted_messages.append(f"🤖 {text_escaped}{tokens_str}")
                else:
                    formatted_messages.append(f"{text_escaped}{tokens_str}")
        
        return formatted_messages
    
    @classmethod
    def format_and_split_history(cls, history: list[dict[str, str]]) -> list[str]:
        """
        Форматирует историю сообщений и разбивает на части, если она слишком длинная.
        
        Args:
            history: Список сообщений в формате [{"role": "user"/"assistant", "text": "..."}, ...]
            
        Returns:
            Список строк для отправки (может быть несколько, если история длинная)
        """
        if not history:
            return []
        
        # Форматируем сообщения
        formatted_messages = cls.format_history(history)
        
        # Формируем заголовок
        header = f"📜 История сообщений ({len(history)} сообщений):\n\n"
        
        # Объединяем все сообщения
        full_history = "\n\n".join(formatted_messages)
        full_text = header + full_history
        
        # Проверяем, помещается ли всё в одно сообщение
        if len(full_text) <= cls.MAX_MESSAGE_LENGTH:
            return [full_text]
        
        # Разбиваем на части
        parts = []
        current_part = []
        is_first_part = True
        
        for msg_text in formatted_messages:
            # Формируем текущую часть для проверки длины
            if is_first_part:
                # Для первой части учитываем заголовок
                test_part = header + "\n\n".join(current_part + [msg_text]) if current_part else header + msg_text
            else:
                # Для остальных частей заголовка нет
                test_part = "\n\n".join(current_part + [msg_text]) if current_part else msg_text
            
            # Проверяем, поместится ли сообщение в текущую часть
            if len(test_part) > cls.MAX_MESSAGE_LENGTH and current_part:
                # Сохраняем текущую часть и начинаем новую
                if is_first_part:
                    # Первая часть с заголовком
                    parts.append(header + "\n\n".join(current_part))
                    is_first_part = False
                else:
                    # Остальные части без заголовка
                    parts.append("\n\n".join(current_part))
                current_part = [msg_text]
            else:
                # Добавляем сообщение в текущую часть
                current_part.append(msg_text)
        
        # Добавляем последнюю часть
        if current_part:
            if is_first_part:
                # Если это единственная часть (не должно случиться, но на всякий случай)
                parts.append(header + "\n\n".join(current_part))
            else:
                # Продолжение истории
                parts.append("\n\n".join(current_part))
        
        return parts

