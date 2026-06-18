from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timezone
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.expense import Expense, Budget, Category
from app.schemas.expense import MonthlyReport, CategorySummary, AlertLevel
from app.services.alert_service import (
    calculate_spent_in_month,
    check_all_budget_alerts,
    get_alert_level,
)

router = APIRouter(prefix="/reports", tags=["Reportes"])


@router.get("/monthly", response_model=MonthlyReport)
def monthly_report(
    month: int = Query(default=None, ge=1, le=12, description="Mes (1-12)"),
    year: int = Query(default=None, description="Año"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reporte mensual completo.
    
    Por defecto usa el mes y año actual.
    
    Incluye:
    - Total gastado vs total presupuestado
    - Desglose por categoría con % de uso
    - Todas las alertas activas (categorías al 80%+)
    """
    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year

    # Obtener todas las categorías del usuario
    categories = db.query(Category).filter(
        Category.owner_id == current_user.id
    ).all()

    # Obtener todos los presupuestos del mes
    budgets_map = {}
    budgets = db.query(Budget).filter(
        Budget.owner_id == current_user.id,
        Budget.month == month,
        Budget.year == year,
    ).all()
    for b in budgets:
        budgets_map[b.category_id] = b

    # Calcular resumen por categoría
    category_summaries = []
    total_spent = 0.0
    total_budgeted = 0.0

    for cat in categories:
        spent = calculate_spent_in_month(db, current_user.id, cat.id, month, year)

        # Solo incluir categorías con gastos o presupuesto en este mes
        budget = budgets_map.get(cat.id)
        if spent == 0 and not budget:
            continue

        total_spent += spent

        budget_amount = None
        percentage = None
        alert_level = None

        if budget:
            budget_amount = budget.amount
            total_budgeted += budget_amount
            percentage = round((spent / budget_amount) * 100, 2) if budget_amount > 0 else 0
            alert_level = get_alert_level(percentage)

        # Contar número de gastos en la categoría este mes
        expense_count = db.query(func.count(Expense.id)).filter(
            Expense.owner_id == current_user.id,
            Expense.category_id == cat.id,
            extract("month", Expense.expense_date) == month,
            extract("year", Expense.expense_date) == year,
        ).scalar() or 0

        category_summaries.append(CategorySummary(
            category_id=cat.id,
            category_name=cat.name,
            category_color=cat.color,
            total_spent=spent,
            budget_amount=budget_amount,
            percentage_used=percentage,
            alert_level=alert_level,
            expense_count=expense_count,
        ))

    # Ordenar por gasto descendente
    category_summaries.sort(key=lambda x: x.total_spent, reverse=True)

    # Calcular porcentaje global
    overall_percentage = round(
        (total_spent / total_budgeted) * 100, 2
    ) if total_budgeted > 0 else 0.0

    # Obtener todas las alertas activas
    alerts = check_all_budget_alerts(db, current_user.id, month, year)

    return MonthlyReport(
        month=month,
        year=year,
        total_spent=round(total_spent, 2),
        total_budgeted=round(total_budgeted, 2),
        overall_percentage=overall_percentage,
        categories=category_summaries,
        alerts=alerts,
    )
