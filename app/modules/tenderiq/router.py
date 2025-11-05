from fastapi import APIRouter

from app.modules.tenderiq.endpoints import tenders
from app.modules.tenderiq.endpoints import analyze

router = APIRouter()

router.include_router(tenders.router)
router.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])
