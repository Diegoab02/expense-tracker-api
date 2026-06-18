"""
Tests de integración para la API.
Usan SQLite en memoria para no necesitar PostgreSQL real en CI.
Ejecutar: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Registra usuario y retorna headers — simula exactamente el flujo del front."""
    # Registro: el front manda solo email + password (sin full_name)
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
    })
    # Login: el front manda form-urlencoded con campo 'username'
    response = client.post("/auth/login", data={
        "username": "test@example.com",
        "password": "password123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Auth tests ───────────────────────────────────────────────────────────────

def test_register_without_full_name(client):
    """El front solo manda email + password, full_name es opcional."""
    response = client.post("/auth/register", json={
        "email": "nuevo@example.com",
        "password": "segura123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "nuevo@example.com"
    assert data["full_name"] == "nuevo"  # generado del email
    assert "hashed_password" not in data


def test_register_with_full_name(client):
    """También acepta full_name si se manda."""
    response = client.post("/auth/register", json={
        "email": "diego@example.com",
        "full_name": "Diego",
        "password": "segura123",
    })
    assert response.status_code == 201
    assert response.json()["full_name"] == "Diego"


def test_register_duplicate_email(client):
    payload = {"email": "dup@test.com", "password": "pass1234"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400


def test_login_form_urlencoded(client):
    """Login usa form-urlencoded con campo 'username' — igual que el front."""
    client.post("/auth/register", json={"email": "user@test.com", "password": "pass1234"})
    response = client.post("/auth/login", data={
        "username": "user@test.com",
        "password": "pass1234",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "user@test.com", "password": "pass1234"})
    response = client.post("/auth/login", data={
        "username": "user@test.com",
        "password": "wrong",
    })
    assert response.status_code == 401


def test_protected_endpoint_without_token(client):
    response = client.get("/categories/")
    assert response.status_code == 401


# ─── Category tests ───────────────────────────────────────────────────────────

def test_create_category(client, auth_headers):
    response = client.post("/categories/", json={
        "name": "Comida", "color": "#ff5733"
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Comida"


def test_duplicate_category(client, auth_headers):
    client.post("/categories/", json={"name": "Comida"}, headers=auth_headers)
    response = client.post("/categories/", json={"name": "Comida"}, headers=auth_headers)
    assert response.status_code == 400


# ─── Expense + Alert tests ────────────────────────────────────────────────────

def test_expense_no_budget_no_alerts(client, auth_headers):
    cat = client.post("/categories/", json={"name": "Test"}, headers=auth_headers).json()
    response = client.post("/expenses/", json={
        "amount": 100,
        "category_id": cat["id"],
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["alerts"] == []


def test_expense_triggers_warning_alert(client, auth_headers):
    cat = client.post("/categories/", json={"name": "Ropa"}, headers=auth_headers).json()
    client.post("/budgets/", json={
        "amount": 100, "month": 6, "year": 2025, "category_id": cat["id"],
    }, headers=auth_headers)
    response = client.post("/expenses/", json={
        "amount": 85,
        "category_id": cat["id"],
        "expense_date": "2025-06-15T10:00:00Z",
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["alert_level"] == "warning"
    assert data["alerts"][0]["percentage_used"] == 85.0


def test_expense_triggers_exceeded_alert(client, auth_headers):
    cat = client.post("/categories/", json={"name": "Ocio"}, headers=auth_headers).json()
    client.post("/budgets/", json={
        "amount": 100, "month": 6, "year": 2025, "category_id": cat["id"],
    }, headers=auth_headers)
    response = client.post("/expenses/", json={
        "amount": 110,
        "category_id": cat["id"],
        "expense_date": "2025-06-15T10:00:00Z",
    }, headers=auth_headers)
    data = response.json()
    assert data["alerts"][0]["alert_level"] == "exceeded"
    assert "🚨" in data["alerts"][0]["message"]


# ─── Report tests ─────────────────────────────────────────────────────────────

def test_monthly_report(client, auth_headers):
    cat = client.post("/categories/", json={"name": "Tech"}, headers=auth_headers).json()
    client.post("/budgets/", json={
        "amount": 200, "month": 6, "year": 2025, "category_id": cat["id"],
    }, headers=auth_headers)
    client.post("/expenses/", json={
        "amount": 180,
        "category_id": cat["id"],
        "expense_date": "2025-06-10T10:00:00Z",
    }, headers=auth_headers)
    response = client.get("/reports/monthly?month=6&year=2025", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_spent"] == 180.0
    assert data["total_budgeted"] == 200.0
    assert data["overall_percentage"] == 90.0
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["alert_level"] == "warning"
