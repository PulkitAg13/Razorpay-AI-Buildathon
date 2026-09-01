import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ScrollText, Bot, Filter } from 'lucide-react';
import { auditApi } from '../lib/api';
import type { AuditLog } from '../types';

const AGENTS = [
  '', 'revenue_sentinel', 'root_cause_diagnosis', 'customer_context_intelligence',
  'recovery_opportunity', 'recovery_strategy_planner', 'recovery_digital_twin',
  'compliance_policy_guardian', 'recovery_execution', 'outcome_monitor', 'learning_optimization',
];

export default function AuditExplorer() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [agentFilter, setAgentFilter] = useState('');
  const [selected, setSelected] = useState<AuditLog | null>(null);

  useEffect(() => {
    auditApi.list(page, 50, agentFilter || undefined).then(r => {
      setLogs(r.logs); setTotal(r.total);
    }).catch(() => {});
  }, [page, agentFilter]);

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Audit Explorer</h1>
        <p className="text-muted text-sm mt-0.5">Immutable audit trail of every agent decision</p>
      </div>

      <div className="flex gap-3">
        <div className="flex items-center gap-2 text-muted">
          <Filter size={14} />
          <span className="text-sm">Filter by agent:</span>
        </div>
        <select
          className="bg-bg-card border border-bg-border rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-primary/50"
          value={agentFilter}
          onChange={e => { setAgentFilter(e.target.value); setPage(1); setSelected(null); }}
        >
          {AGENTS.map(a => <option key={a} value={a}>{a || 'All Agents'}</option>)}
        </select>
        <div className="text-muted text-sm ml-auto">{total} log entries</div>
      </div>

      <div className={`flex gap-5 ${selected ? 'items-start' : ''}`}>
        <div className="flex-1 glass-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-bg-border text-muted text-xs">
                <th className="text-left p-4 font-medium">Timestamp</th>
                <th className="text-left p-4 font-medium">Agent</th>
                <th className="text-left p-4 font-medium">Case ID</th>
                <th className="text-left p-4 font-medium">Decision</th>
                <th className="text-right p-4 font-medium">Conf</th>
                <th className="text-right p-4 font-medium">Duration</th>
                <th className="p-4 font-medium">LLM</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 && (
                <tr><td colSpan={7} className="text-center p-8 text-muted">No audit logs yet. Run the pipeline!</td></tr>
              )}
              {logs.map(log => (
                <tr
                  key={log.id}
                  className={`table-row cursor-pointer text-xs ${selected?.id === log.id ? 'bg-primary/5' : ''}`}
                  onClick={() => setSelected(log.id === selected?.id ? null : log)}
                >
                  <td className="p-3 text-muted font-mono">{new Date(log.timestamp).toLocaleTimeString()}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-1.5">
                      <Bot size={12} className="text-primary" />
                      <span className="text-white">{log.agent_name.replace(/_/g, ' ')}</span>
                    </div>
                  </td>
                  <td className="p-3 font-mono text-muted">{log.case_id?.slice(0, 18)}...</td>
                  <td className="p-3 text-white max-w-[200px] truncate">{log.decision}</td>
                  <td className="p-3 text-right text-muted">{(log.confidence * 100).toFixed(0)}%</td>
                  <td className="p-3 text-right text-muted">{log.duration_ms?.toFixed(0)}ms</td>
                  <td className="p-3">
                    {log.decision_source === "LLM" ? (
                      <span className="badge badge-success bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">LLM</span>
                    ) : log.decision_source === "DETERMINISTIC" ? (
                      <span className="badge badge-primary bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Deterministic</span>
                    ) : (
                      <span className="badge badge-warning bg-amber-500/20 text-amber-300 border border-amber-500/30">Fallback</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selected && (
          <motion.div initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="w-96 glass-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-white">{selected.agent_name.replace(/_/g, ' ')}</div>
              <button onClick={() => setSelected(null)} className="text-muted hover:text-white">×</button>
            </div>
            <div>
              <div className="text-xs text-muted mb-1">Decision</div>
              <div className="text-sm text-white">{selected.decision}</div>
            </div>
            {selected.reasoning && (
              <div>
                <div className="text-xs text-muted mb-1">Reasoning</div>
                <div className="text-xs text-white leading-relaxed">{selected.reasoning}</div>
              </div>
            )}
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              {[
                { label: 'Confidence', value: `${(selected.confidence * 100).toFixed(0)}%` },
                { label: 'Duration', value: `${selected.duration_ms?.toFixed(0)}ms` },
                { label: 'Source', value: selected.decision_source || (selected.llm_used ? 'LLM' : 'Deterministic') },
              ].map(({ label, value }) => (
                <div key={label} className="bg-subtle rounded p-2">
                  <div className="font-bold text-white truncate">{value}</div>
                  <div className="text-muted">{label}</div>
                </div>
              ))}
            </div>
            {selected.llm_provider && selected.llm_provider !== 'None' && (
              <div className="text-xs text-muted">
                Provider: <span className="text-white font-mono">{selected.llm_provider}</span>
              </div>
            )}
            {selected.had_error && selected.error_message && (
              <div className="bg-danger/10 border border-danger/20 rounded p-3 text-xs text-danger">
                Error: {selected.error_message}
              </div>
            )}
            <details className="cursor-pointer">
              <summary className="text-xs text-muted">View raw output</summary>
              <pre className="text-xs text-muted mt-2 overflow-auto max-h-48 whitespace-pre-wrap">
                {JSON.stringify(selected.output, null, 2)}
              </pre>
            </details>
          </motion.div>
        )}
      </div>

      {total > 50 && (
        <div className="flex items-center justify-center gap-3">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="btn-ghost text-sm disabled:opacity-40">← Prev</button>
          <span className="text-muted text-sm">Page {page} of {Math.ceil(total / 50)}</span>
          <button disabled={page >= Math.ceil(total / 50)} onClick={() => setPage(p => p + 1)} className="btn-ghost text-sm disabled:opacity-40">Next →</button>
        </div>
      )}
    </div>
  );
}
