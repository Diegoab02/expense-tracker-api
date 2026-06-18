from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import extract
from datetime import datetime, timezone
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.expense import Expense, Category, Budget
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseWithAlerts
from app.services.alert_service import check_budget_alerts, get_alert_level, calculate_spent_in_month
from app.schemas.expense import AlertLevel

router = APIRouter(prefix="/expenses", tags=["Gastos"])


@router.post("/", response_model=ExpenseWithAlerts, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: dict,  # usamos dict para aceptar tanto budget_id como category_id
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registra un nuevo gasto.
    Acepta tanto 'category_id' (API directa) como 'budget_id' (desde el front).
    """
    amount = data.get("amount")
    description = data.get("description")
    expense_date = data.get("expense_date")

    # El front manda budget_id, la API directa manda category_id
    budget_id = data.get("budget_id")
    category_id = data.get("category_id")

    if budget_id:
        # Buscar la categoría a través del presupuesto
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.owner_id == current_user.id,
        ).first()
        if not budget:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        category_id = budget.category_id
    
    if not category_id:
        raise HTTPException(status_code=422, detail="Se requiere category_id o budget_id")

    category = db.query(Category).filter(
        Category.id == category_id,
        Category.owner_id == current_user.id,
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    if not amount or amount <= 0:
        raise HTTPException(status_code=422, detail="El monto debe ser mayor a 0")

    if expense_date and isinstance(expense_date, str):
        expense_date = datetime.fromisoformat(expense_date.replace("Z", "+00:00"))

    expense_date = expense_date or datetime.now(timezone.utc)

    expense = Expense(
        amount=amount,
        description=description,
        category_id=category_id,
        owner_id=current_user.id,
        expense_date=expense_date,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Verificar alertas
    alert = check_budget_alerts(
        db=db,
        user_id=current_user.id,
        category_id=category_id,
        month=expense_date.month,
        year=expense_date.year,
    )

    # budget_status en el formato que espera el front
    budget_status = None
    if alert:
        budget_status = {
            "level": "CRÍTICO" if alert.alert_level == AlertLevel.EXCEEDED else "ADVERTENCIA",
            "message": alert.message,
            "percentage": alert.percentage_used,
        }
    else:
        spent = calculate_spent_in_month(db, current_user.id, category_id, expense_date.month, expense_date.year)
        budget_obj = db.query(Budget).filter(
            Budget.owner_id == current_user.id,
            Budget.category_id == category_id,
            Budget.month == expense_date.month,
            Budget.year == expense_date.year,
        ).first()
        if budget_obj:
            pct = round((spent / budget_obj.amount) * 100, 2)
            budget_status = {"level": "OK", "message": f"✅ {category.name}: {pct}% usado.", "percentage": pct}

    return ExpenseWithAlerts(
        expense=expense,
        alerts=[alert] if alert else [],
        budget_status=budget_status,
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
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.owner_id == current_user.id,
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(expense)
    db.commit()
