from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.bot.bot import notify_test_message
from ..config.settings import settings, save_settings_to_file

router = APIRouter()


class AlertSettings(BaseModel):
    condition: bool
    percent: int = 0

class NotificationSettings(BaseModel):
    container_stopped: AlertSettings
    ram: AlertSettings
    cpu: AlertSettings
    storage: AlertSettings
    dos: AlertSettings

@router.get("/get-settings")
async def get_notification_settings():
    """
    Возвращает текущие настройки уведомлений.
    """
    resp = settings.notifications.dict()
    resp["telegram_chat_id"] = settings.telegram_chat_id
    return resp

@router.post("/save-settings")
async def save_notification_settings(new_settings: NotificationSettings):
    """
    Сохраняет новые настройки уведомлений.
    """

    # Обновляем настройки в памяти
    settings.notifications = new_settings

    # Сохраняем настройки в файл
    await save_settings_to_file()

    return {"status": "success", "message": "Настройки сохранены"}

@router.get("/test-message")
async def test_message():
    """
    Возвращает текущие настройки уведомлений.
    """
    await notify_test_message()

    return


@router.get("/confirm-chat-id")
async def save_chat_id(chat_id: str = Query(..., description="ID чата в Telegram")):
    """
    Обновляет chat_id телеграмма в настройках.

    Пример запроса:
    `GET /confirm-chat-id?chat_id=123456789`
    """
    settings.telegram_chat_id = chat_id
    await save_settings_to_file()

    return {
        "status": "success",
        "message": "Chat ID обновлен",
    }