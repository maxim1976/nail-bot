from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.admin.auth import require_admin_token
from app.admin.schemas import AdminPortfolioIn, AdminPortfolioOut
from app.db import session_scope
from app.models import PortfolioItem

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/portfolio", response_model=list[AdminPortfolioOut])
def list_portfolio(auth: None = Depends(require_admin_token)) -> list[AdminPortfolioOut]:
    with session_scope() as s:
        rows = (
            s.execute(select(PortfolioItem).order_by(PortfolioItem.sort_order))
            .scalars()
            .all()
        )
        return [AdminPortfolioOut.model_validate(r) for r in rows]


@router.post("/portfolio", response_model=AdminPortfolioOut, status_code=201)
def create_portfolio_item(
    body: AdminPortfolioIn,
    auth: None = Depends(require_admin_token),
) -> AdminPortfolioOut:
    with session_scope() as s:
        item = PortfolioItem(**body.model_dump())
        s.add(item)
        s.flush()
        return AdminPortfolioOut.model_validate(item)


@router.put("/portfolio/{item_id}", response_model=AdminPortfolioOut)
def update_portfolio_item(
    item_id: uuid.UUID,
    body: AdminPortfolioIn,
    auth: None = Depends(require_admin_token),
) -> AdminPortfolioOut:
    with session_scope() as s:
        item = s.get(PortfolioItem, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Portfolio item not found")
        for field, value in body.model_dump().items():
            setattr(item, field, value)
        s.flush()
        return AdminPortfolioOut.model_validate(item)


@router.delete("/portfolio/{item_id}", status_code=204)
def delete_portfolio_item(
    item_id: uuid.UUID,
    auth: None = Depends(require_admin_token),
) -> None:
    with session_scope() as s:
        item = s.get(PortfolioItem, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Portfolio item not found")
        s.delete(item)
