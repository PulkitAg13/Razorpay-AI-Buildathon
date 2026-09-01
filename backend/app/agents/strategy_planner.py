"""
RECOVERX AI — Agent 5: Recovery Strategy Planner
Generates ranked candidate strategies. Does NOT execute them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import CandidateStrategy, StrategyPlannerOutput, StrategyType


class StrategyPlannerAgent(BaseAgent):
    """
    Recovery Strategy Planner Agent.
    Generates 3-5 ranked candidate strategies based on context.
    Does NOT execute — only generates options for the Digital Twin to evaluate.
    """

    @property
    def agent_name(self) -> str:
        return "recovery_strategy_planner"

    @property
    def is_llm_agent(self) -> bool:
        return True

    @property
    def system_prompt(self) -> str:
        return """You are the Recovery Strategy Planner Agent for RECOVERX AI.

Your role: Generate multiple ranked candidate recovery strategies. You NEVER execute them.

Available strategies:
- RETRY_PAYMENT: Immediately retry the same payment
- RETRY_LATER: Schedule a retry at optimal time
- GENERATE_PAYMENT_LINK: Send a payment link via preferred channel
- OFFER_ALTERNATE_PAYMENT: Suggest different payment method
- SEND_WHATSAPP: Send WhatsApp reminder/notification
- SEND_EMAIL: Send email with payment link
- SCHEDULE_FOLLOWUP: Schedule human or automated follow-up
- ESCALATE_TO_HUMAN: Hand off to human agent
- STOP_RECOVERY: Do not attempt recovery

Strategy selection guidance:
- TEMPORARY_BANK_FAILURE → RETRY_LATER (wait 1-2 hours), then SEND_WHATSAPP
- INSUFFICIENT_FUNDS → SCHEDULE_FOLLOWUP (payday), SEND_EMAIL with gentle reminder
- PAYMENT_METHOD_FAILURE → OFFER_ALTERNATE_PAYMENT + GENERATE_PAYMENT_LINK
- CUSTOMER_ABANDONMENT → SEND_WHATSAPP first, then GENERATE_PAYMENT_LINK
- HIGH_VALUE (>₹50k) → Consider ESCALATE_TO_HUMAN

Constraints to consider:
- Customer fatigue score
- Contact attempts in last 7 days
- Contact hours (do not disturb outside allowed window)
- Maximum retries

Generate 3-5 candidates ranked by expected effectiveness (rank 1 = best).
Return StrategyPlannerOutput JSON."""

    async def _run_with_llm(self, state: dict[str, Any]) -> StrategyPlannerOutput:
        event = state.get("event_data", {})
        diagnosis = state.get("diagnosis_output", {})
        profile = state.get("customer_profile", {})
        opportunity = state.get("opportunity_score", {})

        now = datetime.now(timezone.utc)
        prompt = f"""Generate recovery strategies for this case:

Transaction:
- Amount: ₹{event.get('amount', 0):,.2f}
- Event type: {event.get('event_type')}
- Payment method: {event.get('payment_method')}

Diagnosis:
- Root cause: {diagnosis.get('root_cause')}
- Recoverability: {diagnosis.get('recoverability', 0.5):.0%}
- Time sensitive: {diagnosis.get('time_sensitive', False)}

Customer Profile:
- Tier: {profile.get('tier')}
- Preferred channel: {profile.get('preferred_channel')}
- Fatigue level: {profile.get('contact_fatigue_level')}
- Contact count 7d: {profile.get('contact_count_7d', 0)}

Opportunity:
- Net expected value: ₹{opportunity.get('net_expected_value', 0):,.0f}
- Priority: {opportunity.get('priority')}

Current time (UTC): {now.strftime('%H:%M')}

Generate 3-5 candidate strategies ranked by expected effectiveness.
Return StrategyPlannerOutput JSON with candidate_strategies list."""

        return await self._llm_generate(prompt, StrategyPlannerOutput)

    async def _run_fallback(self, state: dict[str, Any]) -> StrategyPlannerOutput:
        """Rule-based strategy generation based on root cause."""
        event = state.get("event_data", {})
        diagnosis = state.get("diagnosis_output", {})
        profile = state.get("customer_profile", {})
        opportunity = state.get("opportunity_score", {})

        from app.config import get_settings
        settings = get_settings()

        root_cause = diagnosis.get("root_cause", "UNKNOWN")
        amount = float(event.get("amount", 0))
        tier = profile.get("tier", "STANDARD")
        preferred_channel = profile.get("preferred_channel", "EMAIL")
        fatigue_level = profile.get("contact_fatigue_level", "LOW")
        contact_count = int(profile.get("contact_count_7d", 0))

        candidates = []
        constraints_applied = []

        # Contact hours check
        now_hour = datetime.now(timezone.utc).hour + 5  # IST offset approx
        now_hour_ist = now_hour % 24
        outside_hours = not (settings.contact_hours_start <= now_hour_ist < settings.contact_hours_end)
        if outside_hours:
            constraints_applied.append("OUTSIDE_CONTACT_HOURS_constraint applied — scheduling for later")

        # Strategy matrix
        strategy_configs = {
            "TEMPORARY_BANK_FAILURE": [
                (StrategyType.RETRY_LATER, {"delay_hours": 2}, 0.72, 15.0, 0.10),
                (StrategyType.SEND_WHATSAPP if preferred_channel == "WHATSAPP" else StrategyType.SEND_EMAIL,
                 {"template": "payment_retry_reminder"}, 0.55, 25.0, 0.20),
                (StrategyType.GENERATE_PAYMENT_LINK, {"expiry_hours": 48}, 0.50, 35.0, 0.15),
            ],
            "INSUFFICIENT_FUNDS": [
                (StrategyType.SCHEDULE_FOLLOWUP, {"delay_hours": 72, "reason": "payday"}, 0.40, 15.0, 0.25),
                (StrategyType.SEND_EMAIL, {"template": "gentle_reminder"}, 0.35, 10.0, 0.15),
                (StrategyType.GENERATE_PAYMENT_LINK, {"expiry_hours": 72}, 0.32, 35.0, 0.15),
            ],
            "PAYMENT_METHOD_FAILURE": [
                (StrategyType.OFFER_ALTERNATE_PAYMENT, {"suggest": "UPI"}, 0.68, 30.0, 0.10),
                (StrategyType.GENERATE_PAYMENT_LINK, {"expiry_hours": 48}, 0.60, 35.0, 0.10),
                (StrategyType.SEND_WHATSAPP if preferred_channel == "WHATSAPP" else StrategyType.SEND_EMAIL,
                 {"template": "alternate_payment_offer"}, 0.52, 20.0, 0.15),
            ],
            "CUSTOMER_ABANDONMENT": [
                (StrategyType.SEND_WHATSAPP, {"template": "cart_recovery"}, 0.62, 25.0, 0.20),
                (StrategyType.GENERATE_PAYMENT_LINK, {"expiry_hours": 24}, 0.55, 35.0, 0.10),
                (StrategyType.SEND_EMAIL, {"template": "cart_recovery_email"}, 0.45, 10.0, 0.15),
            ],
            "TECHNICAL_CHECKOUT_ISSUE": [
                (StrategyType.RETRY_PAYMENT, {}, 0.75, 10.0, 0.05),
                (StrategyType.GENERATE_PAYMENT_LINK, {"expiry_hours": 24}, 0.65, 35.0, 0.10),
                (StrategyType.SEND_WHATSAPP, {"template": "tech_issue_retry"}, 0.55, 25.0, 0.15),
            ],
        }

        config = strategy_configs.get(root_cause, strategy_configs["TEMPORARY_BANK_FAILURE"])

        # Apply fatigue constraint — reduce options if high fatigue
        if fatigue_level in ("HIGH", "CRITICAL"):
            config = config[:1]  # Only best option
            constraints_applied.append("HIGH_FATIGUE: limiting to 1 strategy")

        # High-value → add human escalation
        if amount > settings.high_value_threshold:
            config.append((StrategyType.ESCALATE_TO_HUMAN, {}, 0.90, 150.0, 0.05))
            constraints_applied.append("HIGH_VALUE: added human escalation option")

        for rank, (stype, params, success_rate, cost, friction) in enumerate(config, 1):
            candidates.append(CandidateStrategy(
                strategy_type=stype,
                parameters=params,
                estimated_success_rate=success_rate,
                estimated_cost=cost,
                estimated_friction=friction,
                reasoning=f"Rank {rank}: {stype.value} for {root_cause} — est. {success_rate:.0%} success",
                rank=rank,
                is_automated=stype not in (StrategyType.ESCALATE_TO_HUMAN, StrategyType.STOP_RECOVERY),
            ))

        return StrategyPlannerOutput(
            candidate_strategies=candidates,
            planning_reasoning=f"Generated {len(candidates)} strategies for {root_cause}. Ranked by expected effectiveness. Constraints: {', '.join(constraints_applied) or 'none'}.",
            total_candidates=len(candidates),
            constraints_applied=constraints_applied,
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, StrategyPlannerOutput)
        return {
            "candidate_strategies": [s.model_dump() for s in output.candidate_strategies],
            "strategy_planner_output": output.model_dump(),
        }
