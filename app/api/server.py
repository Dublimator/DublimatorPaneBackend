# app/api/server.py
from fastapi import APIRouter, HTTPException
from app.services.metrics_collector import get_system_metrics  # Импортируем сервис для сбора метрик

# Создаем роутер
router = APIRouter()

# Эндпоинт для получения метрик сервера
@router.get("/metrics")
async def get_server_metrics():
    try:
        # Получаем метрики сервера
        metrics = await get_system_metrics()
        return metrics
    except Exception as e:
        # В случае ошибки возвращаем HTTP 500
        raise HTTPException(status_code=500, detail=str(e))

# Эндпоинт для проверки здоровья сервера
@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Server is running"}

# Экспортируем роутер
__all__ = ["router"]