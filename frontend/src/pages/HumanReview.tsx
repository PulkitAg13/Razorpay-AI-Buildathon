import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UserCheck, CheckCircle2, XCircle, AlertTriangle, Loader2,
  Bot, Shield, ArrowRight, Clock, FileText, Check, DollarSign, RefreshCw
} from 'lucide-react';
import { humanReviewApi } from '../lib/api';
import type { HumanReview } from '../types';

const fmt = (n: number) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const prioStyles: Record<string, { badge: string; label: string }> = {
  LOW: { badge: 'bg-slate-500/20 text-slate-300 border-slate-500/30', label: 'Low Priority' },
  MEDIUM: { badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30', label: 'Medium Priority' },
  HIGH: { badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30', label: 'High Value / High Risk' },
  CRITICAL: { badge: 'bg-rose-500/20 text-rose-300 border-rose-500/30', label: 'Critical Escalation' },
};

export default function HumanReviewPage() {
  const [items, setItems] = useState<HumanReview[]>([]);
  const [selected, setSelected] = useState<HumanReview | null>(null);
  const [notes, setNotes] = useState('');
  const [deciding, setDeciding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'PENDING' | 'APPROVED' | 'REJECTED'>('PENDING');
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await humanReviewApi.getQueue(tab);
      setItems(r.items);
      // Auto-select first if none selected
      if (r.items.length > 0 && (!selected || !r.items.some(i => i.id === selected.id))) {
        setSelected(r.items[0]);
      } else if (r.items.length === 0) {
        setSelected(null);
      }
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    load();
    setActionSuccess(null);
  }, [tab]);

  const decide = async (action: 'APPROVE' | 'REJECT') => {
    if (!selected) return;
    setDeciding(true);
    setActionSuccess(null);
    try {
      const res = await humanReviewApi.decide(selected.id, action, notes);
      setActionSuccess(
        action === 'APPROVE'
          ? `Case approved! Recovery execution completed (${(res as Record<string, unknown>).outcome_status || 'RECOVERED'}).`
          : 'Case rejected. Recovery halted by policy.'
      );
      await load();
      setNotes('');
    } catch (e: unknown) {
      setActionSuccess(`Error: ${String(e)}`);
    }
    setDeciding(false);
  };

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <UserCheck className="text-primary" size={24} />
            Human Review Queue
          </h1>
          <p className="text-muted text-sm mt-0.5">
            Escalated edge-cases & high-value revenue recovery decisions requiring human approval
          </p>
        </div>
        <button
          onClick={load}
          className="btn-ghost text-xs flex items-center gap-1.5 hover:text-white"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-bg-border pb-3">
        {(['PENDING', 'APPROVED', 'REJECTED'] as const).map(t => {
          const isActive = tab === t;
          return (
            <button
              key={t}
              onClick={() => {
                setTab(t);
                setSelected(null);
                setNotes('');
              }}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-2 ${
                isActive
                  ? 'bg-primary text-white shadow-lg shadow-primary/20'
                  : 'bg-bg-card/50 text-muted hover:text-white hover:bg-subtle'
              }`}
            >
              <span>{t}</span>
              {t === 'PENDING' && items.length > 0 && tab === 'PENDING' && (
                <span className="w-5 h-5 rounded-full bg-white/20 text-white flex items-center justify-center text-[10px]">
                  {items.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Action Notification */}
      {actionSuccess && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-300 flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 size={15} className="text-emerald-400" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-muted hover:text-white text-xs">✕</button>
        </motion.div>
      )}

      {/* Empty State */}
      {!loading && items.length === 0 && (
        <div className="glass-card p-12 text-center space-y-2">
          <UserCheck size={36} className="mx-auto text-primary/40 mb-2" />
          <div className="text-base font-semibold text-white">No {tab.toLowerCase()} review items</div>
          <div className="text-xs text-muted max-w-md mx-auto leading-relaxed">
            {tab === 'PENDING'
              ? 'When Policy Guardian encounters high-value (>₹1L) or low-confidence edge cases, they are routed here for human approval.'
              : `Historical ${tab.toLowerCase()} human review cases will appear here.`}
          </div>
        </div>
      )}

      {/* Queue Grid: List + Detail Decision Drawer */}
      {items.length > 0 && (
        <div className={`flex gap-6 ${selected ? 'items-start' : ''}`}>
          {/* List of Review Items */}
          <div className="flex-1 space-y-3">
            {items.map(item => {
              const prio = prioStyles[item.escalation_priority] || prioStyles.MEDIUM;
              const isSelected = selected?.id === item.id;
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`glass-card p-4 cursor-pointer hover:border-primary/40 transition-all ${
                    isSelected ? 'border-primary bg-primary/10 shadow-md' : 'bg-bg-card/70'
                  }`}
                  onClick={() => {
                    setSelected(item);
                    setNotes('');
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`badge text-[10px] px-2 py-0.5 border ${prio.badge}`}>
                          {prio.label}
                        </span>
                        <span className="text-xs font-mono font-bold text-white">{item.case_id}</span>
                      </div>
                      <div className="text-sm font-semibold text-white">
                        {item.escalation_reason || 'Policy Escalation Approval Required'}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted">
                        <span>Amount: <strong className="text-amber-400 font-mono">{fmt(item.amount_at_risk)}</strong></span>
                        <span>·</span>
                        <span>AI Confidence: <strong className="text-emerald-400 font-medium">{((item.ai_confidence || 0.7) * 100).toFixed(0)}%</strong></span>
                      </div>
                    </div>
                    <div className="text-right space-y-1">
                      <div className="text-[11px] text-muted font-mono">
                        {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                      {item.reviewed_at && (
                        <div className="text-[10px] text-emerald-400">Reviewed</div>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Decision Drawer */}
          {selected && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="w-[440px] shrink-0 glass-card p-5 space-y-4"
            >
              <div className="flex items-center justify-between border-b border-bg-border pb-3">
                <div>
                  <div className="text-sm font-bold text-white flex items-center gap-1.5">
                    <Shield size={14} className="text-primary" />
                    Review Decision & Execution
                  </div>
                  <div className="text-xs text-muted font-mono mt-0.5">{selected.case_id}</div>
                </div>
                <span className={`badge text-[10px] ${prioStyles[selected.escalation_priority]?.badge}`}>
                  {selected.escalation_priority}
                </span>
              </div>

              {/* Summary KPIs */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="glass-card p-2.5 bg-bg-card/50">
                  <div className="text-muted text-[11px]">Revenue at Stake</div>
                  <div className="text-amber-400 font-bold text-base mt-0.5">{fmt(selected.amount_at_risk)}</div>
                </div>
                <div className="glass-card p-2.5 bg-bg-card/50">
                  <div className="text-muted text-[11px]">AI Recommendation</div>
                  <div className="text-primary-light font-bold text-sm mt-0.5 truncate">
                    {String(
                      (selected.ai_recommendation as Record<string, unknown>)?.strategy_type ||
                      selected.candidate_strategies?.[0]?.strategy_type ||
                      'RETRY_LATER'
                    ).replace(/_/g, ' ')}
                  </div>
                </div>
              </div>

              {/* Reasoning */}
              <div className="glass-card p-3 space-y-1.5 text-xs bg-bg-card/50">
                <div className="text-muted font-medium">Policy Reason & AI Rationale</div>
                <div className="text-slate-200 text-xs leading-relaxed">
                  {selected.reasoning_summary || selected.escalation_reason || 'High-value transaction requires human approval prior to executing automated payment tools.'}
                </div>
              </div>

              {/* Candidate Strategies Preview */}
              {selected.twin_predictions && selected.twin_predictions.length > 0 && (
                <div className="space-y-1.5 text-xs">
                  <div className="text-muted font-medium">Digital Twin Strategy NEVs</div>
                  {selected.twin_predictions.slice(0, 2).map((pred, i) => (
                    <div key={i} className="glass-card p-2 flex justify-between items-center text-xs">
                      <span className="text-white font-medium">{pred.strategy_type.replace(/_/g, ' ')}</span>
                      <span className="text-emerald-400 font-bold">NEV {fmt(pred.net_expected_value)}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Historical Notes for Approved/Rejected */}
              {tab !== 'PENDING' && selected.reviewer_notes && (
                <div className="glass-card p-3 space-y-1 text-xs bg-bg-card/50">
                  <div className="text-muted font-medium">Operator Notes</div>
                  <div className="text-white italic">{selected.reviewer_notes}</div>
                  <div className="text-[10px] text-muted mt-1">
                    Reviewed: {selected.reviewed_at ? new Date(selected.reviewed_at).toLocaleString() : '—'}
                  </div>
                </div>
              )}

              {/* Interactive Approval Panel for Pending Items */}
              {tab === 'PENDING' && (
                <div className="space-y-3 pt-2 border-t border-bg-border">
                  <div>
                    <label className="text-xs text-muted block mb-1">Operator Notes / Audit Comments</label>
                    <textarea
                      rows={2}
                      className="w-full bg-bg border border-bg-border rounded-lg px-3 py-2 text-xs text-white resize-none focus:outline-none focus:border-primary/50"
                      placeholder="e.g. Approved for immediate WhatsApp + link follow-up with customer..."
                      value={notes}
                      onChange={e => setNotes(e.target.value)}
                    />
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => decide('APPROVE')}
                      disabled={deciding}
                      className="flex-1 btn-primary text-xs py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/20"
                    >
                      {deciding ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={14} />}
                      <span>Approve & Execute</span>
                    </button>
                    <button
                      onClick={() => decide('REJECT')}
                      disabled={deciding}
                      className="flex-1 btn-ghost text-xs py-2.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 font-medium flex items-center justify-center gap-1.5"
                    >
                      <XCircle size={14} />
                      <span>Reject & Stop</span>
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
