import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, RefreshCw, Bot, Shield, ChevronRight, Clock, Code, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import { auditApi } from '../lib/api';
import type { AuditLog } from '../types';

const AGENTS = [
  'revenue_sentinel', 'root_cause_diagnosis', 'customer_context_intelligence',
  'recovery_opportunity', 'recovery_strategy_planner', 'recovery_digital_twin',
  'compliance_policy_guardian', 'recovery_execution', 'outcome_monitor',
  'learning_optimization',
];

function DecisionSourceTag({ source }: { source?: string }) {
  if (source === 'LLM') {
    return (
      <span className="badge text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 inline-flex items-center gap-1 font-medium">
        🤖 LLM
      </span>
    );
  }
  if (source === 'FALLBACK') {
    return (
      <span className="badge text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 inline-flex items-center gap-1 font-medium">
        🛡️ Fallback
      </span>
    );
  }
  return (
    <span className="badge text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 inline-flex items-center gap-1 font-medium">
      ⚙️ Deterministic
    </span>
  );
}

function AuditDetailModal({ log, onClose }: { log: AuditLog; onClose: () => void }) {
  const isLLM = log.decision_source === 'LLM' || log.llm_used;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="glass-card w-full max-w-2xl max-h-[85vh] overflow-y-auto p-6 space-y-5 border-primary/30"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-bg-border pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-white font-mono">#{log.id} · {log.agent_name.replace(/_/g, ' ')}</span>
              <DecisionSourceTag source={log.decision_source} />
            </div>
            <div className="text-xs text-muted font-mono mt-0.5">
              Case ID: <strong className="text-primary-light">{log.case_id}</strong> · Step #{log.step_index || '—'}
            </div>
          </div>
          <button onClick={onClose} className="text-muted hover:text-white text-lg p-1">✕</button>
        </div>

        {/* Telemetry metadata */}
        <div className="grid grid-cols-3 gap-2.5 text-xs">
          <div className="glass-card p-3 bg-bg-card/50">
            <div className="text-muted text-[11px]">Execution Latency</div>
            <div className="text-white font-bold font-mono mt-0.5">{log.duration_ms?.toFixed(1) || 0} ms</div>
          </div>
          <div className="glass-card p-3 bg-bg-card/50">
            <div className="text-muted text-[11px]">Decision Confidence</div>
            <div className="text-emerald-400 font-bold font-mono mt-0.5">{((log.confidence || 0.8) * 100).toFixed(0)}%</div>
          </div>
          <div className="glass-card p-3 bg-bg-card/50">
            <div className="text-muted text-[11px]">Model / Provider</div>
            <div className="text-primary-light font-bold truncate mt-0.5">
              {isLLM ? (log.llm_model || 'Gemini 2.5 Flash') : 'Rule Engine (0 Quota)'}
            </div>
          </div>
        </div>

        {/* Decision & Reasoning */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-white">Decision Summary</div>
          <div className="glass-card p-3 bg-primary/5 border border-primary/20 text-xs font-bold text-white font-mono">
            {log.decision}
          </div>
        </div>

        {log.reasoning && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-white">Full Rationale & Chain of Thought</div>
            <div className="glass-card p-3.5 bg-bg-card/70 text-xs text-slate-200 leading-relaxed">
              {log.reasoning}
            </div>
          </div>
        )}

        {/* Input & Output Payloads */}
        <div className="space-y-3 pt-2 border-t border-bg-border">
          <div className="text-xs font-semibold text-white flex items-center gap-1.5">
            <Code size={13} className="text-primary" />
            Structured Agent I/O Data
          </div>

          {log.input && (
            <div>
              <div className="text-[11px] text-muted mb-1 font-mono">INPUT_PAYLOAD:</div>
              <pre className="glass-card p-3 bg-bg text-[11px] text-slate-300 font-mono overflow-x-auto max-h-36 rounded-lg">
                {typeof log.input === 'string' ? log.input : JSON.stringify(log.input, null, 2)}
              </pre>
            </div>
          )}

          {log.output && (
            <div>
              <div className="text-[11px] text-muted mb-1 font-mono">OUTPUT_DECISION:</div>
              <pre className="glass-card p-3 bg-bg text-[11px] text-emerald-300 font-mono overflow-x-auto max-h-36 rounded-lg">
                {typeof log.output === 'string' ? log.output : JSON.stringify(log.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

export default function AuditExplorer() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [agentFilter, setAgentFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const [caseFilter, setCaseFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await auditApi.list(
        page,
        50,
        agentFilter || undefined,
        caseFilter || undefined,
        sourceFilter !== 'ALL' ? sourceFilter : undefined
      );
      setLogs(r.logs);
      setTotal(r.total);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, [page, agentFilter, sourceFilter]);

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Shield className="text-primary" size={24} />
            Audit Explorer
          </h1>
          <p className="text-muted text-sm mt-0.5">
            Cryptographically logged decisions, reasoning, and runtime telemetry for every agent invocation ({total} Total Records)
          </p>
        </div>
        <button
          onClick={load}
          className="btn-ghost text-xs flex items-center gap-1.5 hover:text-white"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Decision Source Filter Pills */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-muted mr-1">Decision Source:</span>
        {[
          { id: 'ALL', label: 'All Sources' },
          { id: 'LLM', label: '🤖 LLM Invocations' },
          { id: 'DETERMINISTIC', label: '⚙️ Deterministic' },
          { id: 'FALLBACK', label: '🛡️ Fallbacks' },
        ].map(src => {
          const isActive = sourceFilter === src.id;
          return (
            <button
              key={src.id}
              onClick={() => {
                setSourceFilter(src.id);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-primary text-white shadow-md shadow-primary/20'
                  : 'bg-bg-card border border-bg-border text-muted hover:text-white'
              }`}
            >
              {src.label}
            </button>
          );
        })}
      </div>

      {/* Search & Agent Filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            className="w-full bg-bg-card border border-bg-border rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-muted focus:outline-none focus:border-primary/50 font-mono"
            placeholder="Search by Case ID..."
            value={caseFilter}
            onChange={e => setCaseFilter(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load()}
          />
        </div>
        <select
          className="bg-bg-card border border-bg-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary/50"
          value={agentFilter}
          onChange={e => {
            setAgentFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All Agents (10)</option>
          {AGENTS.map(a => (
            <option key={a} value={a}>
              {a.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      {/* Logs Table */}
      <div className="glass-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-bg-border text-muted text-xs">
              <th className="text-left p-4 font-medium">Timestamp</th>
              <th className="text-left p-4 font-medium">Case ID</th>
              <th className="text-left p-4 font-medium">Agent</th>
              <th className="text-left p-4 font-medium">Source</th>
              <th className="text-left p-4 font-medium">Decision</th>
              <th className="text-right p-4 font-medium">Confidence</th>
              <th className="text-right p-4 font-medium">Latency</th>
              <th className="p-4" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="text-center p-8 text-muted">
                  <RefreshCw size={18} className="animate-spin text-primary inline mr-2" />
                  Loading audit logs...
                </td>
              </tr>
            )}
            {!loading && logs.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center p-8 text-muted">
                  No audit logs found. Run a case in the Simulation Lab to generate agent audit records!
                </td>
              </tr>
            )}
            {logs.map(log => (
              <tr
                key={log.id}
                className="table-row cursor-pointer"
                onClick={() => setSelectedLog(log)}
              >
                <td className="p-4 text-muted text-xs font-mono">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </td>
                <td className="p-4 font-mono text-white text-xs font-medium">{log.case_id}</td>
                <td className="p-4 text-slate-200 text-xs font-medium">
                  {log.agent_name.replace(/_/g, ' ')}
                </td>
                <td className="p-4">
                  <DecisionSourceTag source={log.decision_source} />
                </td>
                <td className="p-4 text-white text-xs max-w-xs truncate font-mono">
                  {log.decision}
                </td>
                <td className="p-4 text-right text-emerald-400 font-mono text-xs">
                  {((log.confidence || 0.85) * 100).toFixed(0)}%
                </td>
                <td className="p-4 text-right text-muted font-mono text-xs">
                  {log.duration_ms?.toFixed(0)}ms
                </td>
                <td className="p-4">
                  <ChevronRight size={14} className="text-muted" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 50 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
            className="btn-ghost text-xs px-3 py-1.5 disabled:opacity-40"
          >
            ← Previous
          </button>
          <span className="text-muted text-xs">
            Page {page} of {Math.ceil(total / 50)}
          </span>
          <button
            disabled={page >= Math.ceil(total / 50)}
            onClick={() => setPage(p => p + 1)}
            className="btn-ghost text-xs px-3 py-1.5 disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}

      {/* Modal Detail View */}
      <AnimatePresence>
        {selectedLog && (
          <AuditDetailModal log={selectedLog} onClose={() => setSelectedLog(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}
