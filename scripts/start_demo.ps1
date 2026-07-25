$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " SHB CORPORATE EXPERT WORKSPACE - DEMO " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Ensure .env has AGENTIC_LLM_ENABLED=false for demo fallback by default
$envFile = ".env"
if (!(Test-Path $envFile)) {
    Write-Host "Creating default .env with DEMO FALLBACK enabled..."
    Set-Content $envFile "AGENTIC_LLM_ENABLED=false"
} else {
    Write-Host "Using existing .env"
}

Write-Host "Resetting local Demo database state..." -ForegroundColor Yellow
# We can just start the server, the frontend will reset via /api/v2/demo/reset when "Reset" is clicked, 
# but if we want to reset via script we can run a python command.
python -c "import sqlite3; conn = sqlite3.connect('data/mock_database/enterprise_core.sqlite3'); conn.execute('DELETE FROM corporate_credit_requests'); conn.execute('DELETE FROM intake_sessions'); conn.execute('DELETE FROM cases'); conn.execute('DELETE FROM documents'); conn.commit(); print('Demo DB Reset.')"

Write-Host "Starting FastAPI Server on http://localhost:8000" -ForegroundColor Green
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
