"""
RECOVERX AI — Agent 3: Customer Context Intelligence
Builds a recovery behaviour profile and calculates fatigue score.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import CommunicationChannel, CustomerProfile


class ContextIntelligenceAgent(BaseAgent):
    """
    Customer Context Intelligence Agent.
    Analyses payment history, contact history, and fatigue to build a recovery profile.
    """

    @property
    def agent_name(self) -> str:
        return "customer_context_intelligence"

    @property
    def is_llm_agent(self) -> bool:
        return True

    @property
    def system_prompt(self) -> str:
        return """You are the Customer Context Intelligence Agent for RECOVERX AI.

Your role: Build a comprehensive customer recovery behaviour profile.

Fatigue Score Calculation (0 = no fatigue, 1 = completely fatigued):
- Each message in last 7 days: +0.15
- Each call in last 7 days: +0.25
- No-response streak (each): +0.10
- Previous negative response: +0.20
- Opt-out signal: +1.0 (max out)

Fatigue Levels:
- 0.0-0.29: LOW — normal outreach allowed
- 0.30-0.59: MEDIUM — reduce frequency
- 0.60-0.79: HIGH — minimal contact only
- 0.80+: CRITICAL — stop contact

Preferred Channel Selection:
- If customer has responded to WhatsApp in past: WHATSAPP
- If email open rate > 30%: EMAIL
- Default based on customer tier (PREMIUM → WhatsApp, STANDARD → Email)

Return CustomerProfile JSON."""

    async def _run_with_llm(self, state: dict[str, Any]) -> CustomerProfile:
        customer = state.get("customer_raw", {})
        event = state.get("event_data", {})

        prompt = f"""Build a recovery behaviour profile for this customer:

Customer Data:
{json.dumps(customer, indent=2, default=str)}

Current Event:
- Amount: ₹{event.get('amount', 0):,.0f}
- Event type: {event.get('event_type')}
- Payment method: {event.get('payment_method')}

Calculate fatigue score from contact history, determine preferred recovery channel,
and identify any flags that should influence recovery strategy.

Return CustomerProfile JSON."""

        return await self._llm_generate(prompt, CustomerProfile)

    async def _run_fallback(self, state: dict[str, Any]) -> CustomerProfile:
        """Deterministic customer profile construction."""
        customer = state.get("customer_raw", {})
        contact_history = customer.get("contact_history", []) or []
        payment_history = customer.get("payment_history", []) or []

        # Calculate fatigue score
        contact_count_7d = customer.get("contact_count_7d", 0)
        no_response_streak = customer.get("no_response_streak", 0)
        opt_out = customer.get("opt_out", False)

        fatigue = 0.0
        fatigue += contact_count_7d * 0.15
        fatigue += no_response_streak * 0.10
        if opt_out:
            fatigue = 1.0

        # Add history-based fatigue
        recent_negative = sum(
            1 for c in contact_history[-10:]
            if isinstance(c, dict) and c.get("outcome") in ("NEGATIVE", "NO_RESPONSE", "BLOCKED")
        )
        fatigue += recent_negative * 0.20
        fatigue = min(1.0, fatigue)

        # Fatigue level
        if fatigue < 0.30:
            fatigue_level = "LOW"
        elif fatigue < 0.60:
            fatigue_level = "MEDIUM"
        elif fatigue < 0.80:
            fatigue_level = "HIGH"
        else:
            fatigue_level = "CRITICAL"

        # Preferred channel
        tier = customer.get("tier", "STANDARD")
        stored_channel = customer.get("preferred_channel", "").upper()
        if stored_channel in {c.value for c in CommunicationChannel}:
            preferred = CommunicationChannel(stored_channel)
        elif tier == "PREMIUM":
            preferred = CommunicationChannel.WHATSAPP
        else:
            preferred = CommunicationChannel.EMAIL

        # Payment reliability from history
        if payment_history:
            successful = sum(1 for p in payment_history if isinstance(p, dict) and p.get("status") == "SUCCESS")
            reliability = successful / len(payment_history) if payment_history else 0.5
        else:
            reliability = customer.get("historical_recovery_rate", 0.5)

        # Last successful payment
        last_payment_days = None
        for p in reversed(payment_history):
            if isinstance(p, dict) and p.get("status") == "SUCCESS" and p.get("date"):
                try:
                    last_dt = datetime.fromisoformat(p["date"].replace("Z", "+00:00"))
                    last_payment_days = (datetime.now(timezone.utc) - last_dt).days
                    break
                except Exception:
                    pass

        insights = []
        if fatigue_level in ("HIGH", "CRITICAL"):
            insights.append(f"High fatigue ({fatigue:.2f}) — reduce outreach frequency")
        if no_response_streak > 2:
            insights.append(f"No response for {no_response_streak} consecutive attempts")
        if tier == "PREMIUM":
            insights.append("Premium customer — prioritise high-touch recovery")

        return CustomerProfile(
            customer_id=customer.get("external_id", customer.get("id", "unknown")),
            customer_name=customer.get("name", "Unknown"),
            tier=tier,
            fatigue_score=round(fatigue, 3),
            preferred_channel=preferred,
            payment_reliability=round(float(reliability), 3),
            historical_recovery_rate=round(customer.get("historical_recovery_rate", 0.5), 3),
            last_successful_payment_days_ago=last_payment_days,
            contact_count_7d=contact_count_7d,
            best_contact_time=customer.get("best_contact_time", "10:00-12:00"),
            opt_out=opt_out,
            lifetime_value=float(customer.get("lifetime_value", 0.0)),
            no_response_streak=no_response_streak,
            contact_fatigue_level=fatigue_level,
            insights=insights,
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, CustomerProfile)
        abort = output.opt_out or output.contact_fatigue_level == "CRITICAL"
        return {
            "customer_profile": output.model_dump(),
            "abort": abort or state.get("abort", False),
            "abort_reason": "Customer fatigue CRITICAL or opt-out" if abort else state.get("abort_reason"),
        }
