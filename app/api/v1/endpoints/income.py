from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session
from datetime import date
import math

from app import crud, models, schemas
from app.api import deps
from app.schemas.page import Page
from app.schemas.transaction import IncomeCreate, IncomeUpdate, IncomeAssign
from app.crud.crud_income import income as crud_income
from app.schemas.wallet import Wallet
from pydantic import BaseModel

router = APIRouter()


class IncomeAssignResponse(BaseModel):
    income: schemas.Income
    wallet: Wallet


@router.get("/", response_model=Page[schemas.Income])
def read_incomes(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Any:
    """
    Retrieve incomes for the current user with pagination and filtering.
    """
    items, total = crud_income.get_multi_by_user(
        db=db,
        user=current_user,
        page=page,
        size=size,
        start_date=start_date,
        end_date=end_date,
    )
    return Page(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.post("/", response_model=schemas.Income)
def create_income(
    *,
    db: Session = Depends(deps.get_db),
    income_in: IncomeCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new income for the current user.
    """
    income = crud_income.create_with_user(db=db, obj_in=income_in, user=current_user)
    return income


@router.put("/{id}", response_model=schemas.Income)
def update_income(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    income_in: IncomeUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update an income.
    """
    income = crud_income.get(db=db, id=id)
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    if income.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    income = crud_income.update(db=db, db_obj=income, obj_in=income_in)
    return income


@router.delete("/{id}", response_model=schemas.Income)
def delete_income(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete an income.
    """
    income = crud_income.get(db=db, id=id)
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    if income.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    income = crud_income.remove(db=db, id=id)
    return income


@router.patch("/{id}/assign", response_model=IncomeAssignResponse)
def assign_income(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    assign_in: IncomeAssign,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Assign income to wallet (and optionally category).
    """
    income = crud_income.get(db=db, id=id)
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    if income.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    income = crud_income.assign_income_to_wallet(db=db, income_id=id, wallet_id=assign_in.wallet_id, amount=assign_in.amount, category_id=assign_in.category_id)
    wallet = db.get(models.Wallet, assign_in.wallet_id)
    db.refresh(wallet)
    return IncomeAssignResponse(
        income=schemas.Income.model_validate(income),
        wallet=schemas.Wallet.model_validate(wallet)
    )
