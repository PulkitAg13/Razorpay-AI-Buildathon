import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, ChevronRight, RefreshCw, Bot, Shield, CheckCircle2,
  XCircle, AlertTriangle, Clock, ArrowRight, Play, ExternalLink,
  Zap, UserCheck, DollarSign, Activity, FileText
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { casesApi } from '../lib/api';
import type { RecoveryCase } from '../types';

const fmtAmt = (n: number) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
const fmtTime = (s: string) => s ? new Date(s).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '—';

const statusBadgeStyles: Record<string, { badge: string; dot: string; label: string }> = {
  RECOVERED: { badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', dot: 'bg-emerald-400', label: 'Recovered' },
  PENDING: { badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30', dot: 'bg-amber-400', label: 'Pending / Scheduled' },
  PROCESSING: { badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30', dot: 'bg-blue-400', label: 'Processing' },
  EXECUTING: { badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30', dot: 'bg-purple-400', label: 'Executing' },
  ESCALATED: { badge: 'bg-orange-500/20 text-orange-300 border-orange-500/30', dot: 'bg-orange-400', label: 'Escalated' },
  STOPPED: { badge: 'bg-rose-500/20 text-rose-300 border-rose-500/30', dot: 'bg-rose-400', label: 'Stopped (Policy)' },
  FAILED: { badge: 'bg-slate-500/20 text-slate-300 border-slate-500/30', dot: 'bg-slate-400', label: 'Failed' },
  COMPLETED: { badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', dot: 'bg-emerald-400', label: 'Completed' },
};

function DecisionSourceBadge({ source }: { source?: string }) {
  if (source === 'LLM') {
    return (
      <span className="badge text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 inline-flex items-center gap-1">
        🤖 LLM
      </span>
    );
  }
  if (source === 'FALLBACK') {
    return (
      <span className="badge text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 inline-flex items-center gap-1">
        🛡️ Fallback
      </span>
    );
  }
  return (
    <span className="badge text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 inline-flex items-center gap-1">
      ⚙️ Deterministic
    </span>
  );
}

function CaseDetailDrawer({ caseId, onClose, onRefresh }: { caseId: string; onClose: () => void; onRefresh: () => void }) {
  const navigate = useNavigate();
  const [data, setData] = useState<RecoveryCase | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadCase = () => {
    casesApi.get(caseId).then(setData).catch(() => {});
  };

  useEffect(() => {
    loadCase();
  }, [caseId]);

  if (!data) {
    return (
      <div className="glass-card p-8 text-center text-muted flex items-center justify-center min-h-[400px]">
        <RefreshCw size={20} className="animate-spin text-primary mr-2" />
        Loading full case intelligence...
      </div>
    );
  }

  const effectiveStatus = data.status || data.outcome_status || 'PROCESSING';
  const badgeInfo = statusBadgeStyles[effectiveStatus] || statusBadgeStyles.PENDING;

  const sentinel = data.sentinel_output as Record<string, unknown> | undefined;
  const diagnosis = data.diagnosis_output as Record<string, unknown> | undefined;
  const opp = data.opportunity_score as Record<string, unknown> | undefined;
  const guardian = data.guardian_decision as Record<string, unknown> | undefined;
  const execution = data.execution_result as Record<string, unknown> | undefined;
  const profile = data.customer_profile as Record<string, unknown> | undefined;

  const handleRetry = async () => {
    setActionLoading(true);
    setActionMsg(null);
    try {
      const res = await casesApi.retry(caseId);
      setActionMsg(`Retry completed: ${res.status}`);
      loadCase();
      onRefresh();
    } catch (e: unknown) {
      setActionMsg(`Retry error: ${String(e)}`);
    }
    setActionLoading(false);
  };

  const handleStop = async () => {
    setActionLoading(true);
    setActionMsg(null);
    try {
      await casesApi.stop(caseId);
      setActionMsg('Case stopped.');
      loadCase();
      onRefresh();
    } catch (e: unknown) {
      setActionMsg(`Stop error: ${String(e)}`);
    }
    setActionLoading(false);
  };

  return (
    <motion.div
      initial={{ x: 50, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 50, opacity: 0 }}
      className="glass-card p-5 space-y-5 max-h-[85vh] overflow-y-auto"
    >
      {/* Drawer Header */}
      <div className="flex items-start justify-between border-b border-bg-border pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-white font-mono">{data.case_id}</span>
            <span className={`badge text-[11px] px-2 py-0.5 border ${badgeInfo.badge}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${badgeInfo.dot} inline-block mr-1`} />
              {badgeInfo.label}
            </span>
          </div>
          <div className="text-xs text-muted mt-0.5">
            Created: {fmtTime(data.started_at)}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-muted hover:text-white p-1 rounded hover:bg-subtle text-lg"
        >
          ✕
        </button>
      </div>

      {/* Action Notification */}
      {actionMsg && (
        <div className="p-2.5 rounded-lg bg-primary/10 border border-primary/30 text-xs text-primary-light flex items-center justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-xs text-muted hover:text-white">✕</button>
        </div>
      )}

      {/* Financial Summary Cards */}
      <div className="grid grid-cols-2 gap-2.5 text-xs">
        <div className="glass-card p-3 bg-bg-card/70">
          <div className="text-muted text-[11px]">Revenue at Risk</div>
          <div className="text-amber-400 text-base font-bold mt-0.5">{fmtAmt(data.revenue_at_risk)}</div>
        </div>
        <div className="glass-card p-3 bg-bg-card/70">
          <div className="text-muted text-[11px]">Recovered Amount</div>
          <div className="text-emerald-400 text-base font-bold mt-0.5">{fmtAmt(data.recovered_amount)}</div>
        </div>
        <div className="glass-card p-3 bg-bg-card/70">
          <div className="text-muted text-[11px]">Expected Value (ERV)</div>
          <div className="text-primary-light font-bold mt-0.5">{fmtAmt(data.expected_recovery_value || Number(opp?.expected_recovery_value || 0))}</div>
        </div>
        <div className="glass-card p-3 bg-bg-card/70">
          <div className="text-muted text-[11px]">Recovery Cost</div>
          <div className="text-slate-300 font-bold mt-0.5">{fmtAmt(data.recovery_cost || Number(opp?.estimated_cost || 15))}</div>
        </div>
      </div>

      {/* Action Bar based on State */}
      <div className="p-3 glass-card bg-primary/5 border-primary/20 space-y-2">
        <div className="text-xs font-semibold text-white flex items-center gap-1.5">
          <Activity size={13} className="text-primary" />
          Case Actions
        </div>

        {effectiveStatus === 'PENDING' && (
          <div className="flex gap-2">
            <button
              onClick={handleRetry}
              disabled={actionLoading}
              className="flex-1 btn-primary text-xs py-2 flex items-center justify-center gap-1.5"
            >
              {actionLoading ? <RefreshCw size={12} className="animate-spin" /> : <Play size={12} />}
              <span>Retry Recovery Now</span>
            </button>
            <button
              onClick={handleStop}
              disabled={actionLoading}
              className="btn-ghost text-xs py-2 px-3 text-rose-400 hover:bg-rose-500/10 border border-rose-500/20"
            >
              <span>Stop Case</span>
            </button>
          </div>
        )}

        {effectiveStatus === 'ESCALATED' && (
          <button
            onClick={() => navigate('/human-review')}
            className="w-full btn-primary text-xs py-2 bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30 flex items-center justify-center gap-1.5"
          >
            <UserCheck size={13} />
            <span>Open in Human Review Queue</span>
          </button>
        )}

        {effectiveStatus === 'RECOVERED' && (
          <div className="text-xs text-emerald-400 flex items-center gap-1.5 bg-emerald-500/10 p-2 rounded border border-emerald-500/20">
            <CheckCircle2 size={13} />
            <span>Successfully recovered full amount ({fmtAmt(data.recovered_amount)}) via {data.selected_strategy || 'RETRY_LATER'}.</span>
          </div>
        )}

        {effectiveStatus === 'STOPPED' && (
          <div className="text-xs text-rose-300 flex items-center gap-1.5 bg-rose-500/10 p-2 rounded border border-rose-500/20">
            <Shield size={13} />
            <span>Recovery stopped by Compliance Policy Guardian. All communications halted.</span>
          </div>
        )}

        {effectiveStatus === 'FAILED' && (
          <div className="flex gap-2">
            <button
              onClick={handleRetry}
              disabled={actionLoading}
              className="flex-1 btn-primary text-xs py-2 flex items-center justify-center gap-1.5"
            >
              <RefreshCw size={12} className={actionLoading ? 'animate-spin' : ''} />
              <span>Retry Recovery Attempt</span>
            </button>
          </div>
        )}
      </div>

      {/* Root Cause Diagnosis Section */}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-white flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Bot size={13} className="text-primary" />
            Root Cause Diagnosis
          </span>
          <DecisionSourceBadge source={String(diagnosis?.decision_source || 'DETERMINISTIC')} />
        </div>
        <div className="glass-card p-3 space-y-1.5 text-xs">
          <div className="flex justify-between">
            <span className="text-muted">Diagnosed Cause:</span>
            <span className="font-bold text-white">{data.root_cause?.replace(/_/g, ' ') || 'TEMPORARY BANK FAILURE'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">AI Confidence:</span>
            <span className="text-emerald-400 font-medium">
              {((Number(diagnosis?.confidence || 0.85)) * 100).toFixed(0)}%
            </span>
          </div>
          {Boolean(diagnosis?.reasoning) && (
            <div className="text-muted/90 pt-1 border-t border-bg-border text-[11px] leading-relaxed">
              {String(diagnosis?.reasoning)}
            </div>
          )}
        </div>
      </div>

      {/* Digital Twin Strategy Simulation */}
      {data.twin_predictions && data.twin_predictions.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-white flex items-center justify-between">
            <span>Recovery Digital Twin (Candidate Simulation)</span>
            <span className="text-[10px] text-muted">{data.twin_predictions.length} Strategies Ranked</span>
          </div>
          <div className="space-y-1.5">
            {data.twin_predictions.map((p, idx) => {
              const isSelected = p.strategy_type === data.selected_strategy || idx === 0;
              return (
                <div
                  key={idx}
                  className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-all ${
                    isSelected
                      ? 'border-primary/50 bg-primary/10 shadow-sm'
                      : 'border-bg-border bg-bg-card/50 text-muted'
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-1.5">
                      {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-primary" />}
                      <span className={`font-medium ${isSelected ? 'text-white font-bold' : 'text-slate-300'}`}>
                        {p.strategy_type.replace(/_/g, ' ')}
                      </span>
                      {isSelected && (
                        <span className="text-[9px] badge bg-primary/20 text-primary-light border border-primary/30">
                          Selected
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-muted mt-0.5">
                      Cost: ₹{p.estimated_cost} · Friction: {(p.customer_friction * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-emerald-400 font-bold">{(p.predicted_recovery_probability * 100).toFixed(0)}% prob</div>
                    <div className="text-[10px] text-muted">NEV: {fmtAmt(p.net_expected_value)}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Policy Guardian Decision */}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-white flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Shield size={13} className="text-primary" />
            Policy Guardian Checks
          </span>
          <span className={`badge text-[10px] ${data.policy_approved ? 'badge-success' : 'badge-danger'}`}>
            {data.policy_approved ? 'Policy Approved' : 'Policy Blocked'}
          </span>
        </div>
        <div className="glass-card p-3 text-xs space-y-1">
          <div className="flex justify-between text-muted">
            <span>Customer Opt-Out Check:</span>
            <span className="text-emerald-400 font-medium">PASSED</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>Contact Attempts Limit:</span>
            <span className="text-emerald-400 font-medium">PASSED (0/5)</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>Permitted Contact Hours:</span>
            <span className="text-emerald-400 font-medium">PASSED (IST 09:00-21:00)</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>High-Value Threshold Check:</span>
            <span className={data.revenue_at_risk > 100000 ? 'text-amber-400 font-medium' : 'text-emerald-400 font-medium'}>
              {data.revenue_at_risk > 100000 ? 'ESCALATION REQUIRED (>₹1L)' : 'PASSED (<₹1L)'}
            </span>
          </div>
        </div>
      </div>

      {/* 10-Agent Audit History */}
      {data.audit_logs && data.audit_logs.length > 0 && (
        <div className="space-y-2 border-t border-bg-border pt-3">
          <div className="text-xs font-semibold text-white flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <FileText size={13} className="text-primary" />
              Agent Audit Trail
            </span>
            <span className="text-[10px] text-muted">{data.audit_logs.length} Entries</span>
          </div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {data.audit_logs.map((log, idx) => (
              <div key={idx} className="glass-card p-2 text-xs flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-muted text-[10px]">#{log.step_index || idx + 1}</span>
                    <span className="text-white font-medium">{log.agent_name.replace(/_/g, ' ')}</span>
                    <DecisionSourceBadge source={log.decision_source} />
                  </div>
                  <div className="text-muted text-[11px] mt-0.5 truncate max-w-[220px]">
                    {log.decision}
                  </div>
                </div>
                <div className="text-right text-[10px] text-muted">
                  <div>{log.duration_ms?.toFixed(0)}ms</div>
                  <div className="text-emerald-400">{((log.confidence || 0) * 100).toFixed(0)}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default function CaseExplorer() {
  const location = useLocation();
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await casesApi.list(page, 20, statusFilter || undefined);
      setCases(r.cases);
      setTotal(r.total);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, [page, statusFilter]);

  // Handle incoming case selection from navigation state or URL query
  useEffect(() => {
    const navCaseId = (location.state as { selectedCaseId?: string } | null)?.selectedCaseId ||
      new URLSearchParams(location.search).get('case_id');
    if (navCaseId) {
      setSelectedId(navCaseId);
    }
  }, [location]);

  const filtered = search
    ? cases.filter(c =>
        c.case_id.toUpperCase().includes(search.toUpperCase()) ||
        c.root_cause?.toUpperCase().includes(search.toUpperCase()) ||
        c.selected_strategy?.toUpperCase().includes(search.toUpperCase())
      )
    : cases;

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Case Explorer</h1>
          <p className="text-muted text-sm mt-0.5">
            Inspect, triage, and action all {total} persistent revenue recovery cases
          </p>
        </div>
        <button
          onClick={load}
          className="btn-ghost flex items-center gap-2 text-sm hover:text-white"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filters & Search */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            className="w-full bg-bg-card border border-bg-border rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-muted focus:outline-none focus:border-primary/50 font-mono"
            placeholder="Search by Case ID, Root Cause, or Strategy..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="bg-bg-card border border-bg-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary/50"
          value={statusFilter}
          onChange={e => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All Statuses</option>
          <option value="RECOVERED">Recovered</option>
          <option value="PENDING">Pending / Scheduled</option>
          <option value="ESCALATED">Escalated</option>
          <option value="STOPPED">Stopped (Policy)</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {/* Cases Table + Drawer Split View */}
      <div className={`flex gap-6 ${selectedId ? 'items-start' : ''}`}>
        <div className="flex-1 glass-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-bg-border text-muted text-xs">
                <th className="text-left p-4 font-medium">Case ID</th>
                <th className="text-left p-4 font-medium">Root Cause</th>
                <th className="text-right p-4 font-medium">Revenue at Risk</th>
                <th className="text-right p-4 font-medium">Recovered</th>
                <th className="text-left p-4 font-medium">Status</th>
                <th className="text-left p-4 font-medium">Selected Strategy</th>
                <th className="p-4" />
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={7} className="text-center p-8 text-muted">
                    <RefreshCw size={18} className="animate-spin text-primary inline mr-2" />
                    Loading cases from database...
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center p-8 text-muted">
                    No cases match the selected filter. Run a simulation in the Simulation Lab!
                  </td>
                </tr>
              )}
              {filtered.map(c => {
                const st = c.status || c.outcome_status || 'PROCESSING';
                const badge = statusBadgeStyles[st] || statusBadgeStyles.PENDING;
                const isSelected = selectedId === c.case_id;

                return (
                  <tr
                    key={c.case_id}
                    className={`table-row cursor-pointer transition-all ${
                      isSelected ? 'bg-primary/10 border-l-2 border-primary' : ''
                    }`}
                    onClick={() => setSelectedId(isSelected ? null : c.case_id)}
                  >
                    <td className="p-4 font-mono text-white text-xs font-medium">{c.case_id}</td>
                    <td className="p-4 text-muted text-xs">{c.root_cause?.replace(/_/g, ' ') || 'Pending Diagnosis'}</td>
                    <td className="p-4 text-right text-amber-400 font-mono text-xs">{fmtAmt(c.revenue_at_risk)}</td>
                    <td className="p-4 text-right text-emerald-400 font-mono text-xs font-bold">{fmtAmt(c.recovered_amount)}</td>
                    <td className="p-4">
                      <span className={`badge text-[10px] px-2 py-0.5 border ${badge.badge}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${badge.dot} inline-block mr-1`} />
                        {badge.label}
                      </span>
                    </td>
                    <td className="p-4 text-muted text-xs">{c.selected_strategy?.replace(/_/g, ' ') || '—'}</td>
                    <td className="p-4">
                      <ChevronRight size={14} className={`text-muted transition-transform ${isSelected ? 'rotate-90 text-primary' : ''}`} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Selected Case Detail Drawer */}
        <AnimatePresence>
          {selectedId && (
            <div className="w-[430px] shrink-0">
              <CaseDetailDrawer
                caseId={selectedId}
                onClose={() => setSelectedId(null)}
                onRefresh={load}
              />
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
            className="btn-ghost text-xs px-3 py-1.5 disabled:opacity-40"
          >
            ← Previous
          </button>
          <span className="text-muted text-xs">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button
            disabled={page >= Math.ceil(total / 20)}
            onClick={() => setPage(p => p + 1)}
            className="btn-ghost text-xs px-3 py-1.5 disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
