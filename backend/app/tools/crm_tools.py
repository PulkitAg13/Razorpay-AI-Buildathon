"""
RECOVERX AI — CRM Tools (Simulated)
Human escalation and recovery stop actions.
Only the Recovery Execution Agent is permitted to call these.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def escalate_to_human(
    case_id: str,
    reason: str,
    priority: str,
    amount: float,
    ai_confidence: float,
    ai_recommendation: dict[str, Any],
) -> dict[str, Any]:
    """
    Escalate a recovery case to the human review queue.
    Creates a HumanReview record (handled in the Execution Agent).
    """
    logger.info(f"[TOOL:escalate_to_human] case={case_id} priority={priority}")
    return {
        "tool": "escalate_to_human",
        "success": True,
        "case_id": case_id,
        "escalated_to": "human_review_queue",
        "priority": priority,
        "reason": reason,
        "amount": amount,
        "ai_confidence": ai_confidence,
        "action_required": "Human reviewer must approve or reject recovery strategy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True,
    }


async def stop_recovery(
    case_id: str,
    reason: str,
    final_status: str = "NOT_RECOVERED",
) -> dict[str, Any]:
    """
    Permanently stop recovery attempts for this case.
    Reasons: customer opt-out, max attempts reached, not economically rational, policy block.
    """
    logger.info(f"[TOOL:stop_recovery] case={case_id} reason={reason}")
    return {
        "tool": "stop_recovery",
        "success": True,
        "case_id": case_id,
        "final_status": final_status,
        "reason": reason,
        "no_further_contact": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True,
    }
