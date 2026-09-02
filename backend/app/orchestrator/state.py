"""
RECOVERX AI — LangGraph Workflow State
TypedDict that flows through the entire recovery pipeline.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class RecoveryWorkflowState(TypedDict, total=False):
    """
    Complete state for the RECOVERX AI recovery workflow.
    Each agent reads from and writes to this shared state.
    """

    # ── Input ─────────────────────────────────────────────────────────────────
    case_id: str
    event_id: str
    event_data: dict[str, Any]        # Raw revenue event dict
    customer_raw: dict[str, Any]      # Raw customer dict from DB

    # ── Agent Outputs ─────────────────────────────────────────────────────────
    sentinel_output: Optional[dict[str, Any]]
    diagnosis_output: Optional[dict[str, Any]]
    customer_profile: Optional[dict[str, Any]]
    opportunity_score: Optional[dict[str, Any]]
    candidate_strategies: Optional[list[dict[str, Any]]]
    strategy_planner_output: Optional[dict[str, Any]]
    twin_predictions: Optional[list[dict[str, Any]]]
    digital_twin_output: Optional[dict[str, Any]]
    guardian_decision: Optional[dict[str, Any]]
    execution_result: Optional[dict[str, Any]]
    outcome_record: Optional[dict[str, Any]]
    learning_update: Optional[dict[str, Any]]

    # ── Summary Fields ────────────────────────────────────────────────────────
    status: Optional[str]
    root_cause: Optional[str]
    recommended_strategy: Optional[str]
    policy_approved: bool
    human_escalation_required: bool
    outcome_status: Optional[str]
    recovered_amount: float
    audit_entries: Optional[list[dict[str, Any]]]

    # ── Control Flow ──────────────────────────────────────────────────────────
    current_step: str
    error_count: int
    errors: list[str]
    abort: bool
    abort_reason: Optional[str]
