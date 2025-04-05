import asyncio
from datetime import datetime
import logging
import docker
import psutil
from typing import List, Dict, Any
from ..config.settings import settings
from app.bot import notify_ram_usage, notify_cpu_usage, notify_storage_usage
from ..utils import logger

# Интервал анализа (в секундах)
ANALYSIS_INTERVAL = 10

# Создаем клиент Docker
client = docker.from_env()

async def get_container_metrics() -> List[Dict[str, Any]]:
    """
    Собирает метрики Docker-контейнеров.
    Возвращает список контейнеров с их метриками.
    """
    containers_metrics = []

    try:
        # Получаем список всех контейнеров
        containers = client.containers.list()

        for container in containers:
            # Получаем статистику контейнера
            stats = container.stats(stream=False)

            # Извлекаем нужные метрики
            container_id = container.id
            container_name = container.name
            container_state = container.status
            uptime = "N/A"  # Время работы контейнера (можно вычислить, если нужно)

            # CPU
            cpu_stats = stats.get("cpu_stats", {})
            cpu_usage = cpu_stats.get("cpu_usage", {})
            cpu_percent = round(cpu_usage.get("total_usage", 0) / 10 ** 9, 2)  # Преобразуем наносекунды в проценты

            # Память
            memory_stats = stats.get("memory_stats", {})
            memory_usage = memory_stats.get("usage", 0) / (1024 * 1024)  # Преобразуем байты в мегабайты
            memory_limit = memory_stats.get("limit", 0) / (1024 * 1024)  # Преобразуем байты в мегабайты

            # Сеть
            network_stats = stats.get("networks", {})
            network_metrics = {}
            for interface, metrics in network_stats.items():
                network_metrics[interface] = {
                    "rx_bytes": metrics.get("rx_bytes", 0),
                    "rx_packets": metrics.get("rx_packets", 0),
                    "rx_errors": metrics.get("rx_errors", 0),
                    "rx_dropped": metrics.get("rx_dropped", 0),
                    "tx_bytes": metrics.get("tx_bytes", 0),
                    "tx_packets": metrics.get("tx_packets", 0),
                    "tx_errors": metrics.get("tx_errors", 0),
                    "tx_dropped": metrics.get("tx_dropped", 0),
                }

            # Формируем метрики контейнера
            container_metrics = {
                "id": container_id,
                "name": container_name,
                "state": container_state,
                "uptime": uptime,
                "cpuPercent": cpu_percent,
                "memory": {
                    "usage": round(memory_usage, 2),
                    "limit": round(memory_limit, 2),
                },
                "network": network_metrics,
            }

            containers_metrics.append(container_metrics)

    except Exception as e:
        logger.error(f"Ошибка при сборе метрик контейнеров: {e}")

    return containers_metrics

async def get_system_metrics() -> Dict[str, Any]:
    """
    Собирает системные метрики (CPU, память, диск и т.д.).
    Возвращает словарь с метриками.
    """
    system_metrics = {}

    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)

        # Память
        memory = psutil.virtual_memory()
        memory_usage = memory.used / (1024 * 1024)  # Преобразуем байты в мегабайты
        memory_total = memory.total / (1024 * 1024)  # Преобразуем байты в мегабайты

        # Диск
        disk = psutil.disk_usage("/")
        disk_usage = disk.used / (1024 * 1024)  # Преобразуем байты в мегабайты
        disk_total = disk.total / (1024 * 1024)  # Преобразуем байты в мегабайты

        uptime = (datetime.now().timestamp() - psutil.boot_time())

        # Формируем системные метрики
        system_metrics = {
            "cpuPercent": cpu_percent,
            "memory": {
                "usage": round(memory_usage, 2),
                "total": round(memory_total, 2),
            },
            "disk": {
                "usage": round(disk_usage, 2),
                "total": round(disk_total, 2),
            },
            "uptime": uptime,
        }

    except Exception as e:
        logger.error(f"Ошибка при сборе системных метрик: {e}")

    return system_metrics

async def analyze_metrics() -> None:
    """
    Запускает анализ метрик.
    """
    logger.info("Анализ метрик запущен")

    while True:
        try:
            await asyncio.sleep(ANALYSIS_INTERVAL)  # Асинхронная задержка

            # Собираем метрики контейнеров и системы
            metrics = await get_container_metrics()
            sys_metrics = await get_system_metrics()

            # Проверяем пороговые значения и отправляем уведомления
            cpu_percent = sys_metrics.get("cpuPercent", 0)
            memory_usage = sys_metrics.get("memory", {}).get("usage", 0)
            memory_total = sys_metrics.get("memory", {}).get("total", 1)  # Избегаем деления на ноль
            disk_usage = sys_metrics.get("disk", {}).get("usage", 0)
            disk_total = sys_metrics.get("disk", {}).get("total", 1)  # Избегаем деления на ноль

            if cpu_percent >= settings.notifications.cpu.percent:
                await notify_cpu_usage(cpu_percent)

            if memory_usage / memory_total * 100 >= settings.notifications.ram.percent:
                await notify_ram_usage(memory_usage / memory_total * 100)

            if disk_usage / disk_total * 100 >= settings.notifications.storage.percent:
                await notify_storage_usage(disk_usage / disk_total * 100)

        except Exception as e:
            logger.error(f"Ошибка в analyze_metrics: {e}")