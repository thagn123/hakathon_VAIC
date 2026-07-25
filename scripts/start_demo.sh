#!/bin/bash
set -e

echo "========================================="
echo " SHB CORPORATE EXPERT WORKSPACE - DEMO "
echo "========================================="
echo ""

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating default .env with DEMO FALLBACK enabled..."
    echo "AGENTIC_LLM_ENABLED=false" > "$ENV_FILE"
else
    echo "Using existing .env"
fi

echo -e "\nResetting local Demo database state..."
python -c "import sqlite3; conn = sqlite3.connect('data/mock_database/enterprise_core.sqlite3'); conn.execute('DELETE FROM corporate_credit_requests'); conn.execute('DELETE FROM intake_sessions'); conn.execute('DELETE FROM cases'); conn.execute('DELETE FROM documents'); conn.commit(); print('Demo DB Reset.')"

echo -e "\nStarting FastAPI Server on http://localhost:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
