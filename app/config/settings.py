from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
import json
import aiofiles
import asyncio
from pathlib import Path

from app.utils import logger


class AlertSettings(BaseModel):
    """
    Модель для настроек уведомлений.
    """
    condition: bool = Field(default=False)  # Включено или выключено
    percent: int = Field(default=0)  # Пороговое значение (если применимо)

class NotificationSettings(BaseModel):
    """
    Модель для хранения всех настроек уведомлений.
    """
    # telegram_chat_id: ChatIDSettings = Field(default=0)
    container_stopped: AlertSettings = Field(default_factory=AlertSettings)
    ram: AlertSettings = Field(default_factory=AlertSettings)
    cpu: AlertSettings = Field(default_factory=AlertSettings)
    storage: AlertSettings = Field(default_factory=AlertSettings)
    dos: AlertSettings = Field(default_factory=AlertSettings)

class Settings(BaseSettings):
    # Настройки сервера
    host: str = "127.0.0.1"  # Хост по умолчанию
    port: int = 3001        # Порт по умолчанию

    # Настройки телеграм-бота
    telegram_bot_token: str = Field(default="your-telegram-bot-token", description="Токен телеграм-бота")
    telegram_chat_id: str = Field(default="your-chat-id", description="ID чата для уведомлений")

    # Настройки для анализа сети
    network_analysis_interval: int = 60  # Интервал анализа сети в секундах
    threshold_request_per_second: int = 100 # Количество запросов в секунду

    # Настройки уведомлений
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)



# Путь к файлу настроек
SETTINGS_FILE = Path("settings.json")

# Создаем экземпляр настроек
settings = Settings()

async def save_settings_to_file():
    """
    Сохраняет текущие настройки в JSON-файл.
    """
    try:
        # Преобразуем объект Settings в словарь
        settings_dict = settings.dict()

        # Сохраняем словарь в JSON-файл
        async with aiofiles.open(SETTINGS_FILE, mode="w", encoding="utf-8") as file:
            await file.write(json.dumps(settings_dict, indent=4, ensure_ascii=False))
        logger.info("Настройки сохранены в файл.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении настроек: {e}")

async def load_settings_from_file():
    """
    Загружает настройки из JSON-файла.
    """
    try:
        if SETTINGS_FILE.exists():
            async with aiofiles.open(SETTINGS_FILE, mode="r", encoding="utf-8") as file:
                content = await file.read()
                if content:
                    loaded_settings = json.loads(content)

                    # Обновляем настройки из файла
                    settings.host = loaded_settings.get("host", "127.0.0.1")
                    settings.port = loaded_settings.get("port", 3001)
                    settings.telegram_bot_token = loaded_settings.get("telegram_bot_token", "your-telegram-bot-token")
                    settings.telegram_chat_id = loaded_settings.get("telegram_chat_id", "your-chat-id")
                    settings.network_analysis_interval = loaded_settings.get("network_analysis_interval", 60)
                    settings.threshold_request_per_second = loaded_settings.get("threshold_request_per_second", 100)
                    settings.notifications = NotificationSettings(**loaded_settings.get("notifications", {}))

                    logger.info("Настройки загружены из файла.")
    except Exception as e:
        logger.error(f"Ошибка при загрузке настроек: {e}")


# Загружаем настройки при старте
asyncio.run(load_settings_from_file())