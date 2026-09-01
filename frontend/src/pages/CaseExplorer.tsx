import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Search, ChevronRight, RefreshCw } from 'lucide-react';
import { casesApi } from '../lib/api';
import type { RecoveryCase } from '../types';

const fmtAmt = (n: number) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
const fmtTime = (s: string) => s ? new Date(s).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '—';

const statusColors: Record<string, string> = {
  RECOVERED: 'badge-success', NOT_RECOVERED: 'badge-muted', PENDING: 'badge-warning',
  ESCALATED: 'badge-warning', STOPPED: 'badge-danger', COMPLETED: 'badge-success',
};

function CaseDetail({ caseId, onClose }: { caseId: string; onClose: () => void }) {
  const [data, setData] = useState<RecoveryCase | null>(null);
  useEffect(() => { casesApi.get(caseId).then(setData).catch(() => {}); }, [caseId]);

  if (!data) return <div className="p-8 text-center text-muted">Loading case...</div>;

  const agents = [
    { name: 'Revenue Sentinel', key: 'sentinel_output' },
    { name: 'Root Cause Diagnosis', key: 'diagnosis_output' },
    { name: 'Customer Context', key: 'customer_profile' },
    { name: 'Opportunity Score', key: 'opportunity_score' },
    { name: 'Guardian Decision', key: 'guardian_decision' },
    { name: 'Execution Result', key: 'execution_result' },
  ];

  return (
    <motion.div initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="glass-card p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-bold text-white font-mono">{data.case_id}</div>
          <div className="text-sm text-muted">{data.root_cause?.replace(/_/g, ' ') || 'Pending'}</div>
        </div>
        <button onClick={onClose} className="text-muted hover:text-white text-xl">×</button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="glass-card p-3">
          <div className="text-muted text-xs mb-1">Revenue at Risk</div>
          <div className="text-white font-bold">{fmtAmt(data.revenue_at_risk)}</div>
        </div>
        <div className="glass-card p-3">
          <div className="text-muted text-xs mb-1">Recovered</div>
          <div className="text-success font-bold">{fmtAmt(data.recovered_amount)}</div>
        </div>
        <div className="glass-card p-3">
          <div className="text-muted text-xs mb-1">Strategy</div>
          <div className="text-white text-xs">{data.selected_strategy?.replace(/_/g, ' ') || '—'}</div>
        </div>
        <div className="glass-card p-3">
          <div className="text-muted text-xs mb-1">Status</div>
          <span className={`badge ${statusColors[data.outcome_status || ''] || 'badge-muted'}`}>{data.outcome_status || data.status}</span>
        </div>
      </div>

      {/* Agent decisions */}
      <div className="space-y-2">
        <div className="text-sm font-semibold text-white">Agent Decisions</div>
        {agents.map(({ name, key }) => {
          const d = (data as unknown as Record<string, unknown>)[key] as Record<string, unknown> | undefined;
          if (!d || Object.keys(d).length === 0) return null;
          return (
            <details key={key} className="glass-card p-3 cursor-pointer">
              <summary className="text-sm text-primary-light font-medium">{name}</summary>
              <pre className="text-xs text-muted mt-2 overflow-auto max-h-40 whitespace-pre-wrap">
                {JSON.stringify(d, null, 2)}
              </pre>
            </details>
          );
        })}
      </div>

      {/* Digital Twin predictions */}
      {data.twin_predictions && data.twin_predictions.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-semibold text-white">Digital Twin Predictions</div>
          {data.twin_predictions.slice(0, 3).map((p, i) => (
            <div key={i} className="glass-card p-3 flex items-center justify-between text-sm">
              <div>
                <div className="text-white font-medium">{p.strategy_type.replace(/_/g, ' ')}</div>
                <div className="text-xs text-muted">{p.simulation_notes?.slice(0, 80)}</div>
              </div>
              <div className="text-right">
                <div className="text-success text-xs">{(p.predicted_recovery_probability * 100).toFixed(0)}%</div>
                <div className="text-xs text-muted">NEV: {fmtAmt(p.net_expected_value)}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {data.audit_logs && data.audit_logs.length > 0 && (
        <div className="text-xs text-muted">{data.audit_logs.length} audit log entries available</div>
      )}
    </motion.div>
  );
}

export default function CaseExplorer() {
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
      setCases(r.cases); setTotal(r.total);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, [page, statusFilter]);

  const filtered = search
    ? cases.filter(c => c.case_id.includes(search.toUpperCase()) || c.root_cause?.includes(search.toUpperCase()))
    : cases;

  return (
    <div className="p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Case Explorer</h1>
          <p className="text-muted text-sm mt-0.5">{total} recovery cases</p>
        </div>
        <button onClick={load} className="btn-ghost flex items-center gap-2 text-sm">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      <div className="flex gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            className="w-full bg-bg-card border border-bg-border rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-muted focus:outline-none focus:border-primary/50"
            placeholder="Search case ID or root cause..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="bg-bg-card border border-bg-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary/50"
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
        >
          <option value="">All Statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="STOPPED">Stopped</option>
          <option value="ESCALATED">Escalated</option>
        </select>
      </div>

      <div className={`flex gap-6 ${selectedId ? 'items-start' : ''}`}>
        <div className="flex-1 glass-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-bg-border text-muted text-xs">
                <th className="text-left p-4 font-medium">Case ID</th>
                <th className="text-left p-4 font-medium">Root Cause</th>
                <th className="text-right p-4 font-medium">At Risk</th>
                <th className="text-right p-4 font-medium">Recovered</th>
                <th className="text-left p-4 font-medium">Status</th>
                <th className="text-left p-4 font-medium">Strategy</th>
                <th className="p-4" />
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={7} className="text-center p-8 text-muted">Loading...</td></tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={7} className="text-center p-8 text-muted">No cases found. Run a simulation first!</td></tr>
              )}
              {filtered.map(c => (
                <tr
                  key={c.case_id}
                  className={`table-row cursor-pointer ${selectedId === c.case_id ? 'bg-primary/5' : ''}`}
                  onClick={() => setSelectedId(c.case_id === selectedId ? null : c.case_id)}
                >
                  <td className="p-4 font-mono text-white text-xs">{c.case_id}</td>
                  <td className="p-4 text-muted text-xs">{c.root_cause?.replace(/_/g, ' ') || '—'}</td>
                  <td className="p-4 text-right text-warning">{fmtAmt(c.revenue_at_risk)}</td>
                  <td className="p-4 text-right text-success">{fmtAmt(c.recovered_amount)}</td>
                  <td className="p-4"><span className={`badge ${statusColors[c.outcome_status || ''] || 'badge-muted'}`}>{c.outcome_status || c.status}</span></td>
                  <td className="p-4 text-muted text-xs">{c.selected_strategy?.replace(/_/g, ' ') || '—'}</td>
                  <td className="p-4"><ChevronRight size={14} className="text-muted" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedId && (
          <div className="w-[400px] shrink-0">
            <CaseDetail caseId={selectedId} onClose={() => setSelectedId(null)} />
          </div>
        )}
      </div>

      {total > 20 && (
        <div className="flex items-center justify-center gap-3 mt-5">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="btn-ghost text-sm disabled:opacity-40">← Prev</button>
          <span className="text-muted text-sm">Page {page} of {Math.ceil(total / 20)}</span>
          <button disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(p => p + 1)} className="btn-ghost text-sm disabled:opacity-40">Next →</button>
        </div>
      )}
    </div>
  );
}
