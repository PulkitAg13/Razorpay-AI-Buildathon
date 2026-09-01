"""
RECOVERX AI — Agent 4: Recovery Opportunity Scorer
Calculates the financial ROI of recovery action.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import OpportunityScore, Priority


def _classify_amount_bucket(amount: float) -> str:
    if amount < 500:
        return "MICRO"
    if amount < 5000:
        return "SMALL"
    if amount < 50000:
        return "MEDIUM"
    return "LARGE"


class OpportunityAgent(BaseAgent):
    """
    Recovery Opportunity Agent.
    Calculates Expected Recovery Value (ERV) and determines if recovery is economically rational.

    ERV = Amount × Recovery_Probability − Recovery_Cost − Customer_Friction_Cost
    """

    @property
    def agent_name(self) -> str:
        return "recovery_opportunity"

    @property
    def system_prompt(self) -> str:
        return """You are the Recovery Opportunity Agent for RECOVERX AI.

Your role: Determine the financial return on investment of recovery actions.

Formula:
Expected Recovery Value (ERV) = Amount × Recovery_Probability
Net Expected Value (NEV) = ERV − Recovery_Cost − Customer_Friction_Cost

Recovery cost estimates (INR):
- Immediate retry: ₹10-20 (automated)
- Scheduled retry: ₹15-25
- Payment link generation: ₹25-40
- WhatsApp message: ₹15-30
- Email: ₹5-15
- Human escalation: ₹100-200

Customer friction cost:
- Low fatigue: 0.5% of transaction amount
- Medium fatigue: 1.0% of transaction amount
- High fatigue: 2.0% of transaction amount (relationship damage)

Priority:
- CRITICAL: NEV > ₹50,000 or revenue_at_risk > ₹100,000
- HIGH: NEV > ₹5,000
- MEDIUM: NEV > ₹500
- LOW: NEV > 0 but < ₹500
- Do not proceed if NEV ≤ 0 (not economically rational)

Return OpportunityScore JSON."""

    async def _run_with_llm(self, state: dict[str, Any]) -> OpportunityScore:
        event = state.get("event_data", {})
        diagnosis = state.get("diagnosis_output", {})
        profile = state.get("customer_profile", {})

        prompt = f"""Calculate the recovery opportunity for this case:

Transaction:
- Amount: ₹{event.get('amount', 0):,.2f}
- Currency: {event.get('currency', 'INR')}
- Event type: {event.get('event_type')}

Diagnosis:
- Root cause: {diagnosis.get('root_cause')}
- Recoverability estimate: {diagnosis.get('recoverability', 0.5):.0%}
- Confidence: {diagnosis.get('confidence', 0.5):.0%}

Customer Profile:
- Tier: {profile.get('tier', 'STANDARD')}
- Fatigue level: {profile.get('contact_fatigue_level', 'LOW')}
- Historical recovery rate: {profile.get('historical_recovery_rate', 0.5):.0%}
- Lifetime value: ₹{profile.get('lifetime_value', 0):,.0f}

Calculate: recovery_probability, expected_recovery_value, recovery_cost,
customer_friction_cost, net_expected_value, priority, is_economically_rational.
Return OpportunityScore JSON."""

        res = await self._llm_generate(prompt, OpportunityScore)
        amount = float(event.get("amount", 0))
        if res.expected_recovery_value <= 0 and amount > 0:
            res.expected_recovery_value = round(amount * res.recovery_probability, 2)
            res.net_expected_value = round(res.expected_recovery_value - res.recovery_cost - res.customer_friction_cost, 2)
            res.is_economically_rational = res.net_expected_value > 0
        return res

    async def _run_fallback(self, state: dict[str, Any]) -> OpportunityScore:
        """Deterministic financial calculation."""
        event = state.get("event_data", {})
        diagnosis = state.get("diagnosis_output", {})
        profile = state.get("customer_profile", {})

        from app.config import get_settings
        settings = get_settings()

        amount = float(event.get("amount", 0))
        base_recoverability = float(diagnosis.get("recoverability", 0.5))
        hist_rate = float(profile.get("historical_recovery_rate", 0.5))
        fatigue_score = float(profile.get("fatigue_score", 0.0))
        fatigue_level = profile.get("contact_fatigue_level", "LOW")

        # Combine diagnostic recoverability with historical rate
        recovery_prob = (base_recoverability * 0.6 + hist_rate * 0.4)
        recovery_prob = max(0.05, min(0.97, recovery_prob))

        # Expected Recovery Value
        erv = amount * recovery_prob

        # Recovery cost estimate (average across possible strategies)
        recovery_cost = min(erv * settings.max_recovery_cost_ratio, 150.0)

        # Customer friction cost based on fatigue
        friction_pct = {"LOW": 0.005, "MEDIUM": 0.010, "HIGH": 0.020, "CRITICAL": 0.040}
        friction = amount * friction_pct.get(fatigue_level, 0.010)

        # Net expected value
        nev = erv - recovery_cost - friction

        # Priority
        if nev > 50000 or amount > settings.high_value_threshold:
            priority = Priority.CRITICAL
        elif nev > 5000:
            priority = Priority.HIGH
        elif nev > 500:
            priority = Priority.MEDIUM
        else:
            priority = Priority.LOW

        bucket = _classify_amount_bucket(amount)

        return OpportunityScore(
            recovery_probability=round(recovery_prob, 3),
            expected_recovery_value=round(erv, 2),
            recovery_cost=round(recovery_cost, 2),
            customer_friction_cost=round(friction, 2),
            net_expected_value=round(nev, 2),
            priority=priority,
            is_economically_rational=nev > 0,
            economic_rationale=(
                f"ERV=₹{erv:,.0f} (prob={recovery_prob:.0%}), "
                f"cost=₹{recovery_cost:,.0f}, friction=₹{friction:,.0f}. "
                f"NEV=₹{nev:,.0f} — {'RATIONAL' if nev > 0 else 'NOT RATIONAL'}."
            ),
            amount_bucket=bucket,
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, OpportunityScore)
        abort = not output.is_economically_rational
        return {
            "opportunity_score": output.model_dump(),
            "abort": abort or state.get("abort", False),
            "abort_reason": "Not economically rational to pursue recovery" if abort else state.get("abort_reason"),
        }
