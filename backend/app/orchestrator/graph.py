"""
RECOVERX AI — LangGraph Workflow State Graph
Wires all 10 agents into a conditional workflow with policy-bounded execution.
Compatible with LangGraph 0.2.x and 1.x.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from app.agents import (
    ContextIntelligenceAgent,
    DiagnosisAgent,
    DigitalTwinAgent,
    ExecutionAgent,
    LearningAgent,
    OpportunityAgent,
    OutcomeMonitorAgent,
    PolicyGuardianAgent,
    SentinelAgent,
    StrategyPlannerAgent,
)
from app.orchestrator.state import RecoveryWorkflowState

logger = logging.getLogger(__name__)

# ── Agent singletons (shared across workflow runs) ────────────────────────────
_sentinel = SentinelAgent()
_diagnosis = DiagnosisAgent()
_context = ContextIntelligenceAgent()
_opportunity = OpportunityAgent()
_strategy = StrategyPlannerAgent()
_twin = DigitalTwinAgent()
_guardian = PolicyGuardianAgent()
_execution = ExecutionAgent()
_outcome = OutcomeMonitorAgent()
_learning = LearningAgent()

MAX_ERRORS = 3


# ── Node functions ────────────────────────────────────────────────────────────

async def run_sentinel(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _sentinel.run(state)


async def run_diagnosis(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _diagnosis.run(state)


async def run_context(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _context.run(state)


async def run_opportunity(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _opportunity.run(state)


async def run_strategy(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _strategy.run(state)


async def run_twin(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _twin.run(state)


async def run_guardian(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _guardian.run(state)


async def run_execution(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _execution.run(state)


async def run_outcome(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _outcome.run(state)


async def run_learning(state: RecoveryWorkflowState) -> dict[str, Any]:
    return await _learning.run(state)


async def run_escalation(state: RecoveryWorkflowState) -> dict[str, Any]:
    """Handle human escalation — create review queue entry."""
    logger.info(f"[Orchestrator] Routing case {state.get('case_id')} to human review queue.")
    return {
        "current_step": "human_escalation",
        "outcome_status": "ESCALATED",
        "human_escalation_required": True,
    }


# ── Routing functions ─────────────────────────────────────────────────────────

def route_after_sentinel(state: RecoveryWorkflowState) -> Literal["diagnosis", "end"]:
    if state.get("abort") or state.get("error_count", 0) >= MAX_ERRORS:
        return "end"
    return "diagnosis"


def route_after_context(state: RecoveryWorkflowState) -> Literal["opportunity", "end"]:
    if state.get("abort") or state.get("error_count", 0) >= MAX_ERRORS:
        return "end"
    return "opportunity"


def route_after_opportunity(state: RecoveryWorkflowState) -> Literal["strategy", "end"]:
    if state.get("abort") or state.get("error_count", 0) >= MAX_ERRORS:
        return "end"
    return "strategy"


def route_after_guardian(
    state: RecoveryWorkflowState,
) -> Literal["execution", "escalation", "end"]:
    if state.get("abort") or state.get("error_count", 0) >= MAX_ERRORS:
        return "end"

    guardian = state.get("guardian_decision", {})

    if guardian.get("escalate_to_human") and not guardian.get("stop_recovery"):
        return "escalation"

    if guardian.get("approved"):
        return "execution"

    return "end"


def route_after_execution(state: RecoveryWorkflowState) -> Literal["outcome", "end"]:
    if state.get("error_count", 0) >= MAX_ERRORS:
        return "end"
    return "outcome"


# ── Graph construction ────────────────────────────────────────────────────────

def build_recovery_graph() -> StateGraph:
    """
    Build and compile the RECOVERX AI recovery state graph.

    Graph topology:
    START → sentinel → diagnosis → context → opportunity → strategy
          → twin → guardian → execution → outcome → learning → END

    With conditional edges:
    - sentinel: DO_NOT_CONTACT/error → END
    - context: CRITICAL fatigue/opt-out → END
    - opportunity: NEV≤0 → END
    - guardian: approved → execution, escalate → human_queue, blocked → END
    """
    graph = StateGraph(RecoveryWorkflowState)

    # Add all nodes
    graph.add_node("sentinel", run_sentinel)
    graph.add_node("diagnosis", run_diagnosis)
    graph.add_node("context", run_context)
    graph.add_node("opportunity", run_opportunity)
    graph.add_node("strategy", run_strategy)
    graph.add_node("twin", run_twin)
    graph.add_node("guardian", run_guardian)
    graph.add_node("execution", run_execution)
    graph.add_node("outcome", run_outcome)
    graph.add_node("learning", run_learning)
    graph.add_node("escalation", run_escalation)

    # Entry point
    graph.add_edge(START, "sentinel")

    # Conditional edges
    graph.add_conditional_edges(
        "sentinel",
        route_after_sentinel,
        {"diagnosis": "diagnosis", "end": END},
    )

    graph.add_edge("diagnosis", "context")

    graph.add_conditional_edges(
        "context",
        route_after_context,
        {"opportunity": "opportunity", "end": END},
    )

    graph.add_conditional_edges(
        "opportunity",
        route_after_opportunity,
        {"strategy": "strategy", "end": END},
    )

    graph.add_edge("strategy", "twin")
    graph.add_edge("twin", "guardian")

    graph.add_conditional_edges(
        "guardian",
        route_after_guardian,
        {"execution": "execution", "escalation": "escalation", "end": END},
    )

    graph.add_conditional_edges(
        "execution",
        route_after_execution,
        {"outcome": "outcome", "end": END},
    )

    graph.add_edge("outcome", "learning")
    graph.add_edge("learning", END)
    graph.add_edge("escalation", END)

    return graph


# Compiled graph singleton
_compiled_graph = None


def get_compiled_graph():
    """Return the compiled LangGraph graph (lazy init)."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_recovery_graph()
        _compiled_graph = graph.compile()
    return _compiled_graph
