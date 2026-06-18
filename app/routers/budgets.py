from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.expense import Budget, Category
from app.schemas.expense import BudgetCreate, BudgetResponse

router = APIRouter(prefix="/budgets", tags=["Presupuestos"])


def budget_to_response(budget: Budget) -> BudgetResponse:
    """Convierte un Budget a BudgetResponse con category como string."""
    return BudgetResponse(
        id=budget.id,
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        category_id=budget.category_id,
        category=budget.category.name,  # el front espera string, no objeto
        created_at=budget.created_at,
    )


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = db.query(Category).filter(
        Category.id == data.category_id,
        Category.owner_id == current_user.id,
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    existing = db.query(Budget).filter(
        Budget.category_id == data.category_id,
        Budget.owner_id == current_user.id,
        Budget.month == data.month,
        Budget.year == data.year,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ya hay un presupuesto para '{category.name}' en {data.month}/{data.year}.",
        )

    budget = Budget(
        amount=data.amount,
        month=data.month,
        year=data.year,
        category_id=data.category_id,
        owner_id=current_user.id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget_to_response(budget)


@router.get("/", response_model=List[BudgetResponse])
def list_budgets(
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Budget).filter(Budget.owner_id == current_user.id)
    if month:
        query = query.filter(Budget.month == month)
    if year:
        query = query.filter(Budget.year == year)
    return [budget_to_response(b) for b in query.all()]


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.owner_id == current_user.id,
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    budget.amount = data.amount
    db.commit()
    db.refresh(budget)
    return budget_to_response(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.owner_id == current_user.id,
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    db.delete(budget)
    db.commit()
