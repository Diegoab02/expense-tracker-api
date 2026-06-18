from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import auth, categories, budgets, expenses, reports

# Crea todas las tablas al iniciar (en producción usa Alembic migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="""
API para tracking de gastos con alertas de presupuesto.

## Flujo de uso

1. **Registro/Login** → obtienes un JWT
2. **Crea categorías** → Comida, Transporte, Entretenimiento...
3. **Define presupuestos** → cuánto quieres gastar por categoría al mes
4. **Registra gastos** → la respuesta te avisa si te estás pasando
5. **Consulta reportes** → resumen mensual con todas las alertas

## Autenticación

Todos los endpoints (excepto /auth/register y /auth/login) requieren:
```
Authorization: Bearer <tu-jwt-token>
```
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permite requests desde cualquier origen (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(expenses.router)
app.include_router(reports.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Bienvenido a {settings.APP_NAME}",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Root"])
def health():
    return {"status": "ok"}
