from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.api.schemas import PortfolioItemOut
from app.db import session_scope
from app.models import PortfolioItem, Service

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/portfolio", response_model=list[PortfolioItemOut])
def list_portfolio(category: str | None = None) -> list[PortfolioItemOut]:
    with session_scope() as s:
        q = (
            select(
                PortfolioItem,
                Service.name.label("service_name"),
                Service.category.label("service_category"),
            )
            .outerjoin(Service, PortfolioItem.service_id == Service.id)
            .where(PortfolioItem.is_visible == True)  # noqa: E712
            .order_by(PortfolioItem.sort_order)
        )
        if category:
            q = q.where(Service.category == category)
        rows = s.execute(q).all()

    return [
        PortfolioItemOut(
            id=item.id,
            title=item.title,
            image_url=item.image_url,
            service_id=item.service_id,
            service_name=service_name,
            service_category=service_category,
            sort_order=item.sort_order,
        )
        for item, service_name, service_category in rows
    ]
