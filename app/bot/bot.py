from datetime import datetime

from telegram import Bot, Update
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from ..config.settings import settings
from ..utils import logger

# Инициализация бота
bot = Bot(token=settings.telegram_bot_token)

# Функция для обработки команды /getChatId
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет пользователю его chat_id.
    """
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Ваш chat_id: {chat_id}")

async def send_alert(message: str) -> None:
    """
    Отправляет уведомление в Telegram.
    """
    try:
        await bot.send_message(chat_id=settings.telegram_chat_id, text=message)
        logger.info(f"Уведомление отправлено: {message}")
    except TelegramError as e:
        logger.error(f"Ошибка при отправке уведомления: {e}")

async def notify_dos_attack(incidents: []) -> None:
    """
    Отправляет уведомление о DOS-атаке.
    """
    if settings.notifications.dos.condition:
        message = f"⚠️ Обнаружена атака \n"

        for incident in incidents:
            time_start = datetime.fromtimestamp(incident["timeStart"]).strftime("%d.%m.%Y %H:%M:%S")

            # Формируем строку message
            message = message + (
                f"------------------------\n"
                f"Тип атаки: {incident['type']}\n"
                f"IP-адрес: {incident['sourceIp']}\n"
                f"Количество пакетов: {incident['count']}\n"
                f"Время начала: {time_start}\n"
                f"Статус: {'Активен' if incident['status'] else 'Завершён'}\n"
                f"------------------------\n"
            )


        await send_alert(message)

async def notify_container_stopped(container_name: str) -> None:
    """
    Отправляет уведомление об остановке контейнера.
    """
    if settings.notifications.container_stopped.condition:
        message = f"🚨 Контейнер остановлен: {container_name}"
        await send_alert(message)

async def notify_ram_usage(usage_percent: float) -> None:
    """
    Отправляет уведомление о превышении использования RAM.
    """
    if settings.notifications.ram.condition and usage_percent >= settings.notifications.ram.percent:
        message = f"⚠️ Превышение использования RAM: {round(usage_percent)}%"
        await send_alert(message)

async def notify_cpu_usage(usage_percent: float) -> None:
    """
    Отправляет уведомление о высокой нагрузке CPU.
    """
    if settings.notifications.cpu.condition and usage_percent >= settings.notifications.cpu.percent:
        message = f"⚠️ Высокая нагрузка CPU: {round(usage_percent)}%"
        await send_alert(message)

async def notify_storage_usage(usage_percent: float) -> None:
    """
    Отправляет уведомление о заполнении хранилища.
    """
    if settings.notifications.storage.condition and usage_percent >= settings.notifications.storage.percent:
        message = f"⚠️ Хранилище заполнено: {round(usage_percent)}%"
        await send_alert(message)

async def notify_test_message() -> None:
    """
    Отправляет тестовое сообщение.
    """
    message = "Тестовое сообщение"
    await send_alert(message)

async def start_bot() -> None:
    """
    Запускает телеграм-бота.
    """
    try:
        # Создаем приложение для бота
        application = ApplicationBuilder().token(settings.telegram_bot_token).build()

        # Регистрируем обработчик команды /getChatId
        application.add_handler(CommandHandler("getChatId", get_chat_id))

        # Запускаем бота
        logger.info("Бот запущен")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")