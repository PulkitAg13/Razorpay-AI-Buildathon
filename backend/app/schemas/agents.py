"""
RECOVERX AI — Agent Pydantic Schemas
All inter-agent communication contracts. Validated by every agent.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────

class RecoverabilityClassification(str, Enum):
    HIGH_RECOVERY_POTENTIAL = "HIGH_RECOVERY_POTENTIAL"
    MEDIUM_RECOVERY_POTENTIAL = "MEDIUM_RECOVERY_POTENTIAL"
    LOW_RECOVERY_POTENTIAL = "LOW_RECOVERY_POTENTIAL"
    DO_NOT_CONTACT = "DO_NOT_CONTACT"
    ALREADY_RESOLVED = "ALREADY_RESOLVED"


class RootCause(str, Enum):
    TEMPORARY_BANK_FAILURE = "TEMPORARY_BANK_FAILURE"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    PAYMENT_METHOD_FAILURE = "PAYMENT_METHOD_FAILURE"
    CUSTOMER_ABANDONMENT = "CUSTOMER_ABANDONMENT"
    TECHNICAL_CHECKOUT_ISSUE = "TECHNICAL_CHECKOUT_ISSUE"
    SUBSCRIPTION_PAYMENT_FAILURE = "SUBSCRIPTION_PAYMENT_FAILURE"
    INVOICE_DELAY = "INVOICE_DELAY"
    UNKNOWN = "UNKNOWN"


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class StrategyType(str, Enum):
    RETRY_PAYMENT = "RETRY_PAYMENT"
    RETRY_LATER = "RETRY_LATER"
    GENERATE_PAYMENT_LINK = "GENERATE_PAYMENT_LINK"
    OFFER_ALTERNATE_PAYMENT = "OFFER_ALTERNATE_PAYMENT"
    SEND_WHATSAPP = "SEND_WHATSAPP"
    SEND_EMAIL = "SEND_EMAIL"
    SCHEDULE_FOLLOWUP = "SCHEDULE_FOLLOWUP"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    STOP_RECOVERY = "STOP_RECOVERY"


class CommunicationChannel(str, Enum):
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    CALL = "CALL"


class OutcomeStatus(str, Enum):
    RECOVERED = "RECOVERED"
    NOT_RECOVERED = "NOT_RECOVERED"
    PENDING = "PENDING"
    ESCALATED = "ESCALATED"
    STOPPED = "STOPPED"


# ── Agent 1: Revenue Sentinel ─────────────────────────────────────────────────

class SentinelOutput(BaseModel):
    classification: RecoverabilityClassification
    priority_score: float = Field(ge=0, le=100)
    revenue_at_risk: float
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    contact_allowed: bool = True
    flags: list[str] = Field(default_factory=list)


# ── Agent 2: Root Cause Diagnosis ─────────────────────────────────────────────

class DiagnosisOutput(BaseModel):
    root_cause: RootCause
    confidence: float = Field(ge=0.0, le=1.0)
    recoverability: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[str] = Field(default_factory=list)
    reasoning: str
    time_sensitive: bool = False
    recommended_window_hours: float = 24.0


# ── Agent 3: Customer Context Intelligence ────────────────────────────────────

class CustomerProfile(BaseModel):
    customer_id: str
    customer_name: str
    tier: str
    fatigue_score: float = Field(ge=0.0, le=1.0)
    preferred_channel: CommunicationChannel
    payment_reliability: float = Field(ge=0.0, le=1.0)
    historical_recovery_rate: float = Field(ge=0.0, le=1.0)
    last_successful_payment_days_ago: Optional[int] = None
    contact_count_7d: int = 0
    best_contact_time: str = "10:00-12:00"
    opt_out: bool = False
    lifetime_value: float = 0.0
    no_response_streak: int = 0
    contact_fatigue_level: str = "LOW"
    insights: list[str] = Field(default_factory=list)


# ── Agent 4: Recovery Opportunity ────────────────────────────────────────────

class OpportunityScore(BaseModel):
    recovery_probability: float = Field(ge=0.0, le=1.0)
    expected_recovery_value: float
    recovery_cost: float
    customer_friction_cost: float
    net_expected_value: float
    priority: Priority
    is_economically_rational: bool
    economic_rationale: str
    amount_bucket: str = "MEDIUM"


# ── Agent 5: Strategy Planner ─────────────────────────────────────────────────

class CandidateStrategy(BaseModel):
    strategy_type: StrategyType
    parameters: dict[str, Any] = Field(default_factory=dict)
    estimated_success_rate: float = Field(ge=0.0, le=1.0, default=0.70)
    estimated_cost: float = 0.0
    estimated_friction: float = Field(ge=0.0, le=1.0, default=0.1)
    reasoning: str = ""
    rank: int = 1
    is_automated: bool = True


class StrategyPlannerOutput(BaseModel):
    candidate_strategies: list[CandidateStrategy]
    planning_reasoning: str
    total_candidates: int
    constraints_applied: list[str] = Field(default_factory=list)


# ── Agent 6: Digital Twin ─────────────────────────────────────────────────────

class TwinPrediction(BaseModel):
    strategy_type: str
    strategy_rank: int = 1
    predicted_recovery_probability: float = 0.70
    expected_revenue: float = 0.0
    estimated_cost: float = 0.0
    customer_friction: float = 0.0
    compliance_risk: float = 0.0
    confidence: float = 0.80
    net_expected_value: float = 0.0
    simulation_notes: str = ""
    historical_basis: str = ""


class DigitalTwinOutput(BaseModel):
    predictions: list[TwinPrediction] = Field(default_factory=list)
    recommended_strategy_type: str = "RETRY_LATER"
    simulation_confidence: float = 0.80


# ── Agent 7: Policy Guardian ──────────────────────────────────────────────────

class PolicyCheck(BaseModel):
    rule_name: str
    passed: bool
    details: str
    severity: str = "INFO"


class GuardianDecision(BaseModel):
    approved: bool
    selected_strategy: Optional[CandidateStrategy] = None
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    policy_checks: list[PolicyCheck] = Field(default_factory=list)
    reasoning: str
    escalate_to_human: bool = False
    stop_recovery: bool = False
    block_reason: Optional[str] = None
    override_possible: bool = False


# ── Agent 8: Execution ────────────────────────────────────────────────────────

class ToolCall(BaseModel):
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    success: bool
    error: Optional[str] = None
    duration_ms: float = 0.0


class ExecutionResult(BaseModel):
    action_taken: str
    tool_called: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    success: bool
    result_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str
    error: Optional[str] = None


# ── Agent 9: Outcome Monitor ──────────────────────────────────────────────────

class OutcomeRecord(BaseModel):
    status: OutcomeStatus
    recovered_amount: float
    recovery_cost: float
    net_recovered: float
    recovery_time_seconds: float
    strategy_used: str
    was_first_attempt: bool = True
    notes: str = ""
    expected_vs_actual_ratio: float = 1.0


# ── Agent 10: Learning ────────────────────────────────────────────────────────

class LearningUpdate(BaseModel):
    strategy_key: str
    effectiveness_delta: float
    updated_success_rate: float
    updated_stats: dict[str, Any] = Field(default_factory=dict)
    insights: list[str] = Field(default_factory=list)
    model_updated: bool = True
