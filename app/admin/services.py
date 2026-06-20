from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.admin.auth import require_admin_token
from app.admin.schemas import AdminServiceIn, AdminServiceOut
from app.db import session_scope
from app.models import Service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/services", response_model=list[AdminServiceOut])
def list_services(auth: None = Depends(require_admin_token)) -> list[AdminServiceOut]:
    with session_scope() as s:
        rows = s.execute(select(Service).order_by(Service.sort_order)).scalars().all()
        return [AdminServiceOut.model_validate(r) for r in rows]


@router.post("/services", response_model=AdminServiceOut, status_code=201)
def create_service(
    body: AdminServiceIn,
    auth: None = Depends(require_admin_token),
) -> AdminServiceOut:
    with session_scope() as s:
        svc = Service(**body.model_dump())
        s.add(svc)
        s.flush()
        return AdminServiceOut.model_validate(svc)


@router.put("/services/{service_id}", response_model=AdminServiceOut)
def update_service(
    service_id: uuid.UUID,
    body: AdminServiceIn,
    auth: None = Depends(require_admin_token),
) -> AdminServiceOut:
    with session_scope() as s:
        svc = s.get(Service, service_id)
        if svc is None:
            raise HTTPException(status_code=404, detail="Service not found")
        for field, value in body.model_dump().items():
            setattr(svc, field, value)
        s.flush()
        return AdminServiceOut.model_validate(svc)


@router.delete("/services/{service_id}", status_code=204)
def delete_service(
    service_id: uuid.UUID,
    auth: None = Depends(require_admin_token),
) -> None:
    with session_scope() as s:
        svc = s.get(Service, service_id)
        if svc is None:
            raise HTTPException(status_code=404, detail="Service not found")
        try:
            s.delete(svc)
            s.flush()
        except IntegrityError:
            raise HTTPException(status_code=409, detail="Service has existing appointments")
