import asyncio
from datetime import datetime

from telegram import Bot, Update, BotCommand
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from ..config.settings import settings
from ..utils import logger, load_dos_data

# Инициализация бота
bot = Bot(token=settings.telegram_bot_token)

TELEGRAM_MESSAGE_LIMIT = 4096

# Функция для обработки команды /get_chat_id
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет пользователю его chat_id.
    """
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Ваш chat_id: {chat_id}")

async def get_dos_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет пользователю информацию о DOS-атаках, если он авторизован.
    """
    user_chat_id = update.message.chat_id
    if user_chat_id != int(settings.telegram_chat_id):
        await update.message.reply_text("Невозможно отправить данные в этом канале")
        return

    dos_data = await load_dos_data()
    if not dos_data:
        await update.message.reply_text("Нет данных")
        return

    # Формируем список частей сообщения для каждого инцидента
    incidents = []
    for incident in dos_data:
        try:
            time_start_value = incident["timeStart"]
            if isinstance(time_start_value, str):
                time_start_value = float(time_start_value)
            time_start = datetime.fromtimestamp(time_start_value).strftime("%d.%m.%Y %H:%M:%S")
        except (ValueError, TypeError) as e:
            time_start = "Некорректное время"
            logger.error(f"Ошибка при преобразовании времени: {e}, incident: {incident}")

        incident_text = (
            f"------------------------\n"
            f"Тип атаки: {incident['type']}\n"
            f"IP-адрес: {incident['sourceIp']}\n"
            f"Количество пакетов: {incident['count']}\n"
            f"Время начала: {time_start}\n"
            f"Статус: {'Активен' if incident['status'] else 'Завершён'}\n"
            f"------------------------"
        )
        incidents.append(incident_text)

    full_message = "Информация об атаках\n" + "\n".join(incidents)

    # Если сообщение короткое, отправляем его целиком
    if len(full_message) <= TELEGRAM_MESSAGE_LIMIT:
        await update.message.reply_text(full_message)
        return

    # Если сообщение длинное, разбиваем его на части
    current_part = "Информация об атаках\n"
    for incident_text in incidents:
        # Проверяем, влезет ли текущий инцидент в текущую часть
        if len(current_part) + len(incident_text) + 1 <= TELEGRAM_MESSAGE_LIMIT:
            current_part += "\n" + incident_text
        else:
            await update.message.reply_text(current_part)
            break

async def send_alert(message: str) -> None:
    """
    Отправляет уведомление в Telegram.
    """
    try:
        await bot.send_message(chat_id=settings.telegram_chat_id, text=message)
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

async def set_bot_commands() -> None:
    """
    Устанавливает список команд для бота.
    """
    commands = [
        BotCommand("get_chat_id", "Получить ваш chat_id"),
        BotCommand("get_dos_data", "Получить информацию о дос атаках"),
    ]
    await bot.set_my_commands(commands)

async def start_bot() -> None:
    """
    Запускает телеграм-бота.
    """
    try:
        application = ApplicationBuilder().token(settings.telegram_bot_token).build()

        application.add_handler(CommandHandler("get_chat_id", get_chat_id))
        application.add_handler(CommandHandler("get_dos_data", get_dos_data))

        await set_bot_commands()

        loop = asyncio.get_event_loop()
        if loop.is_running():
            await application.initialize()
            await application.start()
            logger.info("Бот запущен в существующем цикле событий")
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        else:
            logger.info("Бот запущен в новом цикле событий")
            await application.run_polling(allowed_updates=Update.ALL_TYPES)
        await bot.send_message(settings.telegram_chat_id, "Мониторинг активен")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise