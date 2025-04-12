from fastapi import APIRouter, HTTPException
from app.services.metrics_collector import get_latest_docker_metrics_sync
from app.utils import logger

router = APIRouter()

# Эндпоинт для получения метрик сервера
@router.get("/docker")
async def get_docker_metrics():
    try:
        metrics = get_latest_docker_metrics_sync()
        return metrics
    except Exception as e:
        # В случае ошибки возвращаем HTTP 500
        raise HTTPException(status_code=500, detail=str(e))


# Экспортируем роутер
__all__ = ["router"]