from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    color = Column(String, default="#6366f1")  # Para UIs con colores por categoría
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Cada usuario tiene sus propias categorías (mismo nombre permitido entre usuarios)
    __table_args__ = (UniqueConstraint("name", "owner_id", name="uq_category_user"),)

    owner = relationship("User", back_populates="categories")
    expenses = relationship("Expense", back_populates="category")
    budgets = relationship("Budget", back_populates="category")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Fecha del gasto (puede ser diferente a created_at para importar gastos pasados)
    expense_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)  # Límite del presupuesto
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Un presupuesto por categoría por mes por usuario
    __table_args__ = (
        UniqueConstraint("category_id", "owner_id", "month", "year", name="uq_budget_category_month"),
    )

    owner = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")
