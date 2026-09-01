"""
RECOVERX AI — FastAPI Application Entry Point
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("recoverx")

settings = get_settings()

app = FastAPI(
    title="RECOVERX AI",
    description="Autonomous Revenue Recovery Intelligence System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info(f"Starting {settings.app_name} [{settings.app_env}]")
    await init_db()

    # Seed with synthetic data if DB is empty
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.customer import Customer

    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count(Customer.id)))).scalar()
        if count == 0:
            logger.info("Seeding synthetic dataset (first run)...")
            await _seed_synthetic_data(db)

    logger.info(f"LLM Provider: {__import__('app.llm', fromlist=['get_llm_provider']).get_llm_provider().provider_name}")
    logger.info(f"Event Bus: {settings.event_bus}")
    logger.info(f"Database: {settings.database_url[:40]}...")


async def _seed_synthetic_data(db) -> None:
    """Seed the database with synthetic customers and events."""
    from app.simulation.generator import generate_full_dataset
    from app.models.customer import Customer
    from app.models.revenue_event import RevenueEvent
    from datetime import datetime, timezone
    import json

    data = generate_full_dataset(n_customers=200, n_events=1000, seed=settings.simulation_seed)

    # Insert customers
    customer_map = {}
    for c_data in data["customers"]:
        customer = Customer(
            external_id=c_data["external_id"],
            name=c_data["name"],
            email=c_data.get("email", ""),
            phone=c_data.get("phone", ""),
            tier=c_data["tier"],
            preferred_payment_method=c_data.get("preferred_payment_method"),
            preferred_channel=c_data.get("preferred_channel", "EMAIL"),
            best_contact_time=c_data.get("best_contact_time", "10:00-12:00"),
            historical_recovery_rate=c_data.get("historical_recovery_rate", 0.5),
            total_successful_payments=c_data.get("total_successful_payments", 0),
            total_failed_payments=c_data.get("total_failed_payments", 0),
            lifetime_value=c_data.get("lifetime_value", 0),
            fatigue_score=c_data.get("fatigue_score", 0),
            contact_count_7d=c_data.get("contact_count_7d", 0),
            no_response_streak=c_data.get("no_response_streak", 0),
            opt_out=c_data.get("opt_out", False),
            payment_history_json=json.dumps(c_data.get("payment_history", [])),
            contact_history_json=json.dumps(c_data.get("contact_history", [])),
        )
        db.add(customer)
        customer_map[c_data["external_id"]] = customer

    await db.flush()

    # Insert events
    for e_data in data["events"]:
        cust_ext_id = e_data.get("customer_external_id") or e_data.get("customer_id")
        cust = customer_map.get(cust_ext_id)
        if not cust:
            continue

        event = RevenueEvent(
            external_id=e_data["external_id"],
            event_type=e_data["event_type"],
            amount=e_data["amount"],
            currency=e_data.get("currency", "INR"),
            customer_id=cust.id,
            payment_method=e_data.get("payment_method"),
            failure_reason=e_data.get("failure_reason"),
            gateway=e_data.get("gateway"),
            gateway_error_code=e_data.get("gateway_error_code"),
            status="PENDING",
            metadata_json=json.dumps(e_data.get("metadata", {})),
            event_time=datetime.fromisoformat(
                e_data["event_time"].replace("Z", "+00:00")
            ) if e_data.get("event_time") else datetime.now(timezone.utc),
        )
        db.add(event)

    await db.commit()
    logger.info(f"Seeded {len(data['customers'])} customers and {len(data['events'])} events.")


@app.on_event("shutdown")
async def shutdown():
    from app.eventbus import get_event_bus
    await get_event_bus().close()
    logger.info("RECOVERX AI shutdown complete.")


# ── Register routes ────────────────────────────────────────────────────────────
from app.api.dashboard import router as dashboard_router
from app.api.cases import router as cases_router
from app.api.simulation import router as simulation_router
from app.api.routes import agents_router, audit_router, human_review_router, ws_router

app.include_router(dashboard_router)
app.include_router(cases_router)
app.include_router(simulation_router)
app.include_router(agents_router)
app.include_router(audit_router)
app.include_router(human_review_router)
app.include_router(ws_router)


@app.get("/api/health")
async def health():
    from app.llm import get_llm_provider
    return {
        "status": "healthy",
        "service": settings.app_name,
        "llm_provider": get_llm_provider().provider_name,
        "event_bus": settings.event_bus,
        "database": "sqlite" if settings.is_sqlite else "postgresql",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
