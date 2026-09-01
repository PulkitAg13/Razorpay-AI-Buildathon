"""RECOVERX AI — Outcome ORM Model"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from app.database import Base


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True, unique=True)
    status = Column(String(32), nullable=False, default="NOT_RECOVERED")
    recovered_amount = Column(Float, default=0.0)
    recovery_cost = Column(Float, default=0.0)
    net_recovered = Column(Float, default=0.0)
    recovery_time_seconds = Column(Float, default=0.0)
    strategy_used = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    expected_recovery_value = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "status": self.status,
            "recovered_amount": self.recovered_amount,
            "recovery_cost": self.recovery_cost,
            "net_recovered": self.net_recovered,
            "recovery_time_seconds": self.recovery_time_seconds,
            "strategy_used": self.strategy_used,
            "notes": self.notes,
            "expected_recovery_value": self.expected_recovery_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
