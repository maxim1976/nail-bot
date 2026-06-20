from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.schemas import ServiceOut
from app.db import session_scope
from app.models import Service

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/services", response_model=list[ServiceOut])
def list_services() -> list[Service]:
    with session_scope() as s:
        rows = (
            s.execute(
                select(Service)
                .where(Service.is_available == True)  # noqa: E712
                .order_by(Service.sort_order)
            )
            .scalars()
            .all()
        )
        return list(rows)
