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

$py = ".\.venv\Scripts\python.exe"

Write-Host "Resetting local Demo database state..." -ForegroundColor Yellow
& $py -c "import sqlite3; conn = sqlite3.connect('shb_corporate.db'); [conn.execute(f'DROP TABLE IF EXISTS {t}') for t in ('intake_documents', 'intake_processing_jobs', 'intake_sessions', 'cases', 'audit_events')]; conn.commit(); print('Demo DB Reset.')"

Write-Host "Starting FastAPI Server on http://localhost:8000" -ForegroundColor Green
& $py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
