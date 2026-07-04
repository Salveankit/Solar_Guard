from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.database.session import get_engine
from app.services.data_loader import DemoDataLoader

router = APIRouter(prefix="/api/data", tags=["data"])


class LoadDemoRequest(BaseModel):
    reset_existing: bool = True


@router.post("/load-demo")
def load_demo(request: LoadDemoRequest) -> dict:
    settings = get_settings()
    loader = DemoDataLoader(settings.resolved_raw_data_dir, get_engine())
    return loader.load_demo(reset_existing=request.reset_existing)
