@echo off
cd /d %~dp0\backend
set DATABASE_URL=sqlite:///./studio.db
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning
