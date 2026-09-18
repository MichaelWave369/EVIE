Set-StrictMode -Version Latest
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 18791
