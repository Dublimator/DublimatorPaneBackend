import requests
import threading
import time

# Настройки
target_url = "http://localhost:80"  # Целевой URL
num_threads = 50                     # Количество потоков
request_interval = 0.01              # Задержка между запросами (в секундах)

# Функция для отправки HTTP-запросов
def send_http_requests():
    while True:
        try:
            response = requests.get(target_url)
            print(f"Отправлен HTTP-запрос: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Ошибка: {e}")
        time.sleep(request_interval)  # Задержка между запросами

# Запускаем потоки для отправки HTTP-запросов
threads = []
for _ in range(num_threads):
    thread = threading.Thread(target=send_http_requests)
    thread.start()
    threads.append(thread)

# Ждём завершения потоков (можно остановить с помощью Ctrl+C)
try:
    for thread in threads:
        thread.join()
except KeyboardInterrupt:
    print("Остановка программы...")