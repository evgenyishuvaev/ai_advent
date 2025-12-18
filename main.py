import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import config
from services.yandex_gpt_service import YandexGPTService
from services.user_service import UserService
from services.message_service import MessageService
from services.history_formatter_service import HistoryFormatterService
from services.token_service import TokenService
from services.mcp_service import MCPService
from services.mcp_service_manager import MCPServiceManager
from services.daily_task_service import DailyTaskService
from repositories.database import Database
from repositories.user_repository import UserRepository
from repositories.message_repository import MessageRepository
from handlers import setup_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализируем базу данных
database = Database(db_path=config.db_path)

# Инициализируем репозитории
user_repository = UserRepository(database)
message_repository = MessageRepository(database)

# Инициализируем бота и диспетчер
bot = Bot(token=config.bot_token)
dp = Dispatcher()

# Инициализируем MCP сервис (менеджер для работы с несколькими серверами)
if len(config.mcp_server_urls) == 1:
    # Для обратной совместимости: один сервер
    mcp_service = MCPService(mcp_server_url=config.mcp_server_url)
else:
    # Несколько серверов - используем менеджер
    mcp_service = MCPServiceManager(mcp_server_urls=config.mcp_server_urls)

# Инициализируем сервисы
yandex_gpt_service = YandexGPTService(
    api_key=config.yandex_api_key,
    folder_id=config.yandex_folder_id,
    model=config.yandex_model,
    mcp_service=mcp_service
)
user_service = UserService(user_repository, message_repository)
token_service = TokenService()
message_service = MessageService(user_service, yandex_gpt_service, token_service)
history_formatter = HistoryFormatterService()
daily_task_service = DailyTaskService(
    bot=bot,
    user_repository=user_repository,
    message_repository=message_repository,
    yandex_gpt_service=yandex_gpt_service,
    mcp_service=mcp_service
)

# Регистрируем все хендлеры
setup_handlers(dp, user_service, message_service, yandex_gpt_service, history_formatter, bot, mcp_service, daily_task_service)

# Инициализируем scheduler для ежедневных задач
# Используем локальный timezone системы
try:
    # Пытаемся использовать локальный timezone системы
    local_tz = datetime.now().astimezone().tzinfo
    logger.info(f"Используется локальный timezone: {local_tz}")
except Exception as e:
    logger.warning(f"Не удалось определить локальный timezone: {e}, используем UTC")
    local_tz = ZoneInfo('UTC')

scheduler = AsyncIOScheduler(timezone=local_tz)


async def main():
    """Главная функция для запуска бота"""
    # Подключаемся к базе данных
    await database.connect()
    
    # Подключаемся к MCP серверу(ам)
    try:
        await mcp_service.connect()
        if isinstance(mcp_service, MCPServiceManager):
            connected_servers = mcp_service.get_connected_servers()
            logger.info(f"MCP сервис подключен к {len(connected_servers)}/{len(config.mcp_server_urls)} серверам: {connected_servers}")
        else:
            logger.info(f"MCP сервис подключен к {config.mcp_server_url}")
    except Exception as e:
        logger.warning(f"Не удалось подключиться к MCP серверу(ам): {e}")
    
    # Настраиваем scheduler для ежедневных задач
    # Используем локальный timezone
    scheduler.add_job(
        daily_task_service.send_daily_analysis_to_all_users,
        trigger=CronTrigger(hour=10, minute=58, timezone=local_tz),  # Каждый день в 5:52 по локальному времени
        id='daily_task_analysis',
        replace_existing=True
    )
    
    # Запускаем scheduler
    scheduler.start()
    logger.info("Scheduler запущен")
    
    # Логируем все запланированные задачи (после запуска scheduler)
    jobs = scheduler.get_jobs()
    logger.info(f"Всего запланировано задач: {len(jobs)}")
    for job in jobs:
        # В APScheduler next_run_time может быть None до первого вычисления
        # Используем getattr для безопасного доступа
        next_run = getattr(job, 'next_run_time', None)
        if next_run:
            logger.info(f"  - Задача '{job.id}': следующий запуск в {next_run} (timezone: {local_tz})")
        else:
            logger.info(f"  - Задача '{job.id}': время следующего запуска будет вычислено scheduler'ом")
    
    try:
        logger.info("Бот запущен...")
        # Запускаем polling
        await dp.start_polling(bot)
    finally:
        # Останавливаем scheduler
        scheduler.shutdown()
        logger.info("Scheduler остановлен")
        # Закрываем подключение к MCP серверу
        if mcp_service.is_connected():
            await mcp_service.close()
        # Закрываем подключение к базе данных
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
