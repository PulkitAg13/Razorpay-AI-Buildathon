import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../store';
import { Wifi, WifiOff, Zap, Bot, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import type { LiveEvent } from '../types';

const fmtTime = (ts?: number | string) => {
  if (!ts) return '';
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const fmtAmount = (n?: number) => n ? `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '';

function EventIcon({ type }: { type: string }) {
  if (type === 'case_created') return <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center"><Zap size={14} className="text-primary" /></div>;
  if (type === 'agent_step')  return <div className="w-7 h-7 rounded-full bg-subtle flex items-center justify-center"><Bot size={14} className="text-muted" /></div>;
  if (type === 'case_resolved') return <div className="w-7 h-7 rounded-full bg-success/20 flex items-center justify-center"><CheckCircle2 size={14} className="text-success" /></div>;
  return <div className="w-7 h-7 rounded-full bg-warning/20 flex items-center justify-center"><Clock size={14} className="text-warning" /></div>;
}

function EventBadge({ event }: { event: LiveEvent }) {
  if (event.type === 'case_created') return <span className="badge badge-primary">New Case</span>;
  if (event.type === 'case_resolved') {
    const ok = event.outcome === 'RECOVERED';
    return <span className={ok ? 'badge badge-success' : 'badge badge-muted'}>{event.outcome}</span>;
  }
  if (event.type === 'agent_step') return <span className="badge badge-muted">Agent Step</span>;
  return <span className="badge badge-warning">Simulation</span>;
}

function LiveEventRow({ event }: { event: LiveEvent }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className="flex items-start gap-3 py-3 border-b border-bg-border"
    >
      <EventIcon type={event.type} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <EventBadge event={event} />
          {event.case_id && <span className="text-xs font-mono text-muted">{event.case_id}</span>}
          {event.agent && <span className="text-xs text-primary-light">{event.agent.replace(/_/g, ' ')}</span>}
        </div>
        <div className="text-sm text-white mt-0.5">
          {event.type === 'case_created' && <>New {event.event_type?.replace(/_/g, ' ')} — {fmtAmount(event.amount)}</>}
          {event.type === 'agent_step' && <>{event.decision || 'Processing'} {event.confidence ? `(${(event.confidence * 100).toFixed(0)}% conf)` : ''}</>}
          {event.type === 'case_resolved' && <>Outcome: {event.outcome} {event.recovered_amount ? `— ${fmtAmount(event.recovered_amount)} recovered` : ''}</>}
          {event.type === 'simulation_progress' && <>Simulation in progress…</>}
        </div>
        {event.duration_ms !== undefined && (
          <div className="text-xs text-muted mt-0.5">{event.duration_ms.toFixed(0)}ms</div>
        )}
      </div>
      <div className="text-xs text-muted shrink-0">{fmtTime(event._ts || event.timestamp)}</div>
    </motion.div>
  );
}

export default function LiveFeed() {
  const liveEvents = useAppStore(s => s.liveEvents);
  const wsConnected = useAppStore(s => s.wsConnected);

  const caseCreated = liveEvents.filter(e => e.type === 'case_created').length;
  const resolved = liveEvents.filter(e => e.type === 'case_resolved').length;
  const recovered = liveEvents.filter(e => e.type === 'case_resolved' && e.outcome === 'RECOVERED').length;

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Recovery Feed</h1>
          <p className="text-muted text-sm mt-0.5">Real-time agent activity stream via WebSocket</p>
        </div>
        <div className="flex items-center gap-2">
          {wsConnected
            ? <><div className="status-dot-green" /><span className="text-success text-sm">Live</span></>
            : <><WifiOff size={14} className="text-muted" /><span className="text-muted text-sm">Reconnecting...</span></>
          }
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-card p-4 text-center">
          <div className="text-2xl font-bold text-primary">{caseCreated}</div>
          <div className="text-xs text-muted mt-1">Cases Detected</div>
        </div>
        <div className="glass-card p-4 text-center">
          <div className="text-2xl font-bold text-white">{resolved}</div>
          <div className="text-xs text-muted mt-1">Resolved</div>
        </div>
        <div className="glass-card p-4 text-center">
          <div className="text-2xl font-bold text-success">{recovered}</div>
          <div className="text-xs text-muted mt-1">Recovered</div>
        </div>
      </div>

      {/* Feed */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm font-semibold text-white">Event Stream</div>
          <div className="text-xs text-muted">{liveEvents.length} events</div>
        </div>
        {liveEvents.length === 0 ? (
          <div className="text-center py-16 text-muted">
            <Zap size={32} className="mx-auto mb-3 text-primary/40" />
            <div className="text-sm">Waiting for events...</div>
            <div className="text-xs mt-1">Run a simulation from the Simulation Lab to see live activity</div>
          </div>
        ) : (
          <div className="max-h-[600px] overflow-y-auto pr-1">
            <AnimatePresence mode="popLayout">
              {liveEvents.map((e, i) => (
                <LiveEventRow key={`${e._ts}-${i}`} event={e} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
