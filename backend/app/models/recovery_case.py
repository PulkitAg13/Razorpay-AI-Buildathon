"""RECOVERX AI — RecoveryCase ORM Model"""
import json
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from app.database import Base


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), unique=True, nullable=False, index=True)
    event_id = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="CREATED")
    current_step = Column(String(64), nullable=True)
    root_cause = Column(String(64), nullable=True)
    selected_strategy = Column(String(64), nullable=True)
    policy_approved = Column(Boolean, default=False)
    outcome_status = Column(String(32), nullable=True)
    recovered_amount = Column(Float, default=0.0)
    recovery_cost = Column(Float, default=0.0)
    revenue_at_risk = Column(Float, default=0.0)
    expected_recovery_value = Column(Float, default=0.0)
    error_count = Column(Integer, default=0)
    errors_json = Column(Text, nullable=True)
    human_escalation_required = Column(Boolean, default=False)
    is_simulation = Column(Boolean, default=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Agent output JSON fields
    sentinel_output_json = Column(Text, nullable=True)
    diagnosis_output_json = Column(Text, nullable=True)
    customer_profile_json = Column(Text, nullable=True)
    opportunity_score_json = Column(Text, nullable=True)
    candidate_strategies_json = Column(Text, nullable=True)
    twin_predictions_json = Column(Text, nullable=True)
    guardian_decision_json = Column(Text, nullable=True)
    execution_result_json = Column(Text, nullable=True)
    learning_update_json = Column(Text, nullable=True)

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
            "event_id": self.event_id,
            "status": self.status,
            "current_step": self.current_step,
            "root_cause": self.root_cause,
            "selected_strategy": self.selected_strategy,
            "policy_approved": self.policy_approved,
            "outcome_status": self.outcome_status,
            "recovered_amount": self.recovered_amount,
            "recovery_cost": self.recovery_cost,
            "revenue_at_risk": self.revenue_at_risk,
            "expected_recovery_value": self.expected_recovery_value,
            "error_count": self.error_count,
            "human_escalation_required": self.human_escalation_required,
            "is_simulation": self.is_simulation,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "sentinel_output": self._parse("sentinel_output_json"),
            "diagnosis_output": self._parse("diagnosis_output_json"),
            "customer_profile": self._parse("customer_profile_json"),
            "opportunity_score": self._parse("opportunity_score_json"),
            "candidate_strategies": self._parse("candidate_strategies_json"),
            "twin_predictions": self._parse("twin_predictions_json"),
            "guardian_decision": self._parse("guardian_decision_json"),
            "execution_result": self._parse("execution_result_json"),
        }
