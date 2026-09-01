"""RECOVERX AI — Mock LLM Provider (Deterministic Fallback)"""
from __future__ import annotations
import hashlib, random
from typing import Type, TypeVar
from pydantic import BaseModel
from app.llm.base import LLMProvider

T = TypeVar("T", bound=BaseModel)

# Complete enum patches — maps field name → valid default value
_ENUM_PATCHES = {
    "classification": "MEDIUM_RECOVERY_POTENTIAL",
    "root_cause": "TEMPORARY_BANK_FAILURE",
    "priority": "MEDIUM",
    "preferred_channel": "EMAIL",
    "contact_fatigue_level": "LOW",
    "status": "NOT_RECOVERED",
    "tier": "STANDARD",
    "strategy_type": "RETRY_LATER",
    "action_taken": "RETRY_LATER",
    "outcome_status": "NOT_RECOVERED",
    "escalation_priority": "MEDIUM",
    "amount_bucket": "MEDIUM",
}

# Field-name patterns that should be realistic float ranges
_FLOAT_RANGES = {
    "confidence": (0.70, 0.85),
    "recoverability": (0.50, 0.75),
    "recovery_probability": (0.55, 0.80),
    "predicted_recovery_probability": (0.55, 0.80),
    "fatigue_score": (0.05, 0.30),
    "payment_reliability": (0.65, 0.90),
    "historical_recovery_rate": (0.55, 0.80),
    "simulation_confidence": (0.65, 0.85),
    "confidence_weight": (0.10, 0.40),
    "ai_confidence": (0.65, 0.85),
    "success_rate": (0.60, 0.90),
    "customer_friction": (0.05, 0.20),
    "compliance_risk": (0.0, 0.10),
    "priority_score": (60.0, 85.0),
    "expected_recovery_value": (5000.0, 15000.0),
    "net_expected_value": (4000.0, 12000.0),
    "recovery_cost": (15.0, 50.0),
    "customer_friction_cost": (50.0, 200.0),
    "recovered_amount": (0.0, 0.0),  # stays 0 — set by execution
    "net_recovered": (0.0, 0.0),
    "recovery_time_seconds": (5.0, 30.0),
    "effectiveness_delta": (0.01, 0.03),
    "updated_success_rate": (0.60, 0.80),
}


class MockProvider(LLMProvider):
    """
    Deterministic mock LLM provider.
    Uses seeded random so the same prompt always produces the same plausible output.
    Full pipeline demo without any API key.
    """

    @property
    def provider_name(self) -> str:
        return "MockProvider"

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        temperature: float = 0.1,
    ) -> T:
        seed = int(hashlib.sha256((system_prompt + user_prompt).encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        field_values: dict = {}
        for field_name, field_info in schema.model_fields.items():
            annotation = str(field_info.annotation or "")
            default = field_info.default

            # Use schema default when available
            if default is not None and not str(default).startswith("PydanticUndefined"):
                field_values[field_name] = default
                continue

            # Enum patches first
            if field_name in _ENUM_PATCHES:
                field_values[field_name] = _ENUM_PATCHES[field_name]
                continue

            # Float fields with realistic ranges
            if field_name in _FLOAT_RANGES:
                lo, hi = _FLOAT_RANGES[field_name]
                field_values[field_name] = round(rng.uniform(lo, hi), 3)
                continue

            # Fallback by annotation type
            if "float" in annotation:
                field_values[field_name] = round(rng.uniform(0.40, 0.80), 3)
            elif "int" in annotation:
                field_values[field_name] = rng.randint(0, 5)
            elif "bool" in annotation:
                field_values[field_name] = True
            elif "list" in annotation:
                field_values[field_name] = []
            elif "str" in annotation:
                field_values[field_name] = f"mock_{field_name}"
            elif "dict" in annotation:
                field_values[field_name] = {}
            else:
                field_values[field_name] = None

        # Patch required string fields with meaningful content
        _string_patches = {
            "reasoning": "Mock reasoning: Deterministic analysis of payment failure patterns.",
            "economic_rationale": "Mock rationale: Expected recovery value exceeds recovery cost.",
            "planning_reasoning": "Mock planning: Generated strategies based on root cause analysis.",
            "simulation_notes": "Mock simulation: Probability model applied with contextual adjustments.",
            "historical_basis": "Synthetic simulation environment.",
            "notes": "Mock outcome recorded deterministically.",
            "customer_id": "CUST-MOCK-001",
            "customer_name": "Simulation Customer",
            "best_contact_time": "10:00-12:00",
            "strategy_key": "RETRY_LATER:TEMPORARY_BANK_FAILURE:STANDARD:UPI",
            "tool_called": "retry_payment",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "decision": "Proceed with recovery action based on analysis.",
            # Digital twin / planner string fields
            "recommended_strategy_type": "RETRY_LATER",
            "strategy_type": "RETRY_LATER",
            "action_taken": "RETRY_LATER",
            "updated_stats": "{}",
        }
        for k, v in _string_patches.items():
            if k in field_values and (field_values[k] is None or str(field_values[k]).startswith("mock_")):
                field_values[k] = v

        try:
            return schema.model_validate(field_values)
        except Exception:
            return schema.model_construct(**field_values)
