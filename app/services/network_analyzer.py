import asyncio
import time
import ipaddress

from collections import defaultdict

from scapy.packet import Raw

from app.bot.bot import notify_dos_attack
from ..utils import logger
from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.sendrecv import AsyncSniffer
from app.config import settings
from app.utils.data_handler import save_dos_data

# Конфигурация
THRESHOLD_SYN = settings.threshold_syn  # SYN-пакетов в секунду с одного IP = атака
THRESHOLD_HTTP = settings.threshold_http  # HTTP-запросов в секунду с одного IP = атака
THRESHOLD_UDP = settings.threshold_udp  # UDP-запросов в секунду с одного IP = атака
CLEANUP_INTERVAL = 60  # Сбрасываем счетчики каждые 60 сек
ATTACK_EXPIRY_TIME = settings.attack_expiry_time  # Время после которого атака считается завершенной
INTERFACE = settings.interface  # Сетевой интерфейс
WHITELIST = settings.whitelist_ip

# Глобальные счетчики
syn_count = defaultdict(int)
http_count = defaultdict(int)
udp_count = defaultdict(int)
last_cleanup = time.time()

incidents = defaultdict(list)

# Функция для сброса счётчиков
def reset_counters():
    """Сброс счетчиков по таймеру"""
    global last_cleanup
    current_time = time.time()
    if current_time - last_cleanup >= CLEANUP_INTERVAL:
        syn_count.clear()
        http_count.clear()
        udp_count.clear()
        last_cleanup = current_time
        logger.debug("[*] Counters reset")

# Функция для получения активного инцидента (status=True)
def get_active_incident(src_ip, typeI):
    if incidents[src_ip]:  # Если есть инциденты для IP
        for incident in incidents[src_ip]:
            if incident["status"] is True and incident["type"] == typeI:  # Ищем активный инцидент
                return incident
    return None

# Функция для обновления или создания инцидента
def update_or_create_incident(src_ip, attack_type, count):
    current_time = time.time()
    active_incident = get_active_incident(src_ip, attack_type)

    if active_incident:
        # Обновляем существующий инцидент
        active_incident["timeLastPacket"] = current_time
        active_incident["count"] = count
        logger.debug(f"Обновлён инцидент для {src_ip}: {active_incident}")
    else:
        # Создаём новый инцидент
        new_incident = {
            "sourceIp": src_ip,
            "timeStart": current_time,
            "timeLastPacket": current_time,
            "notification": False,
            "status": True,
            "type": attack_type,
            "count": count,
        }
        incidents[src_ip].append(new_incident)
        logger.debug(f"Создан новый инцидент для {src_ip}: {new_incident}")

def is_whitelisted(ip):
    """Проверка IP в белом списке (Cloudflare, ваши серверы и т.д.)"""
    for net in WHITELIST:
        if ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(net):
            return True
    return False

def analyze_packet(packet):
    if not packet.haslayer(IP):
        return

    src_ip = packet[IP].src

    # Игнорируем белый список
    if is_whitelisted(src_ip):
        return

    # Детектор SYN-флуда
    if packet.haslayer(TCP) and packet[TCP].flags == "S":
        syn_count[src_ip] += 1
        if syn_count[src_ip] > THRESHOLD_SYN:
            update_or_create_incident(src_ip, "SYN Flood", syn_count[src_ip])

    # Детектор HTTP-флуда
    elif packet.haslayer(TCP) and packet.haslayer(Raw):
        raw = packet[Raw].load.decode(errors="ignore")
        if "GET" in raw or "POST" in raw:
            http_count[src_ip] += 1
            if http_count[src_ip] > THRESHOLD_HTTP:
                update_or_create_incident(src_ip, "HTTP Flood", http_count[src_ip])

    # Детектор UDP-флуда
    elif packet.haslayer(UDP):
        udp_count[src_ip] += 1
        if udp_count[src_ip] > THRESHOLD_UDP:
            update_or_create_incident(src_ip, "UDP Flood", udp_count[src_ip])

    # Сбрасываем счётчики по таймеру
    reset_counters()

async def analyze_traffic():
    current_time = time.time()
    temp_incidents = []

    for src_ip in list(incidents.keys()):
        for incident in incidents[src_ip][:]:
            time_last_packet = incident["timeLastPacket"]

            # Проверяем, прошло ли ATTACK_EXPIRY_TIME
            if current_time - time_last_packet >= ATTACK_EXPIRY_TIME and incident["status"] is True:
                incident["status"] = False
                incident["notification"] = False
                logger.debug(f"Инцидент для {src_ip} завершён: {incident}")

                # Сбрасываем счётчики для этого IP
                if incident["type"] == "SYN Flood":
                    syn_count[src_ip] = 0
                elif incident["type"] == "HTTP Flood":
                    http_count[src_ip] = 0
                elif incident["type"] == "UDP Flood":
                    udp_count[src_ip] = 0

                # Добавляем завершённый инцидент в temp_incidents
                temp_incidents.append(incident)
                incident["notification"] = True

                # Сохраняем данные об инциденте
                try:
                    await save_dos_data(incident)
                except Exception as e:
                    logger.error(f"Ошибка при сохранении данных инцидента для {src_ip}: {e}")

                # Удаляем завершённый инцидент из incidents
                incidents[src_ip].remove(incident)

            elif incident["status"] is True and incident["notification"] is False:
                incident["notification"] = True
                temp_incidents.append(incident)

        # Если список инцидентов пуст, удаляем ключ
        if not incidents[src_ip]:
            del incidents[src_ip]

    # Отправляем уведомления после обработки всех инцидентов
    if temp_incidents:
        try:
            await notify_dos_attack(temp_incidents)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")

async def analyze_network() -> None:
    """
    Запускает анализ сетевого трафика.
    """
    logger.info("Анализ сетевого трафика запущен")
    sniffer = None

    try:
        # Запускаем сниффер (не асинхронно, так как AsyncSniffer работает в отдельном потоке)
        sniffer = AsyncSniffer(iface=INTERFACE, prn=analyze_packet, store=False)
        sniffer.start()

        # Бесконечный цикл проверки
        while True:
            await analyze_traffic()  # Ваша функция анализа трафика
            await asyncio.sleep(1)  # Добавляем небольшую задержку, чтобы не нагружать CPU

    except asyncio.CancelledError:
        logger.info("Анализ сетевого трафика остановлен")
    except Exception as e:
        logger.error(f"Ошибка в analyze_network: {e}")
        raise
    finally:
        if sniffer:
            sniffer.stop()