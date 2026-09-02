import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FlaskConical, Play, Loader2, TrendingUp, Bot, CheckCircle2, XCircle, AlertTriangle, ShieldCheck, ArrowRight, Sparkles, ExternalLink, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { casesApi, simulationApi } from '../lib/api';
import { useAppStore } from '../store';
import type { LiveEvent } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const fmt = (n: number) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const EVENT_TYPES = ['PAYMENT_FAILURE', 'CHECKOUT_ABANDONMENT', 'SUBSCRIPTION_FAILURE', 'INVOICE_OVERDUE'];
const FAILURE_REASONS = ['BANK_DECLINE', 'INSUFFICIENT_FUNDS', 'CARD_EXPIRED', 'UPI_TIMEOUT', 'CUSTOMER_ABANDONED', 'TECHNICAL_ERROR'];
const PAYMENT_METHODS = ['UPI', 'CARD', 'NETBANKING', 'WALLET', 'BANK_TRANSFER'];
const TIERS = ['STANDARD', 'PREMIUM', 'NEW', 'B2B'];

const PRESET_SCENARIOS = [
  {
    id: 'bank_decline',
    title: 'Bank Decline (Auto Recovered)',
    badge: 'Standard Recovery',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    desc: 'Temporary bank failure for standard customer. Pipeline detects high recovery potential and recovers automatically.',
    expected: 'RECOVERED (₹5,000)',
    data: {
      amount: 5000,
      event_type: 'PAYMENT_FAILURE',
      failure_reason: 'BANK_DECLINE',
      payment_method: 'UPI',
      customer_tier: 'STANDARD',
      contact_count_7d: 0,
      previous_recovery_attempts: 0,
    },
  },
  {
    id: 'opt_out',
    title: 'Customer Opt-Out (Policy Blocked)',
    badge: 'Policy Guardian Block',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    desc: 'Customer reached maximum allowed contact attempts (5 contacts). Policy Guardian strictly BLOCKS communication.',
    expected: 'STOPPED by Policy Guardian',
    data: {
      amount: 8500,
      event_type: 'PAYMENT_FAILURE',
      failure_reason: 'CARD_EXPIRED',
      payment_method: 'CARD',
      customer_tier: 'STANDARD',
      contact_count_7d: 5,
      previous_recovery_attempts: 5,
    },
  },
  {
    id: 'high_value',
    title: 'High-Value (Human Escalation)',
    badge: 'Human Review Queue',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    desc: 'Transaction exceeds ₹1,00,000 threshold. Policy Guardian routes case directly to Human Review Queue for approval.',
    expected: 'ESCALATED to Review Queue',
    data: {
      amount: 150000,
      event_type: 'PAYMENT_FAILURE',
      failure_reason: 'BANK_DECLINE',
      payment_method: 'CARD',
      customer_tier: 'PREMIUM',
      contact_count_7d: 0,
      previous_recovery_attempts: 0,
    },
  },
  {
    id: 'insufficient_funds',
    title: 'Insufficient Funds (Scheduled Follow-up)',
    badge: 'Scheduled Action',
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    desc: 'Low initial probability. Pipeline schedules a delayed follow-up or smart reminder for optimal timing.',
    expected: 'PENDING / SCHEDULED',
    data: {
      amount: 12000,
      event_type: 'PAYMENT_FAILURE',
      failure_reason: 'INSUFFICIENT_FUNDS',
      payment_method: 'UPI',
      customer_tier: 'STANDARD',
      contact_count_7d: 1,
      previous_recovery_attempts: 1,
    },
  },
];

const PIPELINE_AGENTS = [
  { name: 'Revenue Sentinel', key: 'revenue_sentinel', desc: 'Classify recoverability & priority' },
  { name: 'Root Cause Diagnosis', key: 'root_cause_diagnosis', desc: 'Identify root failure cause' },
  { name: 'Customer Context Intel', key: 'customer_context_intelligence', desc: 'Compute fatigue & profile' },
  { name: 'Recovery Opportunity', key: 'recovery_opportunity', desc: 'Calculate ERV & NEV math' },
  { name: 'Strategy Planner', key: 'recovery_strategy_planner', desc: 'Generate candidate strategies' },
  { name: 'Recovery Digital Twin', key: 'recovery_digital_twin', desc: 'Simulate counterfactuals' },
  { name: 'Policy Guardian', key: 'compliance_policy_guardian', desc: 'Enforce 8 policy rules' },
  { name: 'Recovery Execution', key: 'recovery_execution', desc: 'Bounded tool execution' },
  { name: 'Outcome Monitor', key: 'outcome_monitor', desc: 'Record recovery result' },
  { name: 'Learning & Optimization', key: 'learning_optimization', desc: 'Update strategy weights' },
];

export default function SimulationLab() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    amount: 5000, event_type: 'PAYMENT_FAILURE', failure_reason: 'BANK_DECLINE',
    payment_method: 'UPI', customer_tier: 'STANDARD', contact_count_7d: 0, previous_recovery_attempts: 0,
  });
  const [singleResult, setSingleResult] = useState<Record<string, unknown> | null>(null);
  const [runningCase, setRunningCase] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(-1);
  const [batchN, setBatchN] = useState(100);
  const { simulationRunning, setSimulationRunning, simulationProgress, simulationResults, setSimulationResults } = useAppStore();
  const [batchMode, setBatchMode] = useState<string>('SIMULATION_MODE');

  const applyPreset = (preset: typeof PRESET_SCENARIOS[0]) => {
    setForm(preset.data);
    setSingleResult(null);
  };

  const runSingle = async () => {
    setRunningCase(true);
    setSingleResult(null);
    setActiveStepIndex(0);

    // Animate through 10 pipeline steps smoothly while backend executes
    const stepInterval = setInterval(() => {
      setActiveStepIndex(prev => {
        if (prev < 9) return prev + 1;
        return prev;
      });
    }, 180);

    try {
      const r = await casesApi.simulate(form);
      clearInterval(stepInterval);
      setActiveStepIndex(10);
      setSingleResult(r);
    } catch (e: unknown) {
      clearInterval(stepInterval);
      setSingleResult({ error: String(e) });
    }
    setRunningCase(false);
  };

  const runBatch = async () => {
    setSimulationRunning(true);
    try {
      await simulationApi.runBatch(batchN, 42, batchMode);
      // Poll for results
      const poll = setInterval(async () => {
        const r = await simulationApi.getResults();
        if (!r.running && r.results) {
          setSimulationResults(r.results);
          setSimulationRunning(false);
          clearInterval(poll);
        }
      }, 1000);
    } catch { setSimulationRunning(false); }
  };

  const sr = simulationResults?.summary;
  const comparisonData = sr ? [
    { name: 'Recovered', recoverx: sr.recoverx_recovered, baseline: sr.baseline_recovered },
    { name: 'Net Value', recoverx: sr.recoverx_net, baseline: sr.baseline_net },
  ] : [];

  const stratData = simulationResults
    ? Object.entries(simulationResults.strategy_breakdown).map(([k, v]) => ({
        name: k.replace(/_/g, ' '),
        success: v.success,
        total: v.total,
        rate: v.total > 0 ? Math.round(v.success / v.total * 100) : 0,
      }))
    : [];

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FlaskConical className="text-primary" size={24} />
            Simulation Lab
          </h1>
          <p className="text-muted text-sm mt-0.5">
            Interactive Testbed: Trigger synthetic events through the 10-Agent LangGraph Pipeline
          </p>
        </div>
      </div>

      {/* Preset Demo Scenarios */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
            <Sparkles size={14} className="text-primary" />
            1-Click Demo Scenarios
          </div>
          <span className="text-xs text-muted/80">Click any scenario to instantly test different pipeline routing paths</span>
        </div>

        <div className="grid grid-cols-4 gap-3">
          {PRESET_SCENARIOS.map(preset => (
            <button
              key={preset.id}
              onClick={() => applyPreset(preset)}
              className="glass-card p-3 text-left hover:border-primary/50 transition-all hover:scale-[1.01] flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-1.5">
                  <span className={`badge text-[10px] px-2 py-0.5 border ${preset.badgeColor}`}>
                    {preset.badge}
                  </span>
                </div>
                <div className="text-xs font-bold text-white leading-tight">{preset.title}</div>
                <div className="text-[11px] text-muted mt-1 leading-snug">{preset.desc}</div>
              </div>
              <div className="mt-2 pt-2 border-t border-bg-border flex items-center justify-between text-[11px]">
                <span className="text-muted">Target:</span>
                <span className="font-medium text-primary-light">{preset.expected}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Custom Simulator + Batch Simulator */}
      <div className="grid grid-cols-2 gap-6">
        {/* Single Event Simulator */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FlaskConical size={16} className="text-primary" />
              <div className="text-sm font-semibold text-white">Custom Event Parameters</div>
            </div>
            <span className="text-xs text-muted">Configurable synthetic input</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            {[
              { label: 'Amount (₹)', type: 'number', key: 'amount' },
              { label: 'Contact Count (7d)', type: 'number', key: 'contact_count_7d' },
            ].map(({ label, type, key }) => (
              <div key={key}>
                <label className="text-xs text-muted block mb-1">{label}</label>
                <input
                  type={type}
                  className="w-full bg-bg border border-bg-border rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-primary/50 font-mono"
                  value={form[key as keyof typeof form]}
                  onChange={e => setForm(f => ({ ...f, [key]: type === 'number' ? Number(e.target.value) : e.target.value }))}
                />
              </div>
            ))}
            {[
              { label: 'Event Type', key: 'event_type', opts: EVENT_TYPES },
              { label: 'Failure Reason', key: 'failure_reason', opts: FAILURE_REASONS },
              { label: 'Payment Method', key: 'payment_method', opts: PAYMENT_METHODS },
              { label: 'Customer Tier', key: 'customer_tier', opts: TIERS },
            ].map(({ label, key, opts }) => (
              <div key={key}>
                <label className="text-xs text-muted block mb-1">{label}</label>
                <select
                  className="w-full bg-bg border border-bg-border rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-primary/50"
                  value={form[key as keyof typeof form] as string}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                >
                  {opts.map(o => <option key={o}>{o}</option>)}
                </select>
              </div>
            ))}
          </div>

          <button
            onClick={runSingle}
            disabled={runningCase}
            className="btn-primary w-full flex items-center justify-center gap-2 py-2.5 font-medium shadow-lg shadow-primary/20"
          >
            {runningCase ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Executing 10-Agent Pipeline...
              </>
            ) : (
              <>
                <Play size={16} />
                Run Recovery Pipeline (₹{form.amount.toLocaleString()})
              </>
            )}
          </button>

          {/* Pipeline Live Stepper */}
          {(runningCase || singleResult) && (
            <div className="glass-card p-4 space-y-3 bg-bg-card/50">
              <div className="flex items-center justify-between text-xs font-semibold text-white border-b border-bg-border pb-2">
                <span className="flex items-center gap-1.5">
                  <Bot size={14} className="text-primary" />
                  10-Agent Pipeline Execution Stepper
                </span>
                {runningCase ? (
                  <span className="text-primary-light flex items-center gap-1">
                    <Loader2 size={12} className="animate-spin" /> Running Step {Math.min(10, activeStepIndex + 1)}/10
                  </span>
                ) : (
                  <span className="text-success flex items-center gap-1">
                    <CheckCircle2 size={12} /> Pipeline Complete
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                {PIPELINE_AGENTS.map((ag, idx) => {
                  const isDone = activeStepIndex > idx || (singleResult && !runningCase);
                  const isCurrent = runningCase && activeStepIndex === idx;
                  return (
                    <div
                      key={ag.key}
                      className={`p-2 rounded-lg border transition-all flex items-center justify-between ${
                        isCurrent
                          ? 'border-primary bg-primary/10 shadow-sm'
                          : isDone
                          ? 'border-emerald-500/30 bg-emerald-500/5 text-slate-300'
                          : 'border-bg-border/60 text-muted/60 opacity-60'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 truncate">
                        {isDone ? (
                          <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
                        ) : isCurrent ? (
                          <Loader2 size={13} className="text-primary animate-spin shrink-0" />
                        ) : (
                          <div className="w-3 h-3 rounded-full border border-muted/40 shrink-0" />
                        )}
                        <span className="font-medium truncate">{ag.name}</span>
                      </div>
                      <span className="text-[10px] text-muted shrink-0 font-mono">#{idx + 1}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Pipeline Result Banner */}
          {singleResult && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-card p-4 space-y-3 border-primary/30"
            >
              {singleResult.error ? (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-rose-400">
                    <XCircle size={14} /> Pipeline Execution Error
                  </div>
                  <div>{String(singleResult.error)}</div>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                      <ShieldCheck size={14} className="text-success" />
                      Recovery Pipeline Result
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`badge text-xs ${
                          singleResult.status === 'RECOVERED' || singleResult.outcome_status === 'RECOVERED'
                            ? 'badge-success'
                            : singleResult.status === 'ESCALATED' || singleResult.human_escalation_required
                            ? 'badge-warning'
                            : singleResult.status === 'STOPPED' || singleResult.abort
                            ? 'badge-danger'
                            : 'badge-primary'
                        }`}
                      >
                        {String(singleResult.status || singleResult.outcome_status || 'COMPLETED')}
                      </span>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-between">
                    <div>
                      <div className="text-[10px] text-muted uppercase tracking-wider font-semibold">Generated Case Identifier</div>
                      <div className="text-sm font-mono font-bold text-white mt-0.5 select-all">
                        {String(singleResult.case_id || '—')}
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        if (singleResult.case_id) {
                          navigator.clipboard.writeText(String(singleResult.case_id));
                        }
                      }}
                      className="btn-ghost text-[11px] px-2.5 py-1 hover:text-white"
                      title="Copy Case ID"
                    >
                      Copy ID
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="glass-card p-2.5">
                      <div className="text-muted text-[11px]">Root Cause</div>
                      <div className="text-white font-medium truncate mt-0.5">
                        {String(singleResult.root_cause || '—').replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div className="glass-card p-2.5">
                      <div className="text-muted text-[11px]">Amount Recovered</div>
                      <div className="text-success font-bold mt-0.5">
                        {fmt(Number(singleResult.recovered_amount || 0))}
                      </div>
                    </div>
                    <div className="glass-card p-2.5">
                      <div className="text-muted text-[11px]">Strategy</div>
                      <div className="text-white font-medium truncate mt-0.5">
                        {String(singleResult.recommended_strategy || '—').replace(/_/g, ' ')}
                      </div>
                    </div>
                  </div>

                  {/* Action Links */}
                  <div className="flex items-center gap-2 pt-1">
                    <button
                      onClick={() => navigate('/cases', { state: { selectedCaseId: singleResult.case_id } })}
                      className="flex-1 btn-primary text-xs py-2 flex items-center justify-center gap-1.5 shadow-md shadow-primary/20"
                    >
                      <span>View in Case Explorer</span>
                      <ArrowRight size={13} />
                    </button>
                    <button
                      onClick={() => navigate('/audit')}
                      className="btn-ghost text-xs py-2 flex items-center justify-center gap-1 px-3"
                    >
                      <ExternalLink size={12} />
                      <span>Audit Logs</span>
                    </button>
                    {Boolean(singleResult.human_escalation_required || singleResult.status === 'ESCALATED') && (
                      <button
                        onClick={() => navigate('/human-review')}
                        className="btn-ghost text-xs py-2 bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center justify-center gap-1 px-3"
                      >
                        <span>Review Queue</span>
                      </button>
                    )}
                  </div>
                </>
              )}
            </motion.div>
          )}
        </div>

        {/* Batch Simulator */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-primary" />
              <div className="text-sm font-semibold text-white">Batch Simulation & Baseline Comparison</div>
            </div>
            <span className="text-xs text-muted">Benchmark engine</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted block mb-1">Events to simulate</label>
              <input
                type="number"
                min={10}
                max={1000}
                step={50}
                className="w-full bg-bg border border-bg-border rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-primary/50 font-mono"
                value={batchN}
                onChange={e => setBatchN(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">Execution Mode</label>
              <select
                className="w-full bg-bg border border-bg-border rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-primary/50"
                value={batchMode}
                onChange={e => setBatchMode(e.target.value)}
              >
                <option value="SIMULATION_MODE">Simulation Mode (0 Quota Deterministic)</option>
                <option value="HYBRID_MODE">Hybrid Mode (LLM on Edge Cases)</option>
                <option value="DEMO_AI_MODE">Demo AI Mode (Live Gemini)</option>
              </select>
            </div>
          </div>

          <button
            onClick={runBatch}
            disabled={simulationRunning}
            className="btn-primary w-full flex items-center justify-center gap-2 py-2.5 font-medium"
          >
            {simulationRunning ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Simulating... {simulationProgress.toFixed(0)}%
              </>
            ) : (
              <>
                <Play size={16} />
                Run Batch Benchmark ({batchN} Events)
              </>
            )}
          </button>

          {simulationRunning && (
            <div className="space-y-1.5">
              <div className="h-2 bg-subtle rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-300"
                  style={{ width: `${simulationProgress}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-muted">
                <span>Processing synthetic revenue events...</span>
                <span>{simulationProgress.toFixed(0)}%</span>
              </div>
            </div>
          )}

          {sr && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
              {/* Improvement banner */}
              <div
                className={`rounded-lg p-3.5 flex items-center justify-between ${
                  sr.improvement_pct >= 0 ? 'bg-success/10 border border-success/20' : 'bg-danger/10 border border-danger/20'
                }`}
              >
                <div>
                  <div className={`text-xl font-bold ${sr.improvement_pct >= 0 ? 'text-success' : 'text-danger'}`}>
                    {sr.improvement_pct >= 0 ? '+' : ''}
                    {sr.improvement_pct}%
                  </div>
                  <div className="text-xs text-muted">RECOVERX AI Net Recovery Lift vs Naive Baseline</div>
                </div>
                <div className="text-right">
                  <div className="text-base font-bold text-white">{fmt(sr.additional_value_recovered)}</div>
                  <div className="text-xs text-muted">incremental recovered value</div>
                </div>
              </div>

              {/* Comparison chart */}
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={comparisonData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E2230" horizontal={false} />
                  <XAxis
                    type="number"
                    stroke="#94A3B8"
                    tick={{ fontSize: 10 }}
                    tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`}
                  />
                  <YAxis type="category" dataKey="name" stroke="#94A3B8" tick={{ fontSize: 11 }} width={75} />
                  <Tooltip
                    contentStyle={{ background: '#12141A', border: '1px solid #1E2230', borderRadius: 8 }}
                    formatter={(v: number) => fmt(v)}
                  />
                  <Bar dataKey="recoverx" name="RECOVERX AI" fill="#6366F1" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="baseline" name="Naive Baseline" fill="#334155" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>

              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { label: 'RECOVERX AI Rate', value: `${sr.recoverx_recovery_rate_pct}%`, color: 'text-primary-light' },
                  { label: 'Baseline Rate', value: `${sr.baseline_recovery_rate_pct}%`, color: 'text-muted' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="glass-card p-2 text-center">
                    <div className={`font-bold text-sm ${color}`}>{value}</div>
                    <div className="text-muted text-[11px]">{label}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Strategy breakdown */}
      {stratData.length > 0 && (
        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold text-white">Strategy Effectiveness (Batch Simulation)</div>
            <div className="text-xs text-muted">Outcome distribution across recovery strategies</div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stratData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2230" />
              <XAxis dataKey="name" stroke="#94A3B8" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={50} />
              <YAxis stroke="#94A3B8" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#12141A', border: '1px solid #1E2230', borderRadius: 8 }} />
              <Bar dataKey="success" name="Success" fill="#10B981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="total" name="Total Attempts" fill="#1E2230" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
