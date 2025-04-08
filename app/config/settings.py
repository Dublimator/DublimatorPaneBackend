from collections import defaultdict

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
    threshold_syn: int = 100 # SYN-пакетов в секунду с одного IP = атака
    threshold_http: int = 200 # HTTP-запросов в секунду с одного IP = атака
    threshold_udp: int = 400 # UDP-запросов в секунду с одного IP = атака
    attack_expiry_time: int = 10 # Время с последнего пакета когда атака считается завершенной
    interface: str = "eth0" # Сетевой интерфейс
    whitelist_ip: list[str] = Field(default_factory=lambda: ["1.1.1.1", "8.8.8.8", "10.0.0.0/8"])  # Белый список IP

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
    Загружает настройки из JSON-файла и обновляет глобальный объект settings.
    """
    global settings  # Объявляем, что будем изменять глобальный объект settings
    try:
        if SETTINGS_FILE.exists():
            async with aiofiles.open(SETTINGS_FILE, mode="r", encoding="utf-8") as file:
                content = await file.read()
                if content:
                    # Загружаем JSON из файла
                    loaded_settings = json.loads(content)

                    # Создаём новый экземпляр Settings из загруженных данных
                    settings = Settings(**loaded_settings)
                    logger.info("Настройки успешно загружены из файла.")
        else:
            logger.info(f"Файл настроек {SETTINGS_FILE} не найден. Используются настройки по умолчанию.")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при разборе JSON в файле настроек: {e}")
    except Exception as e:
        logger.error(f"Ошибка при загрузке настроек: {e}")


# Загружаем настройки при старте
asyncio.run(load_settings_from_file())