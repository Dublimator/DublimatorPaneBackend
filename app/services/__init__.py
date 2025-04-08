# app/services/__init__.py
from .metrics_collector import get_container_metrics, get_system_metrics, analyze_metrics
from .network_analyzer import analyze_network

# Экспортируем все сервисы для удобного импорта

__all__ = [
    "get_container_metrics",
    "get_system_metrics",
    "analyze_metrics",
    "analyze_network",
]