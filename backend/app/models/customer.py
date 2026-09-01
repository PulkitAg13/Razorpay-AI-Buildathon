"""RECOVERX AI — Customer ORM Model"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    email = Column(String(256), nullable=True)
    phone = Column(String(32), nullable=True)
    tier = Column(String(32), nullable=False, default="STANDARD")
    preferred_payment_method = Column(String(32), nullable=True)
    preferred_channel = Column(String(32), nullable=False, default="EMAIL")
    best_contact_time = Column(String(32), nullable=True)
    historical_recovery_rate = Column(Float, nullable=False, default=0.5)
    total_successful_payments = Column(Integer, default=0)
    total_failed_payments = Column(Integer, default=0)
    lifetime_value = Column(Float, default=0.0)
    fatigue_score = Column(Float, default=0.0)
    contact_count_7d = Column(Integer, default=0)
    no_response_streak = Column(Integer, default=0)
    opt_out = Column(Boolean, default=False)
    payment_history_json = Column(Text, nullable=True)
    contact_history_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "external_id": self.external_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "tier": self.tier,
            "preferred_payment_method": self.preferred_payment_method,
            "preferred_channel": self.preferred_channel,
            "best_contact_time": self.best_contact_time,
            "historical_recovery_rate": self.historical_recovery_rate,
            "total_successful_payments": self.total_successful_payments,
            "total_failed_payments": self.total_failed_payments,
            "lifetime_value": self.lifetime_value,
            "fatigue_score": self.fatigue_score,
            "contact_count_7d": self.contact_count_7d,
            "no_response_streak": self.no_response_streak,
            "opt_out": self.opt_out,
        }
