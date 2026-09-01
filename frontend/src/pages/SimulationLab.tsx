import { useState } from 'react';
import { motion } from 'framer-motion';
import { FlaskConical, Play, Loader2, TrendingUp, ArrowUpRight } from 'lucide-react';
import { casesApi, simulationApi } from '../lib/api';
import { useAppStore } from '../store';
import type { SimulationResult } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const fmt = (n: number) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const EVENT_TYPES = ['PAYMENT_FAILURE', 'CHECKOUT_ABANDONMENT', 'SUBSCRIPTION_FAILURE', 'INVOICE_OVERDUE'];
const FAILURE_REASONS = ['BANK_DECLINE', 'INSUFFICIENT_FUNDS', 'CARD_EXPIRED', 'UPI_TIMEOUT', 'CUSTOMER_ABANDONED', 'TECHNICAL_ERROR'];
const PAYMENT_METHODS = ['UPI', 'CARD', 'NETBANKING', 'WALLET', 'BANK_TRANSFER'];
const TIERS = ['STANDARD', 'PREMIUM', 'NEW', 'B2B'];

export default function SimulationLab() {
  const [form, setForm] = useState({
    amount: 5000, event_type: 'PAYMENT_FAILURE', failure_reason: 'BANK_DECLINE',
    payment_method: 'UPI', customer_tier: 'STANDARD', contact_count_7d: 0, previous_recovery_attempts: 0,
  });
  const [singleResult, setSingleResult] = useState<Record<string, unknown> | null>(null);
  const [runningCase, setRunningCase] = useState(false);
  const [batchN, setBatchN] = useState(100);
  const { simulationRunning, setSimulationRunning, simulationProgress, simulationResults, setSimulationResults } = useAppStore();

  const [batchMode, setBatchMode] = useState<string>('SIMULATION_MODE');

  const runSingle = async () => {
    setRunningCase(true);
    setSingleResult(null);
    try {
      const r = await casesApi.simulate(form);
      setSingleResult(r);
    } catch (e: unknown) { setSingleResult({ error: String(e) }); }
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
      <div>
        <h1 className="text-2xl font-bold text-white">Simulation Lab</h1>
        <p className="text-muted text-sm mt-0.5">Test the complete multi-agent pipeline with custom events</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Single Case Simulator */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <FlaskConical size={16} className="text-primary" />
            <div className="text-sm font-semibold text-white">Custom Event Simulator</div>
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
                  className="w-full bg-bg border border-bg-border rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-primary/50"
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
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {runningCase ? <><Loader2 size={14} className="animate-spin" />Running 10-Agent Pipeline...</> : <><Play size={14} />Run Recovery Pipeline</>}
          </button>

          {singleResult && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
              <div className="text-xs font-semibold text-white">Pipeline Result</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { label: 'Case ID', value: String(singleResult.case_id || '—') },
                  { label: 'Root Cause', value: String(singleResult.root_cause || '—').replace(/_/g, ' ') },
                  { label: 'Strategy', value: String(singleResult.recommended_strategy || '—').replace(/_/g, ' ') },
                  { label: 'Outcome', value: String(singleResult.outcome_status || singleResult.abort_reason || '—') },
                  { label: 'Recovered', value: fmt(Number(singleResult.recovered_amount || 0)) },
                  { label: 'Policy OK', value: String(singleResult.policy_approved || false) },
                ].map(({ label, value }) => (
                  <div key={label} className="glass-card p-2">
                    <div className="text-muted">{label}</div>
                    <div className="text-white font-medium truncate">{value}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>

        {/* Batch Simulator */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-primary" />
            <div className="text-sm font-semibold text-white">Batch Simulation & Baseline Comparison</div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted block mb-1">Events to simulate</label>
              <input
                type="number" min={10} max={1000} step={50}
                className="w-full bg-bg border border-bg-border rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-primary/50"
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
                <option value="SIMULATION_MODE">Simulation Mode (Deterministic)</option>
                <option value="HYBRID_MODE">Hybrid Mode (LLM on Edge Cases)</option>
                <option value="DEMO_AI_MODE">Demo AI Mode (Live Gemini)</option>
              </select>
            </div>
          </div>
          <button onClick={runBatch} disabled={simulationRunning} className="btn-primary w-full flex items-center justify-center gap-2">
            {simulationRunning ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            {simulationRunning ? `Running... ${simulationProgress.toFixed(0)}%` : `Run Batch Benchmark (${batchMode === 'SIMULATION_MODE' ? 'Fast' : 'AI'})`}
          </button>

          {simulationRunning && (
            <div className="space-y-1">
              <div className="h-2 bg-subtle rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${simulationProgress}%` }} />
              </div>
              <div className="text-xs text-muted text-right">{simulationProgress.toFixed(0)}%</div>
            </div>
          )}

          {sr && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
              {/* Improvement banner */}
              <div className={`rounded-lg p-3 flex items-center justify-between ${sr.improvement_pct >= 0 ? 'bg-success/10 border border-success/20' : 'bg-danger/10 border border-danger/20'}`}>
                <div>
                  <div className={`text-lg font-bold ${sr.improvement_pct >= 0 ? 'text-success' : 'text-danger'}`}>
                    {sr.improvement_pct >= 0 ? '+' : ''}{sr.improvement_pct}%
                  </div>
                  <div className="text-xs text-muted">RECOVERX AI vs Naive Baseline</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-white">{fmt(sr.additional_value_recovered)}</div>
                  <div className="text-xs text-muted">additional value</div>
                </div>
              </div>

              {/* Comparison chart */}
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={comparisonData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E2230" horizontal={false} />
                  <XAxis type="number" stroke="#94A3B8" tick={{ fontSize: 10 }} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
                  <YAxis type="category" dataKey="name" stroke="#94A3B8" tick={{ fontSize: 11 }} width={70} />
                  <Tooltip contentStyle={{ background: '#12141A', border: '1px solid #1E2230', borderRadius: 8 }} formatter={(v: number) => fmt(v)} />
                  <Bar dataKey="recoverx" name="RECOVERX AI" fill="#6366F1" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="baseline" name="Baseline" fill="#1E2230" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>

              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { label: 'RECOVERX Rate', value: `${sr.recoverx_recovery_rate_pct}%`, color: 'text-primary-light' },
                  { label: 'Baseline Rate', value: `${sr.baseline_recovery_rate_pct}%`, color: 'text-muted' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="glass-card p-2 text-center">
                    <div className={`font-bold text-sm ${color}`}>{value}</div>
                    <div className="text-muted">{label}</div>
                  </div>
                ))}
              </div>

              <div className="text-xs text-muted/60 text-center">
                ⚠ Synthetic simulation. Not actual payment results.
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Strategy breakdown */}
      {stratData.length > 0 && (
        <div className="glass-card p-5">
          <div className="text-sm font-semibold text-white mb-4">Strategy Effectiveness (Batch Simulation)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stratData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2230" />
              <XAxis dataKey="name" stroke="#94A3B8" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={50} />
              <YAxis stroke="#94A3B8" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#12141A', border: '1px solid #1E2230', borderRadius: 8 }} />
              <Bar dataKey="success" name="Success" fill="#10B981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="total" name="Total" fill="#1E2230" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
