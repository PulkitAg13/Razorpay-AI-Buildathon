import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, CheckCircle2, AlertCircle, Cpu, RefreshCw, Zap, Shield, Sparkles, Activity } from 'lucide-react';
import { agentsApi } from '../lib/api';
import type { AgentStatus } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const AGENT_DESCRIPTIONS: Record<string, { role: string; type: 'LLM' | 'DETERMINISTIC'; desc: string }> = {
  revenue_sentinel: {
    role: 'Triage & Priority Scoring',
    type: 'DETERMINISTIC',
    desc: 'First responder. Evaluates initial recoverability and enforces hard DO_NOT_CONTACT gates.',
  },
  root_cause_diagnosis: {
    role: 'Failure Evidence Analysis',
    type: 'LLM',
    desc: 'Synthesizes gateway error codes, payment history, and temporal patterns to diagnose root cause.',
  },
  customer_context_intelligence: {
    role: 'Fatigue & Channel Intelligence',
    type: 'LLM',
    desc: 'Evaluates customer fatigue score, engagement streak, and optimal communication channel.',
  },
  recovery_opportunity: {
    role: 'Economic Value Engine',
    type: 'DETERMINISTIC',
    desc: 'Computes Expected Recovery Value (ERV) and Net Expected Value (NEV = Amount × P - Cost - Friction).',
  },
  recovery_strategy_planner: {
    role: 'Strategy Candidate Generator',
    type: 'LLM',
    desc: 'Generates 3-5 ranked candidate strategies with parameter optimizations.',
  },
  recovery_digital_twin: {
    role: 'Counterfactual Simulation Engine',
    type: 'DETERMINISTIC',
    desc: 'Runs mathematical simulations of all candidate strategies to rank by highest Net Expected Value.',
  },
  compliance_policy_guardian: {
    role: 'Policy Gatekeeper',
    type: 'DETERMINISTIC',
    desc: 'Enforces 8 strict policy rules (max retries, contact hours, cost limits). Sole agent that can BLOCK.',
  },
  recovery_execution: {
    role: 'Sole Tool Caller',
    type: 'DETERMINISTIC',
    desc: 'Dispatches bounded tools (retry_payment, schedule_retry, payment_links, WhatsApp, Email).',
  },
  outcome_monitor: {
    role: 'Outcome Verification & Recording',
    type: 'DETERMINISTIC',
    desc: 'Monitors tool execution results, records actual recovered revenue, and calculates NEV ratios.',
  },
  learning_optimization: {
    role: 'Continuous Policy Tuning',
    type: 'DETERMINISTIC',
    desc: 'Updates StrategyEffectiveness historical performance matrices for future digital twin accuracy.',
  },
};

const PIPELINE_ORDER = [
  'revenue_sentinel', 'root_cause_diagnosis', 'customer_context_intelligence',
  'recovery_opportunity', 'recovery_strategy_planner', 'recovery_digital_twin',
  'compliance_policy_guardian', 'recovery_execution', 'outcome_monitor', 'learning_optimization',
];

export default function AgentObservatory() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [llmProvider, setLlmProvider] = useState('');
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const loadMetrics = async () => {
    try {
      const r = await agentsApi.getStatus();
      setAgents(r.agents);
      setLlmProvider(r.llm_provider);
      setTotal(r.total_invocations);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    loadMetrics();
    const t = setInterval(loadMetrics, 6000);
    return () => clearInterval(t);
  }, []);

  const sortedAgents = [...agents].sort((a, b) =>
    PIPELINE_ORDER.indexOf(a.agent_name) - PIPELINE_ORDER.indexOf(b.agent_name)
  );

  const totalFallbacks = agents.reduce((acc, a) => acc + (a.fallback_count || 0), 0);
  const totalErrors = agents.reduce((acc, a) => acc + (a.error_count || 0), 0);

  const chartData = sortedAgents.map(a => ({
    name: a.display_name.replace('Recovery ', '').replace('Root Cause ', '').replace('Compliance ', ''),
    invocations: a.total_invocations,
    avgMs: Math.round(a.avg_duration_ms),
    fallbacks: a.fallback_count,
  }));

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bot className="text-primary" size={24} />
            Agent Observatory
          </h1>
          <p className="text-muted text-sm mt-0.5">
            Real-time telemetry, execution throughput, and health metrics across all 10 specialized agents
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="badge bg-primary/20 text-primary-light border border-primary/30 flex items-center gap-1.5 py-1 px-3">
            <Cpu size={13} />
            <span>{llmProvider || 'Gemini'}</span>
          </div>
          <button
            onClick={loadMetrics}
            className="btn-ghost text-xs flex items-center gap-1 hover:text-white"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Summary Telemetry KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass-card p-4">
          <div className="text-xs text-muted">Total Agent Invocations</div>
          <div className="text-2xl font-bold text-white font-mono mt-1">{total}</div>
          <div className="text-[11px] text-emerald-400 mt-0.5">Across 10 pipeline steps</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-xs text-muted">LLM-Enabled Agents</div>
          <div className="text-2xl font-bold text-primary-light font-mono mt-1">3 / 10</div>
          <div className="text-[11px] text-muted mt-0.5">Diagnosis, Context, Strategy</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-xs text-muted">Deterministic Agents</div>
          <div className="text-2xl font-bold text-indigo-300 font-mono mt-1">7 / 10</div>
          <div className="text-[11px] text-muted mt-0.5">Math, Twin, Policy, Execution</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-xs text-muted">Circuit Breaker Fallbacks</div>
          <div className={`text-2xl font-bold font-mono mt-1 ${totalFallbacks > 0 ? 'text-amber-400' : 'text-slate-300'}`}>
            {totalFallbacks}
          </div>
          <div className="text-[11px] text-muted mt-0.5">Deterministic fallback routed</div>
        </div>
      </div>

      {/* 10-Agent Pipeline Visualization */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-white flex items-center gap-1.5">
            <Activity size={14} className="text-primary" />
            10-Agent LangGraph Pipeline Architecture
          </div>
          <div className="text-xs text-muted">Sequential execution flow with conditional early-exit routing</div>
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-2">
          {sortedAgents.map((agent, i) => {
            const meta = AGENT_DESCRIPTIONS[agent.agent_name];
            const isLLM = meta?.type === 'LLM';
            const hasRuns = agent.total_invocations > 0;

            return (
              <div key={agent.agent_name} className="flex items-center gap-1.5 shrink-0">
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className={`w-28 p-2.5 rounded-lg border text-center transition-all ${
                    hasRuns
                      ? 'border-primary/40 bg-primary/10 shadow-sm'
                      : 'border-bg-border bg-bg-card/50 opacity-80'
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center mx-auto mb-1.5 ${
                      hasRuns ? 'bg-primary/20 text-primary' : 'bg-subtle text-muted'
                    }`}
                  >
                    <Bot size={14} />
                  </div>
                  <div className="text-[11px] font-bold text-white leading-tight truncate">
                    {agent.display_name.replace('Recovery ', '').replace('Root Cause ', '').replace('Compliance ', '')}
                  </div>
                  <div className="text-[9px] text-muted mt-0.5">
                    {isLLM ? '🤖 LLM' : '⚙️ Math/Rule'}
                  </div>
                  <div className="text-[10px] text-emerald-400 font-mono mt-1">
                    {agent.total_invocations} runs
                  </div>
                </motion.div>
                {i < sortedAgents.length - 1 && (
                  <div className="text-muted/60 text-xs">→</div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Detailed Agent Cards Grid */}
      <div className="grid grid-cols-2 gap-4">
        {sortedAgents.map((agent, i) => {
          const meta = AGENT_DESCRIPTIONS[agent.agent_name];
          const isLLM = meta?.type === 'LLM';

          return (
            <motion.div
              key={agent.agent_name}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.02 }}
              className="glass-card p-4 space-y-3 hover:border-primary/40 transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                    <Bot size={16} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-white flex items-center gap-2">
                      <span>{agent.display_name}</span>
                      <span className="text-[10px] text-muted font-mono">#{i + 1}</span>
                    </div>
                    <div className="text-xs text-primary-light font-medium">{meta?.role}</div>
                  </div>
                </div>
                <span
                  className={`badge text-[10px] ${
                    isLLM
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                      : 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30'
                  }`}
                >
                  {isLLM ? '🤖 LLM Agent' : '⚙️ Deterministic'}
                </span>
              </div>

              <div className="text-xs text-muted leading-relaxed">
                {meta?.desc}
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-4 gap-2 text-center text-xs pt-1">
                <div className="glass-card p-2 bg-bg-card/50">
                  <div className="font-bold text-white font-mono">{agent.total_invocations}</div>
                  <div className="text-[10px] text-muted">Runs</div>
                </div>
                <div className="glass-card p-2 bg-bg-card/50">
                  <div className="font-bold text-primary-light font-mono">{Math.round(agent.avg_duration_ms)}ms</div>
                  <div className="text-[10px] text-muted">Avg Latency</div>
                </div>
                <div className="glass-card p-2 bg-bg-card/50">
                  <div className="font-bold text-emerald-400 font-mono">{agent.success_rate.toFixed(0)}%</div>
                  <div className="text-[10px] text-muted">Success</div>
                </div>
                <div className="glass-card p-2 bg-bg-card/50">
                  <div className={`font-bold font-mono ${agent.fallback_count > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                    {agent.fallback_count}
                  </div>
                  <div className="text-[10px] text-muted">Fallbacks</div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Chart: Invocations & Latency */}
      {total > 0 && (
        <div className="glass-card p-5">
          <div className="text-sm font-semibold text-white mb-4">Invocations per Agent</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2230" />
              <XAxis dataKey="name" stroke="#94A3B8" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={50} />
              <YAxis stroke="#94A3B8" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#12141A', border: '1px solid #1E2230', borderRadius: 8 }} />
              <Bar dataKey="invocations" name="Invocations" fill="#6366F1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
