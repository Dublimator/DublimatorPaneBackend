# app/utils/__init__.py
from .data_handler import save_dos_data, load_dos_data, clear_dos_data

# Экспортируем функции для удобного импорта
__all__ = [
    "save_dos_data",
    "load_dos_data",
    "clear_dos_data",
]