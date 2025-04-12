import requests
import threading
import time

# URL вашего приложения (порт 8000 на хосте)
url = "http://localhost:3001"

def send_requests():
    while True:
        try:
            response = requests.get(url)
            print(f"Отправлен запрос: {response.status_code}")
        except Exception as e:
            print(f"Ошибка: {e}")
        time.sleep(0.01)  # Задержка между запросами (можно уменьшить для большей нагрузки)

# Запускаем 50 потоков для отправки запросов
threads = []
for _ in range(50):
    thread = threading.Thread(target=send_requests)
    thread.start()
    threads.append(thread)

# Ждём завершения (можно остановить с помощью Ctrl+C)
for thread in threads:
    thread.join()