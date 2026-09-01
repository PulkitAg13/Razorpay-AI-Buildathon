"""
RECOVERX AI — Agent 10: Learning & Optimization
Updates strategy effectiveness statistics after each outcome.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.schemas.agents import LearningUpdate, OutcomeStatus


def _amount_bucket(amount: float) -> str:
    if amount < 500:
        return "MICRO"
    if amount < 5000:
        return "SMALL"
    if amount < 50000:
        return "MEDIUM"
    return "LARGE"


class LearningAgent(BaseAgent):
    """
    Learning & Optimization Agent.
    Updates the StrategyEffectiveness table after every outcome.
    The Digital Twin will use these records to improve future predictions.
    """

    @property
    def agent_name(self) -> str:
        return "learning_optimization"

    @property
    def system_prompt(self) -> str:
        return "Learning & Optimization Agent — updates strategy effectiveness statistics."

    async def _run_with_llm(self, state: dict[str, Any]) -> LearningUpdate:
        return await self._run_fallback(state)

    async def _run_fallback(self, state: dict[str, Any]) -> LearningUpdate:
        """Update effectiveness statistics in DB."""
        event = state.get("event_data", {})
        outcome = state.get("outcome_record", {})
        execution = state.get("execution_result", {})
        diagnosis = state.get("diagnosis_output", {})
        profile = state.get("customer_profile", {})

        strategy_type = execution.get("action_taken", "UNKNOWN")
        root_cause = diagnosis.get("root_cause", "UNKNOWN")
        customer_tier = profile.get("tier", "STANDARD")
        payment_method = event.get("payment_method", "CARD")
        amount = float(event.get("amount", 0))
        bucket = _amount_bucket(amount)

        outcome_status = outcome.get("status", "NOT_RECOVERED")
        recovered_amount = float(outcome.get("recovered_amount", 0))
        recovery_cost = float(outcome.get("recovery_cost", 0))
        recovery_time = float(outcome.get("recovery_time_seconds", 0))
        success = outcome_status == OutcomeStatus.RECOVERED.value

        strategy_key = f"{strategy_type}:{root_cause}:{customer_tier}:{payment_method}"

        insights = []
        if success:
            insights.append(f"Strategy {strategy_type} succeeded for {root_cause} case")
        else:
            insights.append(f"Strategy {strategy_type} did not recover ₹{amount:,.0f} for {root_cause}")

        if float(outcome.get("expected_vs_actual_ratio", 1.0)) < 0.5:
            insights.append("Significant under-performance vs Digital Twin prediction — model needs updating")
        elif float(outcome.get("expected_vs_actual_ratio", 1.0)) > 1.5:
            insights.append("Significantly over-performed prediction — confidence can increase")

        return LearningUpdate(
            strategy_key=strategy_key,
            effectiveness_delta=0.02 if success else -0.01,
            updated_success_rate=0.0,  # Filled in by DB update
            updated_stats={
                "amount": amount,
                "bucket": 0.0,
                "recovered": float(recovered_amount),
                "cost": float(recovery_cost),
                "time_s": float(recovery_time),
            },
            insights=insights,
            model_updated=True,
        )

    async def run_with_db_update(
        self,
        state: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Extended run that also persists effectiveness data to DB."""
        from sqlalchemy import select
        from app.models.strategy_effectiveness import StrategyEffectiveness

        result = await self.run(state, db)

        # Update StrategyEffectiveness table
        try:
            event = state.get("event_data", {})
            outcome = state.get("outcome_record", {})
            execution = state.get("execution_result", {})
            diagnosis = state.get("diagnosis_output", {})
            profile = state.get("customer_profile", {})

            strategy_type = execution.get("action_taken", "UNKNOWN")
            root_cause = diagnosis.get("root_cause", "UNKNOWN")
            customer_tier = profile.get("tier", "STANDARD")
            payment_method = event.get("payment_method", "CARD")
            amount = float(event.get("amount", 0))
            bucket = _amount_bucket(amount)
            success = outcome.get("status") == OutcomeStatus.RECOVERED.value
            recovered = float(outcome.get("recovered_amount", 0))
            cost = float(outcome.get("recovery_cost", 0))
            time_s = float(outcome.get("recovery_time_seconds", 0))

            # Upsert strategy effectiveness
            q = select(StrategyEffectiveness).where(
                StrategyEffectiveness.strategy_type == strategy_type,
                StrategyEffectiveness.root_cause == root_cause,
                StrategyEffectiveness.customer_tier == customer_tier,
                StrategyEffectiveness.payment_method == payment_method,
                StrategyEffectiveness.amount_bucket == bucket,
            )
            existing = (await db.execute(q)).scalar_one_or_none()

            if existing:
                existing.total_count += 1
                existing.success_count += 1 if success else 0
                existing.total_recovered_amount += recovered
                existing.total_recovery_cost += cost
                # Running average for time
                existing.avg_recovery_time_seconds = (
                    (existing.avg_recovery_time_seconds * (existing.total_count - 1) + time_s)
                    / existing.total_count
                )
                existing.success_rate = existing.success_count / existing.total_count
                existing.avg_net_value = (
                    (existing.total_recovered_amount - existing.total_recovery_cost)
                    / existing.total_count
                )
                # Confidence weight grows with sample size
                existing.confidence_weight = min(0.95, 0.1 + existing.total_count / 200)
            else:
                new_eff = StrategyEffectiveness(
                    strategy_type=strategy_type,
                    root_cause=root_cause,
                    customer_tier=customer_tier,
                    payment_method=payment_method,
                    amount_bucket=bucket,
                    success_count=1 if success else 0,
                    total_count=1,
                    total_recovered_amount=recovered,
                    total_recovery_cost=cost,
                    avg_recovery_time_seconds=time_s,
                    success_rate=1.0 if success else 0.0,
                    avg_net_value=recovered - cost,
                    confidence_weight=0.1,
                )
                db.add(new_eff)

        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"[LearningAgent] DB update failed: {exc}")

        return result

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, LearningUpdate)
        return {"learning_update": output.model_dump()}
