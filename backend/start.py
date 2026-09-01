"""
RECOVERX AI — Quickstart Launcher
Initializes DB, seeds synthetic data if needed, and starts uvicorn.
"""
import asyncio
import sys
import uvicorn
from app.config import get_settings
from app.database import init_db

if __name__ == "__main__":
    settings = get_settings()
    print("=" * 60)
    print(f"  {settings.app_name} — Autonomous Revenue Recovery OS")
    print(f"  LLM Provider : {settings.llm_provider}")
    print(f"  Event Bus    : {settings.event_bus}")
    print(f"  Database     : {settings.database_url}")
    print(f"  API Docs     : http://localhost:{settings.port}/api/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
