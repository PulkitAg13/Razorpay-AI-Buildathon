import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, CheckCircle2, AlertCircle, Cpu } from 'lucide-react';
import { agentsApi } from '../lib/api';
import type { AgentStatus } from '../types';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

const AGENT_DESCRIPTIONS: Record<string, string> = {
  revenue_sentinel: 'Monitors and classifies revenue events for recovery potential',
  root_cause_diagnosis: 'Identifies WHY revenue was lost with evidence-backed reasoning',
  customer_context_intelligence: 'Builds recovery profile and computes fatigue score',
  recovery_opportunity: 'Calculates Expected Recovery Value (ERV) and ROI',
  recovery_strategy_planner: 'Generates ranked candidate recovery strategies',
  recovery_digital_twin: 'Simulates outcomes for each candidate strategy',
  compliance_policy_guardian: 'Validates every action against 7 policy rules — can BLOCK',
  recovery_execution: 'The ONLY agent that calls tools — bounded execution',
  outcome_monitor: 'Records final recovery outcome and calculates metrics',
  learning_optimization: 'Updates strategy effectiveness for future predictions',
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

  useEffect(() => {
    const load = async () => {
      try {
        const r = await agentsApi.getStatus();
        setAgents(r.agents);
        setLlmProvider(r.llm_provider);
        setTotal(r.total_invocations);
      } catch {}
      setLoading(false);
    };
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const sortedAgents = [...agents].sort((a, b) =>
    PIPELINE_ORDER.indexOf(a.agent_name) - PIPELINE_ORDER.indexOf(b.agent_name)
  );

  const radarData = sortedAgents.slice(0, 6).map(a => ({
    agent: a.display_name.split(' ')[0],
    invocations: a.total_invocations,
    successRate: a.success_rate,
    avgDuration: Math.min(100, a.avg_duration_ms / 10),
  }));

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Observatory</h1>
          <p className="text-muted text-sm mt-0.5">Real-time health of all 10 specialized agents</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="badge badge-primary"><Cpu size={11} /> {llmProvider || 'Mock'} LLM</div>
          <div className="badge badge-muted">{total} total invocations</div>
        </div>
      </div>

      {/* Pipeline visualization */}
      <div className="glass-card p-5">
        <div className="text-sm font-semibold text-white mb-4">10-Agent Pipeline</div>
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {sortedAgents.map((agent, i) => (
            <div key={agent.agent_name} className="flex items-center gap-1 shrink-0">
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="agent-node w-28 text-center"
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center mx-auto ${
                  agent.total_invocations > 0 ? 'bg-primary/20' : 'bg-subtle'
                }`}>
                  <Bot size={16} className={agent.total_invocations > 0 ? 'text-primary' : 'text-muted'} />
                </div>
                <div className="text-xs font-medium text-white leading-tight mt-1">
                  {agent.display_name.replace('Recovery ', '').replace('Root Cause ', '')}
                </div>
                {agent.total_invocations > 0 && (
                  <div className="text-xs text-success">{agent.success_rate.toFixed(0)}%</div>
                )}
              </motion.div>
              {i < sortedAgents.length - 1 && (
                <div className="text-muted text-xs px-0.5">→</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Agent cards grid */}
      <div className="grid grid-cols-2 gap-4">
        {loading && <div className="col-span-2 text-center text-muted py-8">Loading agent metrics...</div>}
        {sortedAgents.map((agent, i) => (
          <motion.div
            key={agent.agent_name}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="glass-card p-4 hover:border-primary/30 transition-all"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                  agent.error_count > 0 ? 'bg-danger/20' : agent.total_invocations > 0 ? 'bg-primary/20' : 'bg-subtle'
                }`}>
                  {agent.error_count > 0 ? <AlertCircle size={14} className="text-danger" /> : <Bot size={14} className={agent.total_invocations > 0 ? 'text-primary' : 'text-muted'} />}
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{agent.display_name}</div>
                  <div className="text-xs text-muted mt-0.5">{`Step ${PIPELINE_ORDER.indexOf(agent.agent_name) + 1} / 10`}</div>
                </div>
              </div>
              <span className={`badge ${agent.status === 'ACTIVE' ? 'badge-success' : 'badge-muted'}`}>
                {agent.status}
              </span>
            </div>

            <div className="text-xs text-muted mb-3 leading-relaxed">
              {AGENT_DESCRIPTIONS[agent.agent_name] || ''}
            </div>

            <div className="grid grid-cols-4 gap-2 text-center">
              {[
                { label: 'Invocations', value: agent.total_invocations, color: 'text-white' },
                { label: 'Errors', value: agent.error_count, color: agent.error_count > 0 ? 'text-danger' : 'text-muted' },
                { label: 'Fallbacks', value: agent.fallback_count, color: 'text-warning' },
                { label: 'Avg ms', value: Math.round(agent.avg_duration_ms), color: 'text-primary-light' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-subtle rounded p-2">
                  <div className={`text-sm font-bold ${color}`}>{value}</div>
                  <div className="text-xs text-muted">{label}</div>
                </div>
              ))}
            </div>

            {agent.total_invocations > 0 && (
              <div className="mt-3">
                <div className="flex justify-between text-xs text-muted mb-1">
                  <span>Success Rate</span>
                  <span>{agent.success_rate.toFixed(1)}%</span>
                </div>
                <div className="h-1.5 bg-subtle rounded-full overflow-hidden">
                  <div
                    className="h-full bg-success rounded-full transition-all"
                    style={{ width: `${agent.success_rate}%` }}
                  />
                </div>
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Bar chart */}
      {agents.some(a => a.total_invocations > 0) && (
        <div className="glass-card p-5">
          <div className="text-sm font-semibold text-white mb-4">Invocations by Agent</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sortedAgents}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2230" />
              <XAxis dataKey="display_name" stroke="#94A3B8" tick={{ fontSize: 9 }} angle={-30} textAnchor="end" height={60} />
              <YAxis stroke="#94A3B8" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#12141A', border: '1px solid #1E2230', borderRadius: 8 }} />
              <Bar dataKey="total_invocations" name="Invocations" fill="#6366F1" radius={[4, 4, 0, 0]} />
              <Bar dataKey="error_count" name="Errors" fill="#EF4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
