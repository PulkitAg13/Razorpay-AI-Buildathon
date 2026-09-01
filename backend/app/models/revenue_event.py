"""RECOVERX AI — RevenueEvent ORM Model"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from app.database import Base


class RevenueEvent(Base):
    __tablename__ = "revenue_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(64), unique=True, nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False, default="INR")
    customer_id = Column(Integer, nullable=False, index=True)
    payment_method = Column(String(32), nullable=True)
    failure_reason = Column(String(128), nullable=True)
    gateway = Column(String(64), nullable=True)
    gateway_error_code = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="PENDING")
    metadata_json = Column(Text, nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "external_id": self.external_id,
            "event_type": self.event_type,
            "amount": self.amount,
            "currency": self.currency,
            "customer_id": self.customer_id,
            "payment_method": self.payment_method,
            "failure_reason": self.failure_reason,
            "gateway": self.gateway,
            "gateway_error_code": self.gateway_error_code,
            "status": self.status,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
