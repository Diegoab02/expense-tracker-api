from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import extract
from datetime import datetime, timezone
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.expense import Expense, Category
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseWithAlerts
from app.services.alert_service import check_budget_alerts

router = APIRouter(prefix="/expenses", tags=["Gastos"])


@router.post("/", response_model=ExpenseWithAlerts, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registra un nuevo gasto.
    
    Respuesta incluye el gasto + alertas de presupuesto:
    - Si el gasto lleva la categoría al 80-99% → alerta WARNING
    - Si supera el 100% → alerta EXCEEDED
    - Si todo está bien → alerts: []
    
    Las alertas solo aparecen si tienes un presupuesto definido para esa categoría.
    """
    # Verificar que la categoría existe y pertenece al usuario
    category = db.query(Category).filter(
        Category.id == data.category_id,
        Category.owner_id == current_user.id,
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    # Usar fecha del gasto o now() si no se especifica
    expense_date = data.expense_date or datetime.now(timezone.utc)

    expense = Expense(
        amount=data.amount,
        description=data.description,
        category_id=data.category_id,
        owner_id=current_user.id,
        expense_date=expense_date,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Verificar alertas DESPUÉS de guardar el gasto
    # (para que el nuevo gasto ya esté incluido en el cálculo)
    alert = check_budget_alerts(
        db=db,
        user_id=current_user.id,
        category_id=data.category_id,
        month=expense_date.month,
        year=expense_date.year,
    )

    return ExpenseWithAlerts(
        expense=expense,
        alerts=[alert] if alert else [],
    )


@router.get("/", response_model=List[ExpenseResponse])
def list_expenses(
    month: Optional[int] = None,
    year: Optional[int] = None,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista gastos del usuario.
    
    Filtros opcionales:
    - month, year: filtra por periodo
    - category_id: filtra por categoría
    - skip, limit: paginación
    """
    query = db.query(Expense).filter(Expense.owner_id == current_user.id)

    if month:
        query = query.filter(extract("month", Expense.expense_date) == month)
    if year:
        query = query.filter(extract("year", Expense.expense_date) == year)
    if category_id:
        query = query.filter(Expense.category_id == category_id)

    return query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene un gasto por ID."""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.owner_id == current_user.id,
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina un gasto."""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.owner_id == current_user.id,
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(expense)
    db.commit()
