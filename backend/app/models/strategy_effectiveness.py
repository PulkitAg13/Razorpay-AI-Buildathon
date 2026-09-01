"""RECOVERX AI — StrategyEffectiveness ORM Model"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, Float, Integer, String
from app.database import Base


class StrategyEffectiveness(Base):
    __tablename__ = "strategy_effectiveness"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_type = Column(String(64), nullable=False, index=True)
    root_cause = Column(String(64), nullable=False, index=True)
    customer_tier = Column(String(32), nullable=False)
    payment_method = Column(String(32), nullable=False)
    amount_bucket = Column(String(16), nullable=False)
    success_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    total_recovered_amount = Column(Float, default=0.0)
    total_recovery_cost = Column(Float, default=0.0)
    avg_recovery_time_seconds = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    avg_net_value = Column(Float, default=0.0)
    confidence_weight = Column(Float, default=0.1)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "strategy_type": self.strategy_type,
            "root_cause": self.root_cause,
            "customer_tier": self.customer_tier,
            "payment_method": self.payment_method,
            "amount_bucket": self.amount_bucket,
            "success_count": self.success_count,
            "total_count": self.total_count,
            "success_rate": round(self.success_rate, 3),
            "avg_net_value": round(self.avg_net_value, 2),
            "confidence_weight": self.confidence_weight,
        }
