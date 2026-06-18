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
    category: str        # nombre de la categoría (lo que el front espera)
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Alert ───────────────────────────────────────────────────────────────────

class AlertLevel(str, Enum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"


class BudgetAlert(BaseModel):
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
    expense_date: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class ExpenseItem(BaseModel):
    """Gasto en el formato que el front espera dentro del reporte."""
    id: int
    description: Optional[str]
    amount: float
    date: datetime      # el front usa 'date', no 'expense_date'
    category: str       # nombre de la categoría

    model_config = {"from_attributes": True}


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
    expense: ExpenseResponse
    alerts: List[BudgetAlert]
    # budget_status para compatibilidad con el front
    budget_status: Optional[dict] = None


# ─── Reports — estructura exacta que espera el front ──────────────────────────

class CategorySummaryFront(BaseModel):
    """Resumen de categoría en el formato exacto del dashboard del front."""
    category: str               # nombre (el front usa 'category', no 'category_name')
    category_id: int
    category_color: str
    budget: float               # el front usa 'budget'
    spent: float                # el front usa 'spent'
    remaining: float            # el front usa 'remaining'
    percentage: float           # el front usa 'percentage'
    status: str                 # 'OK', 'ADVERTENCIA', 'CRÍTICO'
    expense_count: int
    expenses: List[ExpenseItem]  # el front necesita la lista de gastos por categoría


class ReportSummary(BaseModel):
    """Resumen global — el front accede como report.summary.xxx"""
    total_budget: float
    total_spent: float
    total_remaining: float
    overall_percentage: float


class MonthlyReport(BaseModel):
    """Reporte mensual en el formato exacto que espera el front."""
    month: int
    year: int
    summary: ReportSummary      # el front usa report.summary.total_budget etc.
    categories: List[CategorySummaryFront]
    alerts: List[BudgetAlert]


# ─── Schemas legacy (para endpoints no relacionados con reportes) ──────────────

class CategorySummary(BaseModel):
    category_id: int
    category_name: str
    category_color: str
    total_spent: float
    budget_amount: Optional[float]
    percentage_used: Optional[float]
    alert_level: Optional[AlertLevel]
    expense_count: int
