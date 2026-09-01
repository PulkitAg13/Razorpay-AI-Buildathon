"""
RECOVERX AI — Agent 7: Compliance & Policy Guardian
Validates every proposed action before execution. Can BLOCK actions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agents import CandidateStrategy, GuardianDecision, PolicyCheck, StrategyType


class PolicyGuardianAgent(BaseAgent):
    """
    Compliance & Policy Guardian Agent.
    The only agent that can BLOCK recovery execution.
    Every proposed action must pass this guardian before the Execution Agent runs.
    """

    @property
    def agent_name(self) -> str:
        return "compliance_policy_guardian"

    @property
    def system_prompt(self) -> str:
        return """You are the Compliance & Policy Guardian Agent for RECOVERX AI.

Your role: Validate that proposed recovery actions comply with all policies.
You MUST block any action that violates configured policies.

Policy Rules:
1. MAX_RETRIES: Payment retry count must not exceed configured limit
2. MAX_CONTACT_ATTEMPTS: Total contact attempts must not exceed configured limit
3. OPT_OUT: If customer opted out, ALL communication is BLOCKED
4. CONTACT_HOURS: No contact outside allowed contact hours (configurable)
5. COST_THRESHOLD: Recovery action cost must not exceed MAX_RECOVERY_COST_RATIO of transaction
6. HIGH_VALUE_APPROVAL: Transactions above threshold need human approval
7. MIN_CONFIDENCE: AI confidence below threshold requires human escalation
8. FATIGUE_GATE: High customer fatigue blocks automated communication

For each rule:
- Check if it passes or fails
- Report violation severity: INFO | WARNING | VIOLATION | BLOCK

Decision:
- approved: true → Execution Agent may proceed
- escalate_to_human: true → Route to human review queue
- stop_recovery: true → Permanently stop this case

Return GuardianDecision JSON."""

    async def _run_with_llm(self, state: dict[str, Any]) -> GuardianDecision:
        event = state.get("event_data", {})
        profile = state.get("customer_profile", {})
        strategies = state.get("candidate_strategies", [])
        twin_preds = state.get("twin_predictions", [])
        recommended = state.get("recommended_strategy", "")
        opportunity = state.get("opportunity_score", {})

        prompt = f"""Validate this proposed recovery action against all policies:

Transaction:
- Amount: ₹{event.get('amount', 0):,.2f}
- Event type: {event.get('event_type')}

Customer:
- Opt-out: {profile.get('opt_out', False)}
- Fatigue level: {profile.get('contact_fatigue_level', 'LOW')}
- Contact count 7d: {profile.get('contact_count_7d', 0)}

Recommended Strategy: {recommended}

Top Candidate Strategies:
{json.dumps(strategies[:3], indent=2)}

Digital Twin Best Prediction:
{json.dumps(twin_preds[0] if twin_preds else {}, indent=2)}

Opportunity:
- Net expected value: ₹{opportunity.get('net_expected_value', 0):,.0f}
- Priority: {opportunity.get('priority')}

Check all policy rules and return GuardianDecision JSON."""

        return await self._llm_generate(prompt, GuardianDecision)

    async def _run_fallback(self, state: dict[str, Any]) -> GuardianDecision:
        """Deterministic policy rule engine."""
        from app.config import get_settings
        settings = get_settings()

        event = state.get("event_data", {})
        profile = state.get("customer_profile", {})
        opportunity = state.get("opportunity_score", {})
        strategies = state.get("candidate_strategies", [])
        twin_preds = state.get("twin_predictions", [])
        sentinel = state.get("sentinel_output", {})

        amount = float(event.get("amount", 0))
        opt_out = bool(profile.get("opt_out", False))
        fatigue_level = profile.get("contact_fatigue_level", "LOW")
        fatigue_score = float(profile.get("fatigue_score", 0.0))
        contact_count = int(profile.get("contact_count_7d", 0))
        confidence = float(sentinel.get("confidence", 0.70))
        nev = float(opportunity.get("net_expected_value", 0))

        violations = []
        warnings = []
        checks = []
        block = False
        escalate = False

        # ── Rule 1: Opt-out ──────────────────────────────────────────────────
        passed = not opt_out
        checks.append(PolicyCheck(
            rule_name="customer_opt_out",
            passed=passed,
            details="Customer has not opted out" if passed else "BLOCKED: Customer opted out",
            severity="INFO" if passed else "BLOCK",
        ))
        if not passed:
            violations.append("Customer opt-out detected — all communication blocked")
            block = True

        # ── Rule 2: Max contact attempts ─────────────────────────────────────
        passed = contact_count < settings.max_contact_attempts
        checks.append(PolicyCheck(
            rule_name="max_contact_attempts",
            passed=passed,
            details=f"Contact count {contact_count}/{settings.max_contact_attempts}",
            severity="INFO" if passed else "BLOCK",
        ))
        if not passed:
            violations.append(f"Max contact attempts reached ({contact_count}/{settings.max_contact_attempts})")
            block = True

        # ── Rule 3: Contact hours ─────────────────────────────────────────────
        now_ist = (datetime.now(timezone.utc).hour + 5) % 24  # IST approx
        in_hours = settings.contact_hours_start <= now_ist < settings.contact_hours_end
        checks.append(PolicyCheck(
            rule_name="contact_hours",
            passed=in_hours,
            details=f"IST hour {now_ist:02d}:xx — allowed {settings.contact_hours_start}:00-{settings.contact_hours_end}:00",
            severity="INFO" if in_hours else "WARNING",
        ))
        if not in_hours:
            warnings.append(f"Outside contact hours — strategy should be SCHEDULE_FOLLOWUP or RETRY_LATER")

        # ── Rule 4: Cost threshold ────────────────────────────────────────────
        best_strategy = strategies[0] if strategies else {}
        estimated_cost = float(best_strategy.get("estimated_cost", 0))
        cost_ratio = estimated_cost / amount if amount > 0 else 0
        cost_ok = cost_ratio <= settings.max_recovery_cost_ratio
        checks.append(PolicyCheck(
            rule_name="recovery_cost_ratio",
            passed=cost_ok,
            details=f"Cost ratio {cost_ratio:.1%} vs max {settings.max_recovery_cost_ratio:.0%}",
            severity="INFO" if cost_ok else "VIOLATION",
        ))
        if not cost_ok:
            violations.append(f"Recovery cost {cost_ratio:.1%} exceeds threshold {settings.max_recovery_cost_ratio:.0%}")

        # ── Rule 5: High value threshold ──────────────────────────────────────
        needs_approval = amount > settings.human_approval_threshold
        checks.append(PolicyCheck(
            rule_name="high_value_approval",
            passed=not needs_approval,
            details=f"Amount ₹{amount:,.0f} vs threshold ₹{settings.human_approval_threshold:,.0f}",
            severity="INFO" if not needs_approval else "WARNING",
        ))
        if needs_approval:
            warnings.append(f"High-value transaction ₹{amount:,.0f} — human approval recommended")
            escalate = True

        # ── Rule 6: AI confidence ─────────────────────────────────────────────
        conf_ok = confidence >= settings.min_confidence_for_auto
        checks.append(PolicyCheck(
            rule_name="min_confidence",
            passed=conf_ok,
            details=f"AI confidence {confidence:.0%} vs min {settings.min_confidence_for_auto:.0%}",
            severity="INFO" if conf_ok else "WARNING",
        ))
        if not conf_ok:
            warnings.append(f"Low AI confidence {confidence:.0%} — human review recommended")
            escalate = True

        # ── Rule 7: Fatigue gate ──────────────────────────────────────────────
        fatigue_ok = fatigue_level not in ("CRITICAL",)
        checks.append(PolicyCheck(
            rule_name="customer_fatigue_gate",
            passed=fatigue_ok,
            details=f"Customer fatigue: {fatigue_level} (score={fatigue_score:.2f})",
            severity="INFO" if fatigue_ok else "VIOLATION",
        ))
        if not fatigue_ok:
            violations.append("Customer fatigue CRITICAL — automated contact blocked")
            block = True

        # ── Final decision ────────────────────────────────────────────────────
        approved = not block and len(violations) == 0
        stop = block and not escalate

        # Select best valid strategy
        selected = None
        if approved and strategies:
            try:
                selected = CandidateStrategy(**strategies[0])
            except Exception:
                pass

            # Override with scheduled strategy if outside hours
            if not in_hours and selected and selected.strategy_type.value not in ("RETRY_LATER", "SCHEDULE_FOLLOWUP", "STOP_RECOVERY", "ESCALATE_TO_HUMAN"):
                selected = CandidateStrategy(
                    strategy_type=StrategyType.RETRY_LATER,
                    parameters={"delay_hours": max(1, settings.contact_hours_start - now_ist)},
                    estimated_success_rate=0.60,
                    estimated_cost=15.0,
                    estimated_friction=0.05,
                    reasoning="Scheduled to comply with contact hours policy",
                    rank=1,
                )

        return GuardianDecision(
            approved=approved,
            selected_strategy=selected,
            violations=violations,
            warnings=warnings,
            policy_checks=checks,
            reasoning=(
                f"Policy check complete. {len(checks)} rules evaluated. "
                f"Violations: {len(violations)}. Warnings: {len(warnings)}. "
                f"Decision: {'APPROVED' if approved else 'ESCALATE' if escalate else 'BLOCKED'}."
            ),
            escalate_to_human=escalate and not block,
            stop_recovery=stop,
            block_reason=violations[0] if violations else None,
            override_possible=escalate and not block,
        )

    def _build_state_update(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(output, GuardianDecision)
        return {
            "guardian_decision": output.model_dump(),
            "policy_approved": output.approved,
            "human_escalation_required": output.escalate_to_human,
            "abort": output.stop_recovery or state.get("abort", False),
            "abort_reason": output.block_reason if output.stop_recovery else state.get("abort_reason"),
        }
