
from fastapi import APIRouter

from core.health import full_health_check


router = APIRouter(tags=["system"])


@router.get("/system/health")
async def health_check():
    return await full_health_check()
