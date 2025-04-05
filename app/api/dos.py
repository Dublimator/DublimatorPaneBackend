from fastapi import APIRouter
from app.utils.data_handler import load_dos_data

router = APIRouter()

@router.get("/get-dos")
async def get_dos_attacks():
    data = await load_dos_data()
    return data


# Экспортируем роутер
__all__ = ["router"]