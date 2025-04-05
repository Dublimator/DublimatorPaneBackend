import asyncio
import logging
import time
from scapy.all import sniff
from scapy.layers.inet import IP
from typing import Dict, List, Optional
from app.bot import notify_dos_attack
from app.config.settings import Settings
from app.utils.data_handler import save_dos_data


# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки для обнаружения DOS-атак
THRESHOLD_REQUESTS_PER_SECOND = Settings.threshold_request_per_second  # Пороговое значение запросов в секунду
ANALYSIS_INTERVAL = Settings.network_analysis_interval  # Интервал анализа в секундах

# Глобальные переменные для хранения статистики
request_counts: Dict[str, int] = {}  # Счетчик запросов по IP-адресам
dos_incidents: List[Dict[str, str]] = []  # Список инцидентов DOS-атак

def analyze_packet(packet) -> None:
    """
    Анализирует каждый захваченный пакет.
    """
    global request_counts

    if IP in packet:
        ip_src = packet[IP].src  # IP-адрес источника

        # Увеличиваем счетчик запросов для данного IP
        if ip_src in request_counts:
            request_counts[ip_src] += 1
        else:
            request_counts[ip_src] = 1

def detect_dos() -> Optional[Dict[str, str]]:
    """
    Проверяет, есть ли признаки DOS-атаки.
    Возвращает информацию об инциденте, если атака обнаружена.
    """
    global request_counts, dos_incidents

    # Анализируем статистику запросов
    for ip, count in request_counts.items():
        if count > THRESHOLD_REQUESTS_PER_SECOND:
            # Фиксируем инцидент
            incident = {
                "ip": ip,
                "requests_per_second": count,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            dos_incidents.append(incident)
            request_counts[ip] = 0  # Сбрасываем счетчик для этого IP
            return incident

    return None

async def analyze_network() -> None:
    """
    Запускает анализ сетевого трафика.
    """
    logger.info("Анализ сетевого трафика запущен")

    # Запуск захвата пакетов в отдельном потоке
    loop = asyncio.get_event_loop()
    sniff_task = loop.run_in_executor(None, sniff, {"prn": analyze_packet, "store": False})

    # Периодическая проверка на DOS-атаки
    while True:
        await asyncio.sleep(ANALYSIS_INTERVAL)  # Асинхронная задержка
        incident = detect_dos()
        if incident:
            print(f"Обнаружена DOS-атака: {incident}")
            await save_dos_data(incident)  # Сохраняем данные о DOS-атаке
            await notify_dos_attack(incident)  # Уведомляем о DOS-атаке