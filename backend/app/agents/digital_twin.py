"""
RECOVERX AI — Agent 6: Recovery Digital Twin
Simulates predicted outcomes for each candidate strategy deterministically.
This is the system's unique counterfactual evaluation layer.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import CandidateStrategy, DigitalTwinOutput, TwinPrediction, StrategyType
from app.simulation.engine import SimulationEngine


class DigitalTwinAgent(BaseAgent):
    """
    Recovery Digital Twin Agent.
    Simulates expected outcomes for each candidate strategy using the simulation engine.
    Ranks strategies by Net Expected Value (NEV).
    Completely deterministic — requires 0 LLM calls.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._sim = SimulationEngine()

    @property
    def agent_name(self) -> str:
        return "recovery_digital_twin"

    @property
    def is_llm_agent(self) -> bool:
        return False  # Pure deterministic counterfactual simulation

    async def _run_fallback(self, state: dict[str, Any]) -> DigitalTwinOutput:
        """Deterministic simulation using the SimulationEngine probability model."""
        event = state.get("event_data", {})
        diagnosis = state.get("diagnosis_output", {})
        profile = state.get("customer_profile", {})
        strategies_data = state.get("candidate_strategies", [])

        amount = float(event.get("amount", 0))
        payment_method = event.get("payment_method", "CARD")
        root_cause = diagnosis.get("root_cause", "UNKNOWN")
        tier = profile.get("tier", "STANDARD")
        fatigue = float(profile.get("fatigue_score", 0.0))

        predictions = []
        for idx, strat_item in enumerate(strategies_data):
            if isinstance(strat_item, dict):
                st_type = strat_item.get("strategy_type", "RETRY_LATER")
                st_name = st_type.value if hasattr(st_type, "value") else str(st_type)
                cost = float(strat_item.get("estimated_cost", 0.0))
                friction = float(strat_item.get("estimated_friction", 0.05))
                rank = int(strat_item.get("rank", idx + 1))
            elif hasattr(strat_item, "strategy_type"):
                st_name = strat_item.strategy_type.value if hasattr(strat_item.strategy_type, "value") else str(strat_item.strategy_type)
                cost = float(strat_item.estimated_cost)
                friction = float(strat_item.estimated_friction)
                rank = int(strat_item.rank)
            else:
                continue

            # Use simulation engine for probability
            success, prob = self._sim.simulate_strategy_outcome(
                strategy_type=st_name,
                root_cause=root_cause,
                payment_method=payment_method,
                customer_tier=tier,
                fatigue_score=fatigue,
                amount=amount,
                hours_since_failure=1.0,
            )

            expected_rev = amount * prob
            cost_val = cost or self._sim.estimate_strategy_cost(st_name, amount)
            compliance_risk = 0.0

            # High-fatigue communication actions have compliance risk
            if st_name in ("SEND_WHATSAPP", "SEND_EMAIL") and fatigue > 0.6:
                compliance_risk = min(0.4, fatigue - 0.3)

            nev = expected_rev - cost_val - (amount * friction)

            predictions.append(TwinPrediction(
                strategy_type=st_name,
                strategy_rank=rank,
                predicted_recovery_probability=round(prob, 3),
                expected_revenue=round(expected_rev, 2),
                estimated_cost=round(cost_val, 2),
                customer_friction=round(float(friction), 3),
                compliance_risk=round(compliance_risk, 3),
                confidence=0.85,
                net_expected_value=round(nev, 2),
                simulation_notes=(
                    f"Counterfactual simulation: {st_name} for {root_cause}. "
                    f"Prob={prob:.0%}, NEV=INR {nev:,.0f}."
                ),
                historical_basis="Synthetic simulation environment with contextual probability adjustment.",
            ))

        # Sort by NEV descending
        predictions.sort(key=lambda p: p.net_expected_value, reverse=True)

        best = predictions[0] if predictions else None

        return DigitalTwinOutput(
            predictions=predictions,
            recommended_strategy_type=best.strategy_type if best else "RETRY_LATER",
            simulation_confidence=round(
                sum(p.confidence for p in predictions) / len(predictions), 2
            ) if predictions else 0.80,
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, DigitalTwinOutput)
        return {
            "twin_predictions": [p.model_dump() for p in output.predictions],
            "digital_twin_output": output.model_dump(),
            "recommended_strategy": output.recommended_strategy_type,
        }
