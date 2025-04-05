# project/app/utils/logger.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import colorlog


class AppLogger:
    def __init__(self):
        self.logger = logging.getLogger("app")
        self.logger.setLevel(logging.INFO)  # Уровень по умолчанию

        # Создаем папку для логов если её нет
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Форматтеры
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )

        # Консольный обработчик с цветами
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Файловый обработчик (10 MB, 5 файлов ротации)
        file_handler = RotatingFileHandler(
            "logs/app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger


# Глобальный экземпляр логгера
logger = AppLogger().get_logger()