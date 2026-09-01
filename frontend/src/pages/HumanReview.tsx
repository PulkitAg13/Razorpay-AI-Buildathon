import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { UserCheck, CheckCircle2, XCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { humanReviewApi } from '../lib/api';
import type { HumanReview } from '../types';

const fmt = (n: number) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
const prio = { LOW: 'badge-muted', MEDIUM: 'badge-primary', HIGH: 'badge-warning', CRITICAL: 'badge-danger' };

export default function HumanReviewPage() {
  const [items, setItems] = useState<HumanReview[]>([]);
  const [selected, setSelected] = useState<HumanReview | null>(null);
  const [notes, setNotes] = useState('');
  const [deciding, setDeciding] = useState(false);
  const [tab, setTab] = useState<'PENDING' | 'APPROVED' | 'REJECTED'>('PENDING');

  const load = async () => {
    try {
      const r = await humanReviewApi.getQueue(tab);
      setItems(r.items);
    } catch {}
  };

  useEffect(() => { load(); }, [tab]);

  const decide = async (action: 'APPROVE' | 'REJECT') => {
    if (!selected) return;
    setDeciding(true);
    try {
      await humanReviewApi.decide(selected.id, action, notes);
      await load();
      setSelected(null);
      setNotes('');
    } catch {}
    setDeciding(false);
  };

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Human Review Queue</h1>
        <p className="text-muted text-sm mt-0.5">Cases requiring human approval before recovery execution</p>
      </div>

      <div className="flex gap-2">
        {(['PENDING', 'APPROVED', 'REJECTED'] as const).map(t => (
          <button key={t} onClick={() => { setTab(t); setSelected(null); }} className={tab === t ? 'btn-primary' : 'btn-ghost'}>
            {t}
          </button>
        ))}
      </div>

      {items.length === 0 && (
        <div className="glass-card p-12 text-center">
          <UserCheck size={40} className="mx-auto text-primary/40 mb-3" />
          <div className="text-muted">No {tab.toLowerCase()} items</div>
          <div className="text-xs text-muted mt-1">Escalated cases will appear here when the Policy Guardian routes them for review</div>
        </div>
      )}

      <div className={`flex gap-6 ${selected ? 'items-start' : ''}`}>
        <div className="flex-1 space-y-3">
          {items.map(item => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`glass-card p-4 cursor-pointer hover:border-primary/30 transition-all ${selected?.id === item.id ? 'border-primary/40' : ''}`}
              onClick={() => { setSelected(item === selected ? null : item); setNotes(''); }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`badge ${prio[item.escalation_priority]}`}>{item.escalation_priority}</span>
                    <span className="text-xs font-mono text-muted">{item.case_id}</span>
                  </div>
                  <div className="text-sm text-white mt-1">{item.escalation_reason}</div>
                  <div className="text-xs text-muted mt-0.5">AI Confidence: {(item.ai_confidence * 100).toFixed(0)}% · Amount: {fmt(item.amount_at_risk)}</div>
                </div>
                <div className="text-xs text-muted">{new Date(item.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}</div>
              </div>
            </motion.div>
          ))}
        </div>

        {selected && (
          <motion.div initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="w-96 glass-card p-5 space-y-4">
            <div className="text-sm font-semibold text-white">Review Decision</div>

            <div className="space-y-2 text-sm">
              <div className="glass-card p-3">
                <div className="text-muted text-xs mb-1">AI Recommendation</div>
                <pre className="text-white text-xs whitespace-pre-wrap">{JSON.stringify(selected.ai_recommendation, null, 2)}</pre>
              </div>
              <div className="glass-card p-3">
                <div className="text-muted text-xs mb-1">Reasoning</div>
                <div className="text-white text-xs">{selected.reasoning_summary || 'No reasoning provided'}</div>
              </div>
            </div>

            {tab === 'PENDING' && (
              <>
                <div>
                  <label className="text-xs text-muted block mb-1">Reviewer Notes</label>
                  <textarea
                    rows={3}
                    className="w-full bg-bg border border-bg-border rounded-lg px-3 py-2 text-sm text-white resize-none focus:outline-none focus:border-primary/50"
                    placeholder="Optional notes for audit trail..."
                    value={notes}
                    onChange={e => setNotes(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <button onClick={() => decide('APPROVE')} disabled={deciding} className="flex-1 flex items-center justify-center gap-2 bg-success/20 hover:bg-success/30 text-success border border-success/30 rounded-lg py-2 text-sm font-medium transition-all">
                    {deciding ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} Approve
                  </button>
                  <button onClick={() => decide('REJECT')} disabled={deciding} className="flex-1 flex items-center justify-center gap-2 bg-danger/20 hover:bg-danger/30 text-danger border border-danger/30 rounded-lg py-2 text-sm font-medium transition-all">
                    <XCircle size={14} /> Reject
                  </button>
                </div>
              </>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
