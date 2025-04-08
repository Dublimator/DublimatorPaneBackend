# Используем официальный образ Python 3.12
FROM python:3.12-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app/app

# Копируем requirements.txt в контейнер
COPY requirements.txt ../

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r ../requirements.txt

# Копируем весь проект в контейнер
COPY . ../

# Указываем команду для запуска приложения
CMD ["python", "-m", "app.main"]