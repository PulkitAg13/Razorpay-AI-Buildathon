"""RECOVERX AI — AuditLog ORM Model with AI Transparency Metadata"""
import json
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True)
    agent_name = Column(String(64), nullable=False, index=True)
    step_index = Column(Integer, default=0)
    decision = Column(String(256), nullable=True)
    reasoning = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    
    # AI Transparency Metadata
    decision_source = Column(String(32), default="DETERMINISTIC")  # LLM | DETERMINISTIC | FALLBACK
    llm_provider = Column(String(64), nullable=True)
    llm_model = Column(String(64), nullable=True)
    llm_used = Column(Integer, default=0)       # 0/1 for SQLite compat
    used_fallback = Column(Integer, default=0)  # 0/1 for SQLite compat

    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    had_error = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def _parse(self, field: str) -> Any:
        val = getattr(self, field, None)
        if val:
            try:
                return json.loads(val)
            except Exception:
                pass
        return {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "agent_name": self.agent_name,
            "step_index": self.step_index,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "decision_source": self.decision_source or ("LLM" if self.llm_used else "FALLBACK" if self.used_fallback else "DETERMINISTIC"),
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_used": bool(self.llm_used),
            "used_fallback": bool(self.used_fallback),
            "input": self._parse("input_json"),
            "output": self._parse("output_json"),
            "had_error": bool(self.had_error),
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tool_calls": [],
            "policy_checks": [],
        }
