"""RECOVERX AI — HumanReview ORM Model"""
import json
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from app.database import Base


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True, unique=True)
    status = Column(String(32), nullable=False, default="PENDING")
    escalation_reason = Column(Text, nullable=True)
    escalation_priority = Column(String(16), nullable=False, default="MEDIUM")
    ai_recommendation_json = Column(Text, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    candidate_strategies_json = Column(Text, nullable=True)
    twin_predictions_json = Column(Text, nullable=True)
    policy_checks_json = Column(Text, nullable=True)
    amount_at_risk = Column(Float, default=0.0)
    ai_confidence = Column(Float, default=0.5)
    reviewer_notes = Column(Text, nullable=True)
    modified_strategy_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def _parse(self, field: str) -> Any:
        val = getattr(self, field, None)
        if val:
            try:
                return json.loads(val)
            except Exception:
                pass
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "status": self.status,
            "escalation_reason": self.escalation_reason,
            "escalation_priority": self.escalation_priority,
            "ai_recommendation": self._parse("ai_recommendation_json") or {},
            "reasoning_summary": self.reasoning_summary,
            "candidate_strategies": self._parse("candidate_strategies_json") or [],
            "twin_predictions": self._parse("twin_predictions_json") or [],
            "policy_checks": self._parse("policy_checks_json") or [],
            "amount_at_risk": self.amount_at_risk,
            "ai_confidence": self.ai_confidence,
            "reviewer_notes": self.reviewer_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
