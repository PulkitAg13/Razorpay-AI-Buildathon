"""
RECOVERX AI — Agent Base Class
All specialized agents inherit from this base.
Provides: Selective LLM invocation, deterministic execution, audit logging,
AI transparency metadata (decision_source, provider, model), and event publishing.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import LLMProvider, LLMProviderError, get_llm_provider
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """
    Base class for all RECOVERX AI agents.

    Each agent:
    - Declares whether it is an LLM-enabled agent or a deterministic agent
    - Deterministic agents NEVER call the LLM, preserving API quotas
    - LLM agents call Gemini/OpenAI with automatic fallback to deterministic reasoning
    - Writes an immutable audit log entry with full AI transparency metadata
    - Publishes an event to the reactive event bus
    """

    def __init__(self, llm: Optional[LLMProvider] = None) -> None:
        self._custom_llm = llm

    @property
    def _llm(self) -> LLMProvider:
        if self._custom_llm:
            return self._custom_llm
        return get_llm_provider()

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Unique agent identifier for logging and audit."""
        ...

    @property
    def is_llm_agent(self) -> bool:
        """
        Override in agents where semantic LLM reasoning is genuinely valuable:
        1. Root Cause Diagnosis Agent
        2. Customer Context Intelligence Agent
        3. Recovery Strategy Planner Agent
        
        All other agents default to False (pure deterministic logic).
        """
        return False

    @property
    def system_prompt(self) -> str:
        """System prompt guiding the LLM for this agent's role (if LLM-enabled)."""
        return ""

    async def _run_with_llm(self, state: dict[str, Any]) -> BaseModel:
        """Call the LLM and return a validated Pydantic output."""
        return await self._run_fallback(state)

    @abstractmethod
    async def _run_fallback(self, state: dict[str, Any]) -> BaseModel:
        """
        Deterministic execution logic.
        For deterministic agents, this is the primary reasoning engine.
        For LLM agents, this provides fallback if the LLM is unavailable.
        Must never raise — always return a valid Pydantic model.
        """
        ...

    async def run(
        self,
        state: dict[str, Any],
        db: Optional[AsyncSession] = None,
    ) -> dict[str, Any]:
        """
        Execute this agent:
        1. If deterministic agent → execute deterministic logic directly (0 LLM calls)
        2. If LLM agent → try LLM; fallback to deterministic if unavailable / rate-limited
        3. Record decision_source (LLM, DETERMINISTIC, FALLBACK)
        4. Write audit log with AI transparency metadata
        5. Publish event to reactive bus
        6. Return state update dict
        """
        start = time.monotonic()
        used_llm = False
        used_fallback = False
        decision_source = "DETERMINISTIC"
        error_message = None
        output: Optional[BaseModel] = None

        if self.is_llm_agent:
            # ── LLM Attempt (Only for semantic reasoning agents) ───────────
            try:
                output = await self._run_with_llm(state)
                used_llm = True
                decision_source = "LLM"
                logger.debug(f"[{self.agent_name}] LLM output generated successfully.")
            except (LLMProviderError, Exception) as exc:
                error_message = str(exc)
                logger.warning(f"[{self.agent_name}] LLM unavailable ({str(exc)[:100]}). Using deterministic fallback.")
                used_fallback = True
                decision_source = "FALLBACK"

        # ── Deterministic Engine (Primary for rules/math, fallback for LLM) ──
        if output is None:
            try:
                output = await self._run_fallback(state)
            except Exception as fallback_exc:
                logger.error(f"[{self.agent_name}] Deterministic execution failed: {fallback_exc}")
                return {
                    "errors": state.get("errors", []) + [f"{self.agent_name}: {fallback_exc}"],
                    "error_count": state.get("error_count", 0) + 1,
                    "current_step": self.agent_name,
                }

        duration_ms = (time.monotonic() - start) * 1000

        # Provider transparency info
        provider_name = self._llm.provider_name if used_llm else "None"
        model_name = getattr(self._llm, "_model", "None") if used_llm else "None"

        # ── Collect Audit Entry dict ─────────────────────────────────────────
        from datetime import datetime, timezone
        safe_input = {
            k: v for k, v in state.items()
            if k in ("case_id", "event_data", "current_step", "error_count")
        }
        
        PIPELINE_AGENT_ORDER = {
            "revenue_sentinel": 1,
            "root_cause_diagnosis": 2,
            "customer_context_intelligence": 3,
            "recovery_opportunity": 4,
            "recovery_strategy_planner": 5,
            "recovery_digital_twin": 6,
            "compliance_policy_guardian": 7,
            "recovery_execution": 8,
            "outcome_monitor": 9,
            "learning_optimization": 10,
        }
        step_index = PIPELINE_AGENT_ORDER.get(self.agent_name, 0)

        audit_dict = {
            "case_id": state.get("case_id", "unknown"),
            "agent_name": self.agent_name,
            "step_index": step_index,
            "decision": self._get_decision_summary(output),
            "reasoning": self._get_reasoning(output),
            "confidence": self._get_confidence(output),
            "decision_source": decision_source,
            "llm_provider": provider_name,
            "llm_model": model_name,
            "llm_used": bool(used_llm),
            "used_fallback": bool(used_fallback),
            "input_json": json.dumps(safe_input, default=str),
            "output_json": output.model_dump_json(),
            "had_error": bool(error_message is not None and not used_fallback),
            "error_message": error_message,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # ── Audit Log to DB if session provided ──────────────────────────────
        if db is not None:
            try:
                await self._write_audit_log(
                    db=db,
                    case_id=state.get("case_id", "unknown"),
                    output=output,
                    state_input=state,
                    decision_source=decision_source,
                    llm_provider=provider_name,
                    llm_model=model_name,
                    used_llm=used_llm,
                    used_fallback=used_fallback,
                    error_message=error_message,
                    duration_ms=duration_ms,
                    step_index=step_index,
                )
            except Exception as ae:
                logger.warning(f"[{self.agent_name}] Audit log write failed: {ae}")

        # ── Build state update ────────────────────────────────────────────────
        update = self._build_state_update(output, state)
        update["current_step"] = self.agent_name
        update["decision_source"] = decision_source
        
        # Accumulate audit logs in workflow state
        existing_audits = list(state.get("audit_entries", []))
        existing_audits.append(audit_dict)
        update["audit_entries"] = existing_audits

        # ── Publish event ────────────────────────────────────────────────────
        try:
            await self._publish_event(state, output, decision_source, duration_ms)
        except Exception as pe:
            logger.debug(f"[{self.agent_name}] Event publish failed: {pe}")

        return update

    @abstractmethod
    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        """Map the agent output into the LangGraph state update dict."""
        ...

    async def _write_audit_log(
        self,
        db: AsyncSession,
        case_id: str,
        output: BaseModel,
        state_input: dict[str, Any],
        decision_source: str,
        llm_provider: str,
        llm_model: str,
        used_llm: bool,
        used_fallback: bool,
        error_message: Optional[str],
        duration_ms: float,
        step_index: int = 0,
    ) -> None:
        """Write an immutable audit entry with full AI transparency metadata."""
        safe_input = {
            k: v for k, v in state_input.items()
            if k in ("case_id", "event_data", "current_step", "error_count")
        }

        log = AuditLog(
            case_id=case_id,
            agent_name=self.agent_name,
            step_index=step_index,
            decision=self._get_decision_summary(output),
            reasoning=self._get_reasoning(output),
            confidence=self._get_confidence(output),
            decision_source=decision_source,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_used=int(used_llm),
            used_fallback=int(used_fallback),
            input_json=json.dumps(safe_input, default=str),
            output_json=output.model_dump_json(),
            had_error=int(error_message is not None and not used_fallback),
            error_message=error_message,
            duration_ms=duration_ms,
        )
        db.add(log)

    async def _publish_event(
        self,
        state: dict[str, Any],
        output: BaseModel,
        decision_source: str,
        duration_ms: float,
    ) -> None:
        from app.eventbus import get_event_bus
        bus = get_event_bus()
        await bus.publish("live_feed", {
            "type": "agent_step",
            "agent": self.agent_name,
            "case_id": state.get("case_id"),
            "decision": self._get_decision_summary(output),
            "decision_source": decision_source,
            "confidence": self._get_confidence(output),
            "duration_ms": round(duration_ms, 1),
        })

    # ── Overridable helpers ───────────────────────────────────────────────────

    def _get_decision_summary(self, output: BaseModel) -> str:
        """Extract a short decision string from the output for audit."""
        for field in ("classification", "root_cause", "status", "approved", "action_taken", "decision"):
            val = getattr(output, field, None)
            if val is not None:
                return str(val)
        return type(output).__name__

    def _get_reasoning(self, output: BaseModel) -> str:
        for field in ("reasoning", "economic_rationale", "planning_reasoning", "notes"):
            val = getattr(output, field, None)
            if val:
                return str(val)[:1000]
        return ""

    def _get_confidence(self, output: BaseModel) -> float:
        for field in ("confidence", "simulation_confidence", "recovery_probability"):
            val = getattr(output, field, None)
            if isinstance(val, (int, float)):
                return float(val)
        return 0.0

    async def _llm_generate(
        self,
        user_prompt: str,
        schema: Type[T],
        temperature: float = 0.1,
    ) -> T:
        """Convenience wrapper around the LLM provider's generate_structured."""
        return await self._llm.generate_structured(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            temperature=temperature,
        )
