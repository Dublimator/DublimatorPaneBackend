# app/utils/data_handler.py
import json
import aiofiles
from typing import List, Dict, Optional
from pathlib import Path

# Путь к файлу data.json
DATA_FILE = Path("data.json")

async def save_dos_data(incident: Dict[str, str]) -> None:
    """
    Сохраняет данные о DOS-атаке в файл data.json.
    """
    try:
        # Читаем существующие данные
        existing_data = await load_dos_data() or []

        # Добавляем новый инцидент
        existing_data.append(incident)

        # Записываем обновленные данные в файл
        async with aiofiles.open(DATA_FILE, mode="w", encoding="utf-8") as file:
            await file.write(json.dumps(existing_data, indent=4, ensure_ascii=False))

        print(f"Данные о DOS-атаке сохранены: {incident}")
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

async def load_dos_data() -> Optional[List[Dict[str, str]]]:
    """
    Загружает данные о DOS-атаках из файла data.json.
    """
    try:
        if not DATA_FILE.exists():
            return []

        async with aiofiles.open(DATA_FILE, mode="r", encoding="utf-8") as file:
            content = await file.read()
            return json.loads(content) if content else []
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return None

async def clear_dos_data() -> None:
    """
    Очищает файл data.json.
    """
    try:
        async with aiofiles.open(DATA_FILE, mode="w", encoding="utf-8") as file:
            await file.write(json.dumps([], indent=4, ensure_ascii=False))
        print("Файл data.json очищен.")
    except Exception as e:
        print(f"Ошибка при очистке данных: {e}")