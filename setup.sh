#!/bin/bash
# setup.sh — Configura el proyecto desde cero

echo "📦 Instalando dependencias..."
pip install -r requirements.txt

echo "🗄️  Inicializando Alembic para migraciones..."
alembic init alembic

echo "✅ Listo. Próximos pasos:"
echo ""
echo "1. Copia .env.example a .env y configura tu DATABASE_URL"
echo "2. Crea la base de datos en PostgreSQL:"
echo "   createdb expense_tracker"
echo ""
echo "3. Crea la primera migración:"
echo "   alembic revision --autogenerate -m 'initial'"
echo "   alembic upgrade head"
echo ""
echo "4. Levanta el servidor:"
echo "   uvicorn app.main:app --reload"
echo ""
echo "5. Abre la documentación interactiva:"
echo "   http://localhost:8000/docs"
