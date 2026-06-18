from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.expense import Budget, Category
from app.schemas.expense import BudgetCreate, BudgetResponse
from app.services.alert_service import calculate_spent_in_month

router = APIRouter(prefix="/budgets", tags=["Presupuestos"])


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Define un presupuesto mensual para una categoría.
    
    Solo puede existir un presupuesto por categoría/mes/año.
    Si ya existe, usar PUT para actualizarlo.
    """
    # Verificar que la categoría pertenece al usuario
    category = db.query(Category).filter(
        Category.id == data.category_id,
        Category.owner_id == current_user.id,
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    # Verificar que no existe presupuesto para esa categoría/mes/año
    existing = db.query(Budget).filter(
        Budget.category_id == data.category_id,
        Budget.owner_id == current_user.id,
        Budget.month == data.month,
        Budget.year == data.year,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya hay un presupuesto para '{category.name}' en {data.month}/{data.year}. Usa PUT para actualizarlo.",
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
    return budget


@router.get("/", response_model=List[BudgetResponse])
def list_budgets(
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista presupuestos del usuario, con filtro opcional por mes/año."""
    query = db.query(Budget).filter(Budget.owner_id == current_user.id)
    if month:
        query = query.filter(Budget.month == month)
    if year:
        query = query.filter(Budget.year == year)
    return query.all()


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza el monto de un presupuesto existente."""
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.owner_id == current_user.id,
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    budget.amount = data.amount
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina un presupuesto."""
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.owner_id == current_user.id,
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    db.delete(budget)
    db.commit()
