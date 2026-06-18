# 💸 Expense Tracker API

API REST para tracking de gastos personales con alertas automáticas de presupuesto.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy · JWT · bcrypt · Pydantic v2

---

## ✨ Features

- **Multi-usuario** con registro, login y JWT
- **Categorías** personalizadas por usuario
- **Presupuestos mensuales** por categoría
- **Alertas automáticas** en la respuesta al registrar un gasto:
  - ⚠️ `WARNING` al llegar al 80% del presupuesto
  - 🚨 `EXCEEDED` al superar el 100%
- **Reporte mensual** con desglose por categoría y todas las alertas activas

---

## 🚀 Inicio rápido

### Opción 1 — Docker (recomendado)

```bash
docker-compose up
```

La API queda en `http://localhost:8000`

### Opción 2 — Local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu DATABASE_URL

# 3. Crear la base de datos
createdb expense_tracker

# 4. Levantar
uvicorn app.main:app --reload
```

---

## 📋 Endpoints

### Auth
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/register` | Registro |
| POST | `/auth/login` | Login → retorna JWT |
| GET | `/auth/me` | Perfil del usuario actual |

### Categorías
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/categories/` | Crear categoría |
| GET | `/categories/` | Listar categorías |
| PUT | `/categories/{id}` | Actualizar |
| DELETE | `/categories/{id}` | Eliminar |

### Presupuestos
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/budgets/` | Crear presupuesto mensual |
| GET | `/budgets/?month=6&year=2025` | Listar presupuestos |
| PUT | `/budgets/{id}` | Actualizar monto |
| DELETE | `/budgets/{id}` | Eliminar |

### Gastos
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/expenses/` | Registrar gasto (incluye alertas) |
| GET | `/expenses/?month=6&year=2025` | Listar gastos |
| GET | `/expenses/{id}` | Obtener gasto |
| DELETE | `/expenses/{id}` | Eliminar |

### Reportes
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/reports/monthly?month=6&year=2025` | Reporte mensual completo |

---

## 🔐 Autenticación

Todos los endpoints (excepto `/auth/register` y `/auth/login`) requieren el token en el header:

```
Authorization: Bearer <tu-token>
```

### Flujo completo

```bash
# 1. Registrarse
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "yo@mail.com", "full_name": "Mi Nombre", "password": "segura123"}'

# 2. Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "yo@mail.com", "password": "segura123"}' | jq -r .access_token)

# 3. Crear categoría
curl -X POST http://localhost:8000/categories/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Comida", "color": "#22c55e"}'

# 4. Crear presupuesto ($500 para Comida en junio 2025)
curl -X POST http://localhost:8000/budgets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 500, "month": 6, "year": 2025, "category_id": 1}'

# 5. Registrar gasto (gasto de $420 = 84% del presupuesto)
curl -X POST http://localhost:8000/expenses/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 420, "description": "Mercado", "category_id": 1}'
```

### Respuesta al registrar el gasto anterior:

```json
{
  "expense": {
    "id": 1,
    "amount": 420.0,
    "description": "Mercado",
    "category": { "id": 1, "name": "Comida", "color": "#22c55e" },
    "expense_date": "2025-06-10T15:30:00Z"
  },
  "alerts": [
    {
      "category_name": "Comida",
      "budget_amount": 500.0,
      "spent_amount": 420.0,
      "percentage_used": 84.0,
      "alert_level": "warning",
      "message": "⚠️ Alerta en 'Comida': llevas el 84.0% del presupuesto. Estás cerca del límite mensual."
    }
  ]
}
```

---

## 🧪 Tests

```bash
pytest tests/ -v
```

---

## 📁 Estructura

```
expense-tracker-api/
├── app/
│   ├── core/
│   │   ├── config.py      # Variables de entorno con Pydantic Settings
│   │   ├── database.py    # SQLAlchemy engine + session
│   │   └── security.py    # JWT + bcrypt + dependency get_current_user
│   ├── models/
│   │   ├── user.py        # Modelo User con relaciones
│   │   └── expense.py     # Modelos Category, Expense, Budget
│   ├── schemas/
│   │   ├── user.py        # Schemas Pydantic para auth
│   │   └── expense.py     # Schemas para gastos, alertas, reportes
│   ├── routers/
│   │   ├── auth.py        # /auth/register, /auth/login, /auth/me
│   │   ├── categories.py  # CRUD categorías
│   │   ├── budgets.py     # CRUD presupuestos
│   │   ├── expenses.py    # CRUD gastos + trigger alertas
│   │   └── reports.py     # Reporte mensual
│   ├── services/
│   │   └── alert_service.py  # Lógica de negocio: cálculo y alertas
│   └── main.py            # App FastAPI + middleware
├── tests/
│   └── test_api.py        # Tests de integración completos
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 💡 Lo que aprendiste construyendo esto

| Concepto | Dónde está |
|----------|-----------|
| JWT + bcrypt | `app/core/security.py` |
| Dependency Injection | `Depends(get_current_user)` en todos los routers |
| Relaciones entre tablas | `models/user.py` + `models/expense.py` |
| Lógica de negocio | `services/alert_service.py` |
| Queries con agregados | `func.sum()`, `extract()` en alert_service y reports |
| Constraints únicos | `UniqueConstraint` en los modelos |
| Tests de integración | `tests/test_api.py` con SQLite en memoria |
