from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from config.settings import settings
from app.api.server import router as server_router
from app.api.metrics import router as metrics_router
from app.api.dos import router as dos_router
from app.api.notifications import router as notifications_router
from app.services.network_analyzer import analyze_network
from app.services.metrics_collector import analyze_metrics
from app.bot import start_bot
import asyncio

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем экземпляр FastAPI приложения
app = FastAPI(title="Server Monitoring App", version="1.0.0")

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
        # Запуск бота
        bot_task = asyncio.create_task(start_bot())

        # Запуск анализа сети и сбора метрик параллельно
        network_task = asyncio.create_task(analyze_network())
        metrics_task = asyncio.create_task(analyze_metrics())

        # Ожидаем завершения задач (если нужно)
        await asyncio.gather(bot_task, network_task, metrics_task)
    except Exception as e:
        logger.error(f"Ошибка в фоновых задачах: {e}")

# Запуск фоновых задач при старте приложения
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_background_tasks())

# Запуск приложения
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)