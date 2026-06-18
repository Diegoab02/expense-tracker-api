from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.expense import Category
from app.schemas.expense import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categorías"])


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una nueva categoría para el usuario autenticado."""
    # Verificar que no existe ya esa categoría para este usuario
    existing = db.query(Category).filter(
        Category.name == data.name,
        Category.owner_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya tienes una categoría llamada '{data.name}'",
        )

    category = Category(
        name=data.name,
        description=data.description,
        color=data.color or "#6366f1",
        owner_id=current_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/", response_model=List[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todas las categorías del usuario."""
    return db.query(Category).filter(Category.owner_id == current_user.id).all()


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene una categoría por ID."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.owner_id == current_user.id,
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza nombre, descripción o color de una categoría."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.owner_id == current_user.id,
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    category.name = data.name
    category.description = data.description
    if data.color:
        category.color = data.color
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina una categoría (y en cascada sus gastos y presupuestos)."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.owner_id == current_user.id,
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    db.delete(category)
    db.commit()
