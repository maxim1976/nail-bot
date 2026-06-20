from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.admin.auth import require_admin_token
from app.admin.schemas import StudioProfileIn, StudioProfileOut
from app.db import session_scope
from app.models import StudioProfile

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/studio", response_model=StudioProfileOut)
def get_studio(auth: None = Depends(require_admin_token)) -> StudioProfileOut:
    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        if profile is None:
            raise HTTPException(status_code=404, detail="Studio profile not configured")
        return StudioProfileOut.model_validate(profile)


@router.put("/studio", response_model=StudioProfileOut)
def put_studio(
    body: StudioProfileIn,
    auth: None = Depends(require_admin_token),
) -> StudioProfileOut:
    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        if profile is None:
            profile = StudioProfile(id=1)
            s.add(profile)
        for field, value in body.model_dump().items():
            setattr(profile, field, value)
        s.flush()
        return StudioProfileOut.model_validate(profile)
