import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.utils import logger
from config.settings import settings
from app.api.server import router as server_router
from app.api.metrics import router as metrics_router
from app.api.dos import router as dos_router
from app.api.notifications import router as notifications_router
from app.services.network_analyzer import analyze_network
from app.services.metrics_collector import analyze_metrics
from app.bot import start_bot
import asyncio

# Настройка логгеров Uvicorn и FastAPI
def configure_loggers():
    # Отключаем стандартные логгеры Uvicorn
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = False

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = False

    # Отключаем стандартный логгер FastAPI
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.handlers.clear()
    fastapi_logger.propagate = False

# Создаем экземпляр FastAPI приложения
app = FastAPI(title="DublimatorPane", version="1.0.0")

# Применяем настройки логгеров
configure_loggers()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все домены
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

# Подключаем роутеры
app.include_router(server_router, prefix="/server", tags=["server"])
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
app.include_router(dos_router, prefix="/dos", tags=["dos"])
app.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

async def run_background_tasks():
    """
    Запускает фоновые задачи (бот, анализ сети и сбор метрик).
    """
    try:
        logger.info("Запуск фоновых задач...")

        # Запуск бота
        bot_task = asyncio.create_task(start_bot())
        logger.info("Бот запущен")

        # Запуск анализа сети и сбора метрик параллельно
        network_task = asyncio.create_task(analyze_network())
        metrics_task = asyncio.create_task(analyze_metrics())
        logger.info("Сервисы мониторинга запущены")

        await asyncio.gather(bot_task, network_task, metrics_task)
    except Exception as e:
        logger.error(f"Ошибка в фоновых задачах: {e}")
        raise

# Запуск фоновых задач при старте приложения
@app.on_event("startup")
async def startup_event():
    logger.info(f"Запуск приложения на {settings.host}:{settings.port}")
    asyncio.create_task(run_background_tasks())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Завершение работы приложения")

# Запуск приложения
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_config=None,  # Отключаем стандартную конфигурацию логов
        access_log=False  # Отключаем access-логи
    )