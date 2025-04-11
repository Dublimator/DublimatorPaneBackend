import asyncio
import os
from datetime import datetime, timedelta
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

# Создаем очереди для метрик с ограничением размера
system_metrics_queue = asyncio.Queue(maxsize=1)
docker_metrics_queue = asyncio.Queue(maxsize=1)

# Переменные для хранения последних метрик
latest_system_metrics: Dict[str, Any] = {}
latest_docker_metrics: List[Dict[str, Any]] = []

def format_uptime(seconds: float) -> str:
    """Форматирует аптайм в стиль 'Up X hours' или 'Up X minutes'."""
    if seconds is None:
        return "N/A"
    delta = timedelta(seconds=int(seconds))
    if delta.days > 0:
        return f"Up {delta.days} days"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"Up {hours} hours"
    minutes = (delta.seconds % 3600) // 60
    if minutes > 0:
        return f"Up {minutes} minutes"
    return f"Up {delta.seconds} seconds"

async def get_container_metrics() -> List[Dict[str, Any]]:
    """
    Собирает метрики Docker-контейнеров.
    Возвращает список контейнеров с их метриками.
    """
    containers_metrics = []
    try:
        containers = client.containers.list()
        for container in containers:
            stats = container.stats(stream=False)
            container_info = container.attrs
            container_id = container.id
            container_name = container.name
            container_state = container.status
            state = container_info.get("State", {})
            status = state.get("Status", "").capitalize()

            uptime = None
            if status.lower() == "running":
                started_at = state.get("StartedAt")
                if started_at:
                    try:
                        start_time = datetime.strptime(started_at[:19], "%Y-%m-%dT%H:%M:%S")
                        uptime = (datetime.utcnow() - start_time).total_seconds()
                    except ValueError as e:
                        logger.error(f"Ошибка при парсинге времени запуска для контейнера {container_name}: {e}")

            cpu_stats = stats.get("cpu_stats", {})
            cpu_usage = cpu_stats.get("cpu_usage", {})
            cpu_percent = round(cpu_usage.get("total_usage", 0) / 10 ** 9, 2)

            memory_stats = stats.get("memory_stats", {})
            memory_usage = memory_stats.get("usage", 0) / (1024 * 1024)
            memory_limit = memory_stats.get("limit", 0) / (1024 * 1024)

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

            container_metrics = {
                "id": container_id,
                "name": container_name,
                "state": container_state,
                "uptime": format_uptime(uptime),
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
    sys_metrics = {}
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_usage = memory.used / (1024 * 1024)
        memory_total = memory.total / (1024 * 1024)
        disk_path = "/host" if os.path.exists("/host") else "/"
        disk = psutil.disk_usage(disk_path)
        disk_usage = disk.used / (1024 * 1024)
        disk_total = disk.total / (1024 * 1024)
        uptime = (datetime.now().timestamp() - psutil.boot_time())

        sys_metrics = {
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
    return sys_metrics

async def analyze_metrics() -> None:
    """
    Запускает анализ метрик и отправляет их в очереди.
    """
    global latest_system_metrics, latest_docker_metrics
    logger.info("Анализ метрик запущен")
    while True:
        try:
            # Собираем метрики
            docker_metrics = await get_container_metrics()
            system_metrics = await get_system_metrics()

            # Обновляем последние метрики
            latest_docker_metrics = docker_metrics
            latest_system_metrics = system_metrics

            # Помещаем метрики в очереди, очищая старые данные
            try:
                await docker_metrics_queue.put(docker_metrics)
            except asyncio.QueueFull:
                await docker_metrics_queue.get()  # Удаляем старые данные
                await docker_metrics_queue.put(docker_metrics)

            try:
                await system_metrics_queue.put(system_metrics)
            except asyncio.QueueFull:
                await system_metrics_queue.get()
                await system_metrics_queue.put(system_metrics)

            # Проверяем пороговые значения и отправляем уведомления
            cpu_percent = system_metrics.get("cpuPercent", 0)
            memory_usage = system_metrics.get("memory", {}).get("usage", 0)
            memory_total = system_metrics.get("memory", {}).get("total", 1)
            disk_usage = system_metrics.get("disk", {}).get("usage", 0)
            disk_total = system_metrics.get("disk", {}).get("total", 1)

            if cpu_percent >= settings.notifications.cpu.percent:
                await notify_cpu_usage(cpu_percent)
            if memory_usage / memory_total * 100 >= settings.notifications.ram.percent:
                await notify_ram_usage(memory_usage / memory_total * 100)
            if disk_usage / disk_total * 100 >= settings.notifications.storage.percent:
                await notify_storage_usage(disk_usage / disk_total * 100)

        except Exception as e:
            logger.error(f"Ошибка в analyze_metrics: {e}")
        await asyncio.sleep(ANALYSIS_INTERVAL)

def start_metrics_collection():
    """Запускает сбор метрик в фоновом режиме."""
    asyncio.create_task(analyze_metrics())

async def get_latest_docker_metrics() -> List[Dict[str, Any]]:
    """
    Возвращает последние метрики Docker.
    """
    global latest_docker_metrics
    try:
        # Если есть данные в переменной, возвращаем их
        if latest_docker_metrics:
            return latest_docker_metrics
        # Проверяем очередь
        if not docker_metrics_queue.empty():
            latest_docker_metrics = await docker_metrics_queue.get()
            return latest_docker_metrics
        # Если данных нет, возвращаем пустой список
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении Docker метрик: {e}")
        return []

async def get_latest_system_metrics() -> Dict[str, Any]:
    """
    Возвращает последние системные метрики.
    """
    global latest_system_metrics
    try:
        if latest_system_metrics:
            return latest_system_metrics
        if not system_metrics_queue.empty():
            latest_system_metrics = await system_metrics_queue.get()
            return latest_system_metrics
        return {}
    except Exception as e:
        logger.error(f"Ошибка при получении системных метрик: {e}")
        return {}