from aiogram.fsm.state import State, StatesGroup


class SystemPromptStates(StatesGroup):
    """Состояния FSM для запроса системного промпта"""
    waiting_for_prompt = State()

