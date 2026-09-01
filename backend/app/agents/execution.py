"""
RECOVERX AI — Agent 8: Recovery Execution
The ONLY agent allowed to call tools. All actions go through Policy Guardian first.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import ExecutionResult, StrategyType, ToolCall


class ExecutionAgent(BaseAgent):
    """
    Recovery Execution Agent.
    The sole agent permitted to call payment, communication, and CRM tools.
    Receives Guardian-approved strategy and executes it via bounded tools.
    LLM is NOT used for tool selection — tool routing is deterministic.
    """

    @property
    def agent_name(self) -> str:
        return "recovery_execution"

    @property
    def system_prompt(self) -> str:
        # The Execution Agent doesn't use LLM for tool routing — fully deterministic
        return "Recovery Execution Agent — executes Guardian-approved strategies via bounded tools."

    async def _run_with_llm(self, state: dict[str, Any]) -> ExecutionResult:
        # Execution is always deterministic — LLM not used for tool routing
        # This prevents LLM hallucinations from causing unintended actions
        return await self._run_fallback(state)

    async def _run_fallback(self, state: dict[str, Any]) -> ExecutionResult:
        """
        Deterministic tool dispatch based on Guardian-approved strategy.
        All tool calls are simulated and bounded.
        """
        guardian = state.get("guardian_decision", {})
        event = state.get("event_data", {})
        profile = state.get("customer_profile", {})

        # Handle escalation case
        if guardian.get("escalate_to_human"):
            return await self._execute_escalation(state)

        # Handle stop recovery
        if guardian.get("stop_recovery"):
            return await self._execute_stop(state)

        selected_strategy = guardian.get("selected_strategy")
        if not selected_strategy:
            return ExecutionResult(
                action_taken="NO_ACTION",
                tool_called="none",
                success=False,
                result_data={"reason": "No approved strategy found"},
                timestamp=datetime.now(timezone.utc).isoformat(),
                error="Guardian did not select a strategy",
            )

        strategy_type = selected_strategy.get("strategy_type", "STOP_RECOVERY")
        parameters = selected_strategy.get("parameters", {})

        amount = float(event.get("amount", 0))
        payment_method = event.get("payment_method", "CARD")
        customer_id = profile.get("customer_id", event.get("customer_id", "unknown"))
        root_cause = state.get("root_cause", "UNKNOWN")
        fatigue = float(profile.get("fatigue_score", 0.0))
        case_id = state.get("case_id", "unknown")

        tool_calls = []
        result_data = {}
        success = False
        error = None

        try:
            if strategy_type == StrategyType.RETRY_PAYMENT.value:
                from app.tools.payment_tools import retry_payment
                result = await retry_payment(
                    case_id=case_id, amount=amount,
                    payment_method=payment_method, customer_id=customer_id,
                    root_cause=root_cause,
                )
                success = result.get("success", False)
                result_data = result
                tool_calls.append(ToolCall(
                    tool_name="retry_payment",
                    parameters={"amount": amount, "method": payment_method},
                    result=result,
                    success=success,
                ))

            elif strategy_type == StrategyType.RETRY_LATER.value:
                from app.tools.payment_tools import schedule_retry
                delay = float(parameters.get("delay_hours", 2.0))
                result = await schedule_retry(
                    case_id=case_id, amount=amount, payment_method=payment_method,
                    delay_hours=delay, customer_id=customer_id, root_cause=root_cause,
                )
                success = result.get("success", False)
                result_data = result
                tool_calls.append(ToolCall(
                    tool_name="schedule_retry",
                    parameters={"delay_hours": delay},
                    result=result,
                    success=success,
                ))

            elif strategy_type == StrategyType.GENERATE_PAYMENT_LINK.value:
                from app.tools.payment_tools import generate_payment_link
                result = await generate_payment_link(
                    case_id=case_id, amount=amount, customer_id=customer_id,
                    expiry_hours=int(parameters.get("expiry_hours", 48)),
                )
                success = result.get("simulated_payment_completed", False)
                result_data = result
                tool_calls.append(ToolCall(
                    tool_name="generate_payment_link",
                    parameters={"amount": amount, "expiry_hours": parameters.get("expiry_hours", 48)},
                    result=result,
                    success=success,
                ))

            elif strategy_type == StrategyType.SEND_WHATSAPP.value:
                from app.tools.comms_tools import send_whatsapp
                result = await send_whatsapp(
                    case_id=case_id, customer_id=customer_id,
                    template=parameters.get("template", "payment_reminder"),
                    params={"amount": amount},
                    fatigue_score=fatigue,
                )
                success = result.get("simulated_customer_responded", False)
                result_data = result
                tool_calls.append(ToolCall(
                    tool_name="send_whatsapp",
                    parameters={"template": parameters.get("template")},
                    result=result,
                    success=result.get("simulated_delivered", False),
                ))

            elif strategy_type == StrategyType.SEND_EMAIL.value:
                from app.tools.comms_tools import send_email
                result = await send_email(
                    case_id=case_id, customer_id=customer_id,
                    template=parameters.get("template", "payment_reminder_email"),
                    params={"amount": amount},
                    fatigue_score=fatigue,
                )
                success = result.get("simulated_clicked", False)
                result_data = result
                tool_calls.append(ToolCall(
                    tool_name="send_email",
                    parameters={"template": parameters.get("template")},
                    result=result,
                    success=result.get("simulated_delivered", False),
                ))

            elif strategy_type == StrategyType.OFFER_ALTERNATE_PAYMENT.value:
                from app.tools.payment_tools import generate_payment_link
                result = await generate_payment_link(
                    case_id=case_id, amount=amount, customer_id=customer_id, expiry_hours=48
                )
                success = result.get("simulated_payment_completed", False)
                result_data = {**result, "alternate_method_suggested": parameters.get("suggest", "UPI")}
                tool_calls.append(ToolCall(
                    tool_name="generate_payment_link",
                    parameters={"alternate_method": parameters.get("suggest")},
                    result=result,
                    success=success,
                ))

            elif strategy_type == StrategyType.SCHEDULE_FOLLOWUP.value:
                from app.tools.crm_tools import escalate_to_human
                result = await escalate_to_human(
                    case_id=case_id, reason="Scheduled follow-up", priority="LOW",
                    amount=amount, ai_confidence=0.7, ai_recommendation={"strategy": strategy_type},
                )
                success = True
                result_data = result

            elif strategy_type == StrategyType.ESCALATE_TO_HUMAN.value:
                return await self._execute_escalation(state)

            elif strategy_type == StrategyType.STOP_RECOVERY.value:
                return await self._execute_stop(state)

            else:
                return ExecutionResult(
                    action_taken="UNKNOWN_STRATEGY",
                    tool_called="none",
                    success=False,
                    result_data={},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    error=f"Unrecognised strategy: {strategy_type}",
                )

        except Exception as exc:
            error = f"Tool execution failed: {exc}"
            success = False

        return ExecutionResult(
            action_taken=strategy_type,
            tool_called=tool_calls[0].tool_name if tool_calls else "none",
            tool_calls=tool_calls,
            success=success,
            result_data=result_data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            error=error,
        )

    async def _execute_escalation(self, state: dict[str, Any]) -> ExecutionResult:
        from app.tools.crm_tools import escalate_to_human
        event = state.get("event_data", {})
        guardian = state.get("guardian_decision", {})
        sentinel = state.get("sentinel_output", {})

        result = await escalate_to_human(
            case_id=state.get("case_id", "unknown"),
            reason=guardian.get("block_reason", "Human review required"),
            priority="HIGH" if float(event.get("amount", 0)) > 50000 else "MEDIUM",
            amount=float(event.get("amount", 0)),
            ai_confidence=float(sentinel.get("confidence", 0.5)),
            ai_recommendation=state.get("guardian_decision", {}),
        )
        return ExecutionResult(
            action_taken="ESCALATE_TO_HUMAN",
            tool_called="escalate_to_human",
            success=True,
            result_data=result,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _execute_stop(self, state: dict[str, Any]) -> ExecutionResult:
        from app.tools.crm_tools import stop_recovery
        guardian = state.get("guardian_decision", {})
        result = await stop_recovery(
            case_id=state.get("case_id", "unknown"),
            reason=guardian.get("block_reason", "Policy blocked recovery"),
        )
        return ExecutionResult(
            action_taken="STOP_RECOVERY",
            tool_called="stop_recovery",
            success=True,
            result_data=result,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, ExecutionResult)
        return {"execution_result": output.model_dump()}
