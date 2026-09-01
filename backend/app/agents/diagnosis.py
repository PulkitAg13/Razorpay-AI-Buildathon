"""
RECOVERX AI — Agent 2: Root Cause Diagnosis
Determines why revenue was lost.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import DiagnosisOutput, RootCause


class DiagnosisAgent(BaseAgent):
    """
    Root Cause Diagnosis Agent — identifies WHY revenue was lost.
    Returns structured evidence and recoverability estimate.
    """

    @property
    def agent_name(self) -> str:
        return "root_cause_diagnosis"

    @property
    def is_llm_agent(self) -> bool:
        return True

    @property
    def system_prompt(self) -> str:
        return """You are the Root Cause Diagnosis Agent for RECOVERX AI.

Your role: Determine the precise root cause of a payment/revenue failure with evidence-backed reasoning.

Root cause options:
- TEMPORARY_BANK_FAILURE: Transient bank-side issues (server down, timeout, maintenance)
- INSUFFICIENT_FUNDS: Customer doesn't have enough money
- PAYMENT_METHOD_FAILURE: Card expired, UPI daily limit exceeded, method blocked
- CUSTOMER_ABANDONMENT: Customer intentionally left checkout
- TECHNICAL_CHECKOUT_ISSUE: Platform bug, gateway timeout, checkout session expired
- SUBSCRIPTION_PAYMENT_FAILURE: Recurring payment auto-debit failed
- INVOICE_DELAY: B2B invoice payment overdue, customer delay on purpose
- UNKNOWN: Cannot determine with confidence

For each diagnosis:
1. Cite specific evidence from the event data
2. Assign confidence (0-1) based on evidence strength
3. Estimate recoverability (0-1) — probability of recovery with optimal action
4. Flag time sensitivity (bank failures are time-sensitive; insufficient funds less so)

Return DiagnosisOutput JSON."""

    async def _run_with_llm(self, state: dict[str, Any]) -> DiagnosisOutput:
        event = state.get("event_data", {})
        sentinel = state.get("sentinel_output", {})

        prompt = f"""Diagnose the root cause of this revenue failure:

Event Data:
{json.dumps(event, indent=2, default=str)}

Sentinel Analysis:
- Classification: {sentinel.get('classification')}
- Revenue at risk: ₹{sentinel.get('revenue_at_risk', 0):,.0f}
- Priority score: {sentinel.get('priority_score')}

Analyze the failure_reason, gateway_error_code, event_type, and payment_method.
Return DiagnosisOutput JSON with root_cause, confidence, recoverability, supporting_evidence, reasoning."""

        return await self._llm_generate(prompt, DiagnosisOutput)

    async def _run_fallback(self, state: dict[str, Any]) -> DiagnosisOutput:
        """Rule-based root cause diagnosis."""
        event = state.get("event_data", {})
        failure_reason = event.get("failure_reason", "").upper()
        event_type = event.get("event_type", "PAYMENT_FAILURE")
        gateway_error = event.get("gateway_error_code", "").upper()

        # Rule-based mapping
        rules = [
            ({"INSUFFICIENT_FUNDS", "INSUFFICIENT", "LOW_BALANCE", "CREDIT_LIMIT"}, RootCause.INSUFFICIENT_FUNDS, 0.82, 0.30),
            ({"CARD_EXPIRED", "EXPIRED", "PAYMENT_METHOD_EXPIRED", "UPI_LIMIT"}, RootCause.PAYMENT_METHOD_FAILURE, 0.88, 0.55),
            ({"BANK_DECLINE", "BANK_ERROR", "BANK_TIMEOUT", "TEMPORARY", "TRANSIENT"}, RootCause.TEMPORARY_BANK_FAILURE, 0.80, 0.75),
            ({"NETWORK", "TIMEOUT", "GATEWAY_ERROR", "CHECKOUT_ERROR", "TECHNICAL"}, RootCause.TECHNICAL_CHECKOUT_ISSUE, 0.75, 0.72),
            ({"ABANDONED", "CUSTOMER_CANCELLED", "LEFT_PAGE", "SESSION_EXPIRED"}, RootCause.CUSTOMER_ABANDONMENT, 0.85, 0.52),
            ({"SUBSCRIPTION", "RECURRING", "AUTO_DEBIT"}, RootCause.SUBSCRIPTION_PAYMENT_FAILURE, 0.83, 0.58),
            ({"INVOICE", "OVERDUE", "NET30", "NET60"}, RootCause.INVOICE_DELAY, 0.80, 0.62),
        ]

        combined = failure_reason + " " + gateway_error + " " + event_type

        for keywords, cause, confidence, recoverability in rules:
            if any(kw in combined for kw in keywords):
                return DiagnosisOutput(
                    root_cause=cause,
                    confidence=confidence,
                    recoverability=recoverability,
                    supporting_evidence=[
                        f"Failure reason contains: {failure_reason}",
                        f"Gateway error: {gateway_error or 'N/A'}",
                        f"Event type: {event_type}",
                    ],
                    reasoning=f"Rule-based diagnosis: '{failure_reason}' matches {cause.value} pattern.",
                    time_sensitive=cause == RootCause.TEMPORARY_BANK_FAILURE,
                    recommended_window_hours=2 if cause == RootCause.TEMPORARY_BANK_FAILURE else 24,
                )

        # Default — unknown
        return DiagnosisOutput(
            root_cause=RootCause.UNKNOWN,
            confidence=0.45,
            recoverability=0.42,
            supporting_evidence=[f"Unrecognised failure pattern: {failure_reason}"],
            reasoning="Unable to determine root cause from available data. Using conservative defaults.",
            time_sensitive=False,
            recommended_window_hours=24,
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, DiagnosisOutput)
        return {
            "diagnosis_output": output.model_dump(),
            "root_cause": output.root_cause.value,
        }
