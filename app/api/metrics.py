from fastapi import APIRouter, HTTPException
from app.services.metrics_collector import get_container_metrics  # Импортируем сервис для сбора метрик


router = APIRouter()

# Эндпоинт для получения метрик сервера
@router.get("/docker")
async def get_docker_metrics():
    try:
        # Получаем метрики контейнеров
        metrics = await get_container_metrics()
        return metrics
    except Exception as e:
        # В случае ошибки возвращаем HTTP 500
        raise HTTPException(status_code=500, detail=str(e))


# Экспортируем роутер
__all__ = ["router"]