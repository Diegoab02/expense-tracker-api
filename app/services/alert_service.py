"""
Servicio de alertas — el corazón de la lógica de negocio.

Calcula el estado del presupuesto de una categoría y genera alertas
cuando el gasto llega al 80% o 100% del límite.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime
from typing import List, Optional

from app.models.expense import Expense, Budget, Category
from app.schemas.expense import BudgetAlert, AlertLevel


def calculate_spent_in_month(
    db: Session,
    user_id: int,
    category_id: int,
    month: int,
    year: int,
) -> float:
    """
    Suma todos los gastos de un usuario en una categoría durante un mes.
    
    Usa extract() de SQLAlchemy para filtrar por mes y año directamente en SQL,
    que es más eficiente que traer todos los registros a Python.
    """
    result = db.query(func.sum(Expense.amount)).filter(
        Expense.owner_id == user_id,
        Expense.category_id == category_id,
        extract("month", Expense.expense_date) == month,
        extract("year", Expense.expense_date) == year,
    ).scalar()

    return result or 0.0  # scalar() devuelve None si no hay gastos


def get_alert_level(percentage: float) -> AlertLevel:
    """
    Determina el nivel de alerta según el porcentaje usado del presupuesto.
    
    < 80%  → OK (sin alerta)
    80-99% → WARNING (llegaste al 80%)
    100%+  → EXCEEDED (superaste el presupuesto)
    """
    if percentage >= 100:
        return AlertLevel.EXCEEDED
    elif percentage >= 80:
        return AlertLevel.WARNING
    return AlertLevel.OK


def build_alert_message(level: AlertLevel, category_name: str, percentage: float) -> str:
    """Genera el mensaje de alerta según el nivel."""
    if level == AlertLevel.EXCEEDED:
        return (
            f"🚨 ¡Presupuesto superado en '{category_name}'! "
            f"Llevas el {percentage:.1f}% del límite mensual."
        )
    elif level == AlertLevel.WARNING:
        return (
            f"⚠️ Alerta en '{category_name}': llevas el {percentage:.1f}% del presupuesto. "
            f"Estás cerca del límite mensual."
        )
    return f"✅ '{category_name}' va bien ({percentage:.1f}% del presupuesto usado)."


def check_budget_alerts(
    db: Session,
    user_id: int,
    category_id: int,
    month: int,
    year: int,
) -> Optional[BudgetAlert]:
    """
    Verifica si hay alertas para una categoría en un mes dado.
    
    Retorna un BudgetAlert si el gasto supera el 80%, None si todo está bien.
    Así el endpoint solo incluye alertas relevantes en la respuesta.
    """
    # Buscar presupuesto para esta categoría/mes/año
    budget = db.query(Budget).filter(
        Budget.owner_id == user_id,
        Budget.category_id == category_id,
        Budget.month == month,
        Budget.year == year,
    ).first()

    # Sin presupuesto definido → no hay alertas
    if not budget:
        return None

    # Calcular gasto actual
    spent = calculate_spent_in_month(db, user_id, category_id, month, year)
    percentage = (spent / budget.amount) * 100

    alert_level = get_alert_level(percentage)

    # Solo retornar alerta si supera el 80%
    if alert_level == AlertLevel.OK:
        return None

    category = db.query(Category).filter(Category.id == category_id).first()

    return BudgetAlert(
        category_id=category_id,
        category_name=category.name,
        budget_amount=budget.amount,
        spent_amount=spent,
        percentage_used=round(percentage, 2),
        alert_level=alert_level,
        message=build_alert_message(alert_level, category.name, percentage),
    )


def check_all_budget_alerts(
    db: Session,
    user_id: int,
    month: int,
    year: int,
) -> List[BudgetAlert]:
    """
    Verifica alertas para TODAS las categorías del usuario en un mes.
    Usado en el reporte mensual.
    """
    budgets = db.query(Budget).filter(
        Budget.owner_id == user_id,
        Budget.month == month,
        Budget.year == year,
    ).all()

    alerts = []
    for budget in budgets:
        alert = check_budget_alerts(db, user_id, budget.category_id, month, year)
        if alert:
            alerts.append(alert)

    return alerts
