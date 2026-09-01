"""
RECOVERX AI — Agent 9: Outcome Monitor
Records the final result of recovery attempts and calculates metrics.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import OutcomeRecord, OutcomeStatus


class OutcomeMonitorAgent(BaseAgent):
    """
    Outcome Monitor Agent.
    Observes execution results and determines the final outcome status.
    Calculates recovered amount, recovery time, and NEV ratio.
    """

    @property
    def agent_name(self) -> str:
        return "outcome_monitor"

    @property
    def system_prompt(self) -> str:
        return "Outcome Monitor Agent — records recovery outcomes."

    async def _run_with_llm(self, state: dict[str, Any]) -> OutcomeRecord:
        # Outcome monitoring is always deterministic — no LLM needed
        return await self._run_fallback(state)

    async def _run_fallback(self, state: dict[str, Any]) -> OutcomeRecord:
        """Deterministic outcome determination from execution result."""
        import time

        execution = state.get("execution_result", {})
        event = state.get("event_data", {})
        guardian = state.get("guardian_decision", {})
        opportunity = state.get("opportunity_score", {})

        amount = float(event.get("amount", 0))
        action_taken = execution.get("action_taken", "NO_ACTION")
        success = bool(execution.get("success", False))

        # Determine outcome status
        if action_taken == "ESCALATE_TO_HUMAN":
            status = OutcomeStatus.ESCALATED
            recovered = 0.0
        elif action_taken == "STOP_RECOVERY":
            status = OutcomeStatus.STOPPED
            recovered = 0.0
        elif action_taken in ("RETRY_LATER", "SCHEDULE_FOLLOWUP"):
            # Scheduled — outcome pending
            status = OutcomeStatus.PENDING
            recovered = 0.0
        elif success:
            status = OutcomeStatus.RECOVERED
            # For payment link and comms — partial recovery possibility
            if action_taken in ("SEND_WHATSAPP", "SEND_EMAIL"):
                # Recovery happens when customer acts on the communication
                result_data = execution.get("result_data", {})
                paid = result_data.get("simulated_payment_completed", result_data.get("simulated_customer_responded", False))
                if paid:
                    recovered = amount
                else:
                    status = OutcomeStatus.PENDING
                    recovered = 0.0
            else:
                recovered = amount
        else:
            status = OutcomeStatus.NOT_RECOVERED
            recovered = 0.0

        # Calculate cost from selected strategy
        selected = guardian.get("selected_strategy", {})
        cost = float(selected.get("estimated_cost", 0.0)) if selected else 0.0
        net = recovered - cost

        # Recovery time estimate (would be real in production)
        recovery_time = 5.0 if action_taken == "RETRY_PAYMENT" else 30.0

        # Expected vs actual ratio
        expected_nev = float(opportunity.get("net_expected_value", 0)) if opportunity else 0.0
        ratio = (net / expected_nev) if expected_nev > 0 else 0.0

        return OutcomeRecord(
            status=status,
            recovered_amount=round(recovered, 2),
            recovery_cost=round(cost, 2),
            net_recovered=round(net, 2),
            recovery_time_seconds=recovery_time,
            strategy_used=action_taken,
            was_first_attempt=True,
            notes=f"Action: {action_taken}. Tool success: {success}. Status: {status.value}.",
            expected_vs_actual_ratio=round(ratio, 3),
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, OutcomeRecord)
        return {
            "outcome_record": output.model_dump(),
            "outcome_status": output.status.value,
            "recovered_amount": output.recovered_amount,
        }
