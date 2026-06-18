from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


# ─── Category ────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#6366f1"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Budget ───────────────────────────────────────────────────────────────────

class BudgetCreate(BaseModel):
    amount: float
    month: int
    year: int
    category_id: int

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El presupuesto debe ser mayor a 0")
        return v

    @field_validator("month")
    @classmethod
    def valid_month(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("El mes debe estar entre 1 y 12")
        return v


class BudgetResponse(BaseModel):
    id: int
    amount: float
    month: int
    year: int
    category_id: int
    category: CategoryResponse
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Alert ───────────────────────────────────────────────────────────────────

class AlertLevel(str, Enum):
    OK = "ok"                     # < 80%
    WARNING = "warning"           # 80% - 99%
    EXCEEDED = "exceeded"         # 100%+


class BudgetAlert(BaseModel):
    """Alerta generada cuando se registra un gasto."""
    category_id: int
    category_name: str
    budget_amount: float
    spent_amount: float
    percentage_used: float
    alert_level: AlertLevel
    message: str


# ─── Expense ──────────────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    amount: float
    description: Optional[str] = None
    category_id: int
    expense_date: Optional[datetime] = None  # Si no se pasa, se usa now()

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class ExpenseResponse(BaseModel):
    id: int
    amount: float
    description: Optional[str]
    category_id: int
    category: CategoryResponse
    expense_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseWithAlerts(BaseModel):
    """Respuesta al crear un gasto — incluye el gasto + alertas de presupuesto."""
    expense: ExpenseResponse
    alerts: List[BudgetAlert]  # Lista vacía si no hay alertas


# ─── Reports ──────────────────────────────────────────────────────────────────

class CategorySummary(BaseModel):
    category_id: int
    category_name: str
    category_color: str
    total_spent: float
    budget_amount: Optional[float]  # None si no tiene presupuesto definido
    percentage_used: Optional[float]
    alert_level: Optional[AlertLevel]
    expense_count: int


class MonthlyReport(BaseModel):
    month: int
    year: int
    total_spent: float
    total_budgeted: float
    overall_percentage: float
    categories: List[CategorySummary]
    alerts: List[BudgetAlert]  # Categorías que están al 80%+ del presupuesto
