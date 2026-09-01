// RECOVERX AI — Shared TypeScript types

export interface RecoveryCase {
  id: number;
  case_id: string;
  event_id: number;
  status: string;
  current_step: string;
  root_cause: string | null;
  selected_strategy: string | null;
  policy_approved: boolean;
  outcome_status: string | null;
  recovered_amount: number;
  recovery_cost: number;
  revenue_at_risk: number;
  expected_recovery_value: number;
  error_count: number;
  human_escalation_required: boolean;
  is_simulation: boolean;
  started_at: string;
  completed_at: string | null;
  sentinel_output?: Record<string, unknown>;
  diagnosis_output?: Record<string, unknown>;
  customer_profile?: Record<string, unknown>;
  opportunity_score?: Record<string, unknown>;
  candidate_strategies?: CandidateStrategy[];
  twin_predictions?: TwinPrediction[];
  guardian_decision?: Record<string, unknown>;
  execution_result?: Record<string, unknown>;
  audit_logs?: AuditLog[];
  outcome?: Outcome;
}

export interface Outcome {
  id: number;
  case_id: string;
  status: 'RECOVERED' | 'NOT_RECOVERED' | 'PENDING' | 'ESCALATED' | 'STOPPED';
  recovered_amount: number;
  recovery_cost: number;
  net_recovered: number;
  recovery_time_seconds: number;
  strategy_used: string;
  created_at: string;
}

export interface AuditLog {
  id: number;
  case_id: string;
  agent_name: string;
  step_index: number;
  decision: string;
  reasoning: string;
  confidence: number;
  decision_source?: string;
  llm_provider?: string;
  llm_model?: string;
  llm_used: boolean;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  tool_calls: ToolCall[];
  policy_checks: PolicyCheck[];
  had_error: boolean;
  error_message: string | null;
  used_fallback: boolean;
  duration_ms: number;
  timestamp: string;
}

export interface CandidateStrategy {
  strategy_type: string;
  parameters: Record<string, unknown>;
  estimated_success_rate: number;
  estimated_cost: number;
  reasoning: string;
  rank: number;
}

export interface TwinPrediction {
  strategy_type: string;
  strategy_rank: number;
  predicted_recovery_probability: number;
  expected_revenue: number;
  estimated_cost: number;
  customer_friction: number;
  compliance_risk: number;
  confidence: number;
  net_expected_value: number;
  simulation_notes: string;
}

export interface ToolCall {
  tool_name: string;
  parameters: Record<string, unknown>;
  result: Record<string, unknown>;
  success: boolean;
  error: string | null;
  duration_ms: number;
}

export interface PolicyCheck {
  rule_name: string;
  passed: boolean;
  details: string;
  severity: 'INFO' | 'WARNING' | 'VIOLATION' | 'BLOCK';
}

export interface DashboardMetrics {
  total_revenue_at_risk: number;
  total_recovered: number;
  recovery_rate_pct: number;
  net_recovered: number;
  total_cases: number;
  recovered_cases: number;
  active_cases: number;
  escalated_cases: number;
  stopped_cases: number;
  total_recovery_cost: number;
  avg_recovery_time_seconds: number;
  policy_approved_count: number;
  policy_violations_prevented: number;
  recent_cases: RecoveryCase[];
  disclaimer: string;
}

export interface AgentStatus {
  agent_name: string;
  display_name: string;
  total_invocations: number;
  error_count: number;
  fallback_count: number;
  success_rate: number;
  avg_duration_ms: number;
  status: 'ACTIVE' | 'IDLE' | 'ERROR';
}

export interface HumanReview {
  id: number;
  case_id: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'MODIFIED';
  escalation_reason: string;
  escalation_priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  ai_recommendation: Record<string, unknown>;
  reasoning_summary: string;
  candidate_strategies: CandidateStrategy[];
  twin_predictions: TwinPrediction[];
  policy_checks: PolicyCheck[];
  amount_at_risk: number;
  ai_confidence: number;
  reviewer_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface LiveEvent {
  type: 'case_created' | 'agent_step' | 'case_resolved' | 'simulation_progress' | 'simulation_complete';
  case_id?: string;
  agent?: string;
  decision?: string;
  outcome?: string;
  recovered_amount?: number;
  amount?: number;
  event_type?: string;
  duration_ms?: number;
  confidence?: number;
  timestamp?: string;
  _ts?: number;
}

export interface SimulationResult {
  summary: {
    total_events: number;
    total_revenue_at_risk: number;
    recoverx_recovered: number;
    recoverx_cost: number;
    recoverx_net: number;
    recoverx_recovery_rate_pct: number;
    baseline_recovered: number;
    baseline_cost: number;
    baseline_net: number;
    baseline_recovery_rate_pct: number;
    improvement_pct: number;
    additional_value_recovered: number;
  };
  by_event_type: Record<string, { total: number; recovered: number; at_risk: number }>;
  strategy_breakdown: Record<string, { success: number; total: number; recovered: number }>;
  disclaimer: string;
}
