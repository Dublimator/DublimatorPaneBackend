# app/api/__init__.py
from .server import router as server_router
from .metrics import router as metrics_router
from .dos import router as dos_router
from .notifications import router as notifications_router

# Экспортируем все роутеры для удобного импорта
__all__ = ["server_router", "metrics_router", "dos_router", "notifications_router"]