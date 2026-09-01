"""
RECOVERX AI — Agent 1: Revenue Sentinel
Monitors revenue events and classifies recovery potential.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import RecoverabilityClassification, SentinelOutput


class SentinelAgent(BaseAgent):
    """
    Revenue Sentinel — First agent in the pipeline.
    Classifies whether a revenue event is worth recovering and assigns priority.
    """

    @property
    def agent_name(self) -> str:
        return "revenue_sentinel"

    @property
    def system_prompt(self) -> str:
        return """You are the Revenue Sentinel Agent for RECOVERX AI, an autonomous revenue recovery system.

Your role: Analyze incoming revenue events and classify their recovery potential.

Classification options:
- HIGH_RECOVERY_POTENTIAL: >70% estimated chance of recovery, significant revenue at risk
- MEDIUM_RECOVERY_POTENTIAL: 40-70% estimated chance of recovery
- LOW_RECOVERY_POTENTIAL: <40% chance but economically worth attempting
- DO_NOT_CONTACT: Customer opted out, too many failed attempts, or compliance block
- ALREADY_RESOLVED: Payment already completed or case closed

Priority score (0-100):
- 90-100: Critical, act immediately (large amount, high probability)
- 70-89: High priority
- 50-69: Medium priority
- 0-49: Low priority

Consider:
1. Transaction amount (higher = more priority)
2. Event type (payment failure vs abandonment)
3. Failure reason (some are more recoverable than others)
4. Contact history (too many = DO_NOT_CONTACT)
5. Opt-out signals

Return a JSON object matching the SentinelOutput schema exactly."""

    async def _run_with_llm(self, state: dict[str, Any]) -> SentinelOutput:
        event = state.get("event_data", {})
        customer = state.get("customer_raw", {})

        prompt = f"""Analyze this revenue event and classify its recovery potential:

Event Data:
{json.dumps(event, indent=2, default=str)}

Customer Context:
- Contact attempts in last 7 days: {customer.get('contact_count_7d', 0)}
- Opt-out status: {customer.get('opt_out', False)}
- Customer tier: {customer.get('tier', 'STANDARD')}

Classify the recovery potential and return SentinelOutput JSON."""

        result = await self._llm_generate(prompt, SentinelOutput)
        if result.revenue_at_risk <= 0 or result.revenue_at_risk < 1:
            result.revenue_at_risk = float(event.get("amount", 0))
        return result

    async def _run_fallback(self, state: dict[str, Any]) -> SentinelOutput:
        """Deterministic fallback based on event data analysis."""
        event = state.get("event_data", {})
        customer = state.get("customer_raw", {})

        amount = float(event.get("amount", 0))
        event_type = event.get("event_type", "PAYMENT_FAILURE")
        failure_reason = event.get("failure_reason", "UNKNOWN")
        opt_out = customer.get("opt_out", False)
        contact_count = customer.get("contact_count_7d", 0)

        from app.config import get_settings
        settings = get_settings()

        # Hard stops
        if opt_out:
            return SentinelOutput(
                classification=RecoverabilityClassification.DO_NOT_CONTACT,
                priority_score=0.0,
                revenue_at_risk=amount,
                reasoning="Customer has opted out of communications.",
                confidence=0.99,
                contact_allowed=False,
                flags=["OPT_OUT"],
            )

        if contact_count >= settings.max_contact_attempts:
            return SentinelOutput(
                classification=RecoverabilityClassification.DO_NOT_CONTACT,
                priority_score=0.0,
                revenue_at_risk=amount,
                reasoning=f"Maximum contact attempts ({settings.max_contact_attempts}) reached.",
                confidence=0.95,
                contact_allowed=False,
                flags=["MAX_ATTEMPTS_REACHED"],
            )

        # Classify by recoverability
        high_prob_reasons = {"BANK_DECLINE", "TEMPORARY_BANK_FAILURE", "NETWORK_ERROR", "UPI_TIMEOUT", "TECHNICAL"}
        low_prob_reasons = {"INSUFFICIENT_FUNDS", "CREDIT_LIMIT"}

        failure_upper = failure_reason.upper()

        if any(r in failure_upper for r in high_prob_reasons):
            classification = RecoverabilityClassification.HIGH_RECOVERY_POTENTIAL
            base_priority = 75.0
            confidence = 0.82
        elif any(r in failure_upper for r in low_prob_reasons):
            classification = RecoverabilityClassification.LOW_RECOVERY_POTENTIAL
            base_priority = 35.0
            confidence = 0.75
        elif event_type == "CHECKOUT_ABANDONMENT":
            classification = RecoverabilityClassification.HIGH_RECOVERY_POTENTIAL
            base_priority = 70.0
            confidence = 0.78
        else:
            classification = RecoverabilityClassification.MEDIUM_RECOVERY_POTENTIAL
            base_priority = 55.0
            confidence = 0.70

        # Adjust priority by amount
        amount_boost = min(20.0, amount / 5000)
        priority = min(100.0, base_priority + amount_boost)

        return SentinelOutput(
            classification=classification,
            priority_score=round(priority, 1),
            revenue_at_risk=amount,
            reasoning=(
                f"Event type: {event_type}. Failure: {failure_reason}. "
                f"Amount: ₹{amount:,.0f}. Classification based on failure pattern analysis."
            ),
            confidence=confidence,
            contact_allowed=True,
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, SentinelOutput)
        abort = output.classification in (
            RecoverabilityClassification.DO_NOT_CONTACT,
            RecoverabilityClassification.ALREADY_RESOLVED,
        )
        return {
            "sentinel_output": output.model_dump(),
            "abort": abort,
            "abort_reason": f"Sentinel: {output.classification.value}" if abort else state.get("abort_reason"),
        }
