from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timezone
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.expense import Expense, Budget, Category
from app.schemas.expense import (
    MonthlyReport, CategorySummaryFront, ReportSummary,
    BudgetAlert, AlertLevel, ExpenseItem
)
from app.services.alert_service import calculate_spent_in_month, get_alert_level

router = APIRouter(prefix="/reports", tags=["Reportes"])


def alert_level_to_status(level: AlertLevel) -> str:
    """Convierte el nivel de alerta al texto que espera el front."""
    if level == AlertLevel.EXCEEDED:
        return "CRÍTICO"
    elif level == AlertLevel.WARNING:
        return "ADVERTENCIA"
    return "OK"


@router.get("/monthly", response_model=MonthlyReport)
def monthly_report(
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reporte mensual en el formato exacto que espera el frontend.
    """
    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year

    categories = db.query(Category).filter(Category.owner_id == current_user.id).all()

    # Mapa de presupuestos del mes
    budgets_map = {}
    for b in db.query(Budget).filter(
        Budget.owner_id == current_user.id,
        Budget.month == month,
        Budget.year == year,
    ).all():
        budgets_map[b.category_id] = b

    category_summaries = []
    total_spent = 0.0
    total_budget = 0.0

    for cat in categories:
        spent = calculate_spent_in_month(db, current_user.id, cat.id, month, year)
        budget = budgets_map.get(cat.id)

        if spent == 0 and not budget:
            continue

        budget_amount = budget.amount if budget else 0.0
        total_spent += spent
        total_budget += budget_amount

        percentage = round((spent / budget_amount) * 100, 2) if budget_amount > 0 else 0.0
        alert_level = get_alert_level(percentage)
        status = alert_level_to_status(alert_level)
        remaining = max(budget_amount - spent, 0)

        # Obtener gastos de esta categoría en el mes
        expenses_raw = db.query(Expense).filter(
            Expense.owner_id == current_user.id,
            Expense.category_id == cat.id,
            extract("month", Expense.expense_date) == month,
            extract("year", Expense.expense_date) == year,
        ).order_by(Expense.expense_date.desc()).all()

        expenses = [
            ExpenseItem(
                id=e.id,
                description=e.description,
                amount=e.amount,
                date=e.expense_date,
                category=cat.name,
            )
            for e in expenses_raw
        ]

        category_summaries.append(CategorySummaryFront(
            category=cat.name,
            category_id=cat.id,
            category_color=cat.color,
            budget=budget_amount,
            spent=round(spent, 2),
            remaining=round(remaining, 2),
            percentage=percentage,
            status=status,
            expense_count=len(expenses),
            expenses=expenses,
        ))

    category_summaries.sort(key=lambda x: x.spent, reverse=True)

    overall_percentage = round((total_spent / total_budget) * 100, 2) if total_budget > 0 else 0.0
    total_remaining = max(total_budget - total_spent, 0)

    # Alertas — categorías al 80%+
    alerts = []
    for cat_summary in category_summaries:
        if cat_summary.status in ("ADVERTENCIA", "CRÍTICO"):
            level = AlertLevel.EXCEEDED if cat_summary.status == "CRÍTICO" else AlertLevel.WARNING
            alerts.append(BudgetAlert(
                category_id=cat_summary.category_id,
                category_name=cat_summary.category,
                budget_amount=cat_summary.budget,
                spent_amount=cat_summary.spent,
                percentage_used=cat_summary.percentage,
                alert_level=level,
                message=f"{'🚨' if level == AlertLevel.EXCEEDED else '⚠️'} {cat_summary.category}: {cat_summary.percentage}% del presupuesto usado.",
            ))

    return MonthlyReport(
        month=month,
        year=year,
        summary=ReportSummary(
            total_budget=round(total_budget, 2),
            total_spent=round(total_spent, 2),
            total_remaining=round(total_remaining, 2),
            overall_percentage=overall_percentage,
        ),
        categories=category_summaries,
        alerts=alerts,
    )
