import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, DollarSign, Target, Shield, Clock, Users, AlertTriangle } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { dashboardApi } from '../lib/api';
import { useAppStore } from '../store';
import type { DashboardMetrics } from '../types';

const fmt = (n: number) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
const fmtK = (n: number) => n >= 100000 ? `₹${(n / 100000).toFixed(1)}L` : n >= 1000 ? `₹${(n / 1000).toFixed(1)}K` : `₹${n.toFixed(0)}`;

function MetricCard({ title, value, sub, icon: Icon, color = 'primary', trend }: {
  title: string; value: string; sub?: string;
  icon: React.ElementType; color?: string; trend?: number;
}) {
  const colors = {
    primary: 'text-primary-light bg-primary/10',
    success: 'text-success bg-success/10',
    warning: 'text-warning bg-warning/10',
    danger: 'text-danger bg-danger/10',
    muted: 'text-muted bg-subtle',
  };
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="metric-card">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2 rounded-lg ${colors[color as keyof typeof colors]}`}>
          <Icon size={18} />
        </div>
        {trend !== undefined && (
          <span className={`text-xs flex items-center gap-1 ${trend >= 0 ? 'text-success' : 'text-danger'}`}>
            {trend >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {Math.abs(trend).toFixed(1)}%
          </span>
        )}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-sm text-muted mt-1">{title}</div>
      {sub && <div className="text-xs text-muted/70 mt-0.5">{sub}</div>}
    </motion.div>
  );
}

const COLORS = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#94A3B8'];

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [timeline, setTimeline] = useState<Array<{ date: string; revenue_at_risk: number; recovered: number }>>([]);
  const [loading, setLoading] = useState(true);
  const { setMetrics: storeSetMetrics } = useAppStore();

  useEffect(() => {
    const load = async () => {
      try {
        const [m, t] = await Promise.all([dashboardApi.getMetrics(), dashboardApi.getTimeline(7)]);
        setMetrics(m); storeSetMetrics(m); setTimeline(t);
      } catch { /* backend may not be seeded yet */ }
      finally { setLoading(false); }
    };
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const pieData = metrics ? [
    { name: 'Recovered', value: metrics.recovered_cases },
    { name: 'Active', value: metrics.active_cases },
    { name: 'Escalated', value: metrics.escalated_cases },
    { name: 'Stopped', value: metrics.stopped_cases },
    { name: 'Not Recovered', value: metrics.total_cases - metrics.recovered_cases - metrics.active_cases - metrics.escalated_cases - metrics.stopped_cases },
  ].filter(d => d.value > 0) : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center mx-auto animate-pulse">
            <DollarSign className="text-primary" />
          </div>
          <div className="text-muted text-sm">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Executive Dashboard</h1>
          <p className="text-muted text-sm mt-0.5">Autonomous Revenue Recovery Intelligence — Synthetic Simulation</p>
        </div>
        <div className="badge badge-warning">⚠ Synthetic Data Only</div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Revenue at Risk" value={fmtK(metrics?.total_revenue_at_risk ?? 0)} icon={AlertTriangle} color="warning" />
        <MetricCard title="Total Recovered" value={fmtK(metrics?.total_recovered ?? 0)} icon={DollarSign} color="success" trend={5.2} />
        <MetricCard title="Recovery Rate" value={`${metrics?.recovery_rate_pct?.toFixed(1) ?? 0}%`} icon={Target} color="primary" />
        <MetricCard title="Net Recovered" value={fmtK(metrics?.net_recovered ?? 0)} sub={`After ₹${((metrics?.total_recovery_cost ?? 0) / 1000).toFixed(1)}K costs`} icon={TrendingUp} color="success" />
      </div>

      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Total Cases" value={String(metrics?.total_cases ?? 0)} icon={Users} color="muted" />
        <MetricCard title="Active Cases" value={String(metrics?.active_cases ?? 0)} icon={Clock} color="primary" />
        <MetricCard title="Escalated" value={String(metrics?.escalated_cases ?? 0)} icon={Users} color="warning" />
        <MetricCard title="Policy Blocks Prevented" value={String(metrics?.policy_violations_prevented ?? 0)} icon={Shield} color="success" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="col-span-2 glass-card p-5">
          <div className="text-sm font-semibold text-white mb-4">Recovery Trend (7 days)</div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={timeline}>
              <defs>
                <linearGradient id="gAt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#F59E0B" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gRec" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2230" />
              <XAxis dataKey="date" stroke="#94A3B8" tick={{ fontSize: 11 }} />
              <YAxis stroke="#94A3B8" tick={{ fontSize: 11 }} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip formatter={(v: number) => fmtK(v)} contentStyle={{ background: '#12141A', border: '1px solid #1E2230', borderRadius: 8 }} />
              <Area type="monotone" dataKey="revenue_at_risk" name="At Risk" stroke="#F59E0B" fill="url(#gAt)" strokeWidth={2} />
              <Area type="monotone" dataKey="recovered" name="Recovered" stroke="#10B981" fill="url(#gRec)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pie */}
        <div className="glass-card p-5">
          <div className="text-sm font-semibold text-white mb-4">Case Distribution</div>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#12141A', border: '1px solid #1E2230', borderRadius: 8 }} />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 11, color: '#94A3B8' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-muted text-sm">No cases yet.<br/>Run the simulation!</div>
          )}
        </div>
      </div>

      {/* Recent cases */}
      {metrics && metrics.recent_cases.length > 0 && (
        <div className="glass-card p-5">
          <div className="text-sm font-semibold text-white mb-4">Recent Cases</div>
          <div className="space-y-2">
            {metrics.recent_cases.slice(0, 5).map(c => (
              <div key={c.case_id} className="flex items-center justify-between py-2 border-b border-bg-border last:border-0">
                <div className="flex items-center gap-3">
                  <div className={`status-dot ${c.outcome_status === 'RECOVERED' ? 'status-dot-green' : c.outcome_status === 'PENDING' ? 'status-dot-amber' : 'status-dot-muted'}`} />
                  <div>
                    <div className="text-sm text-white font-mono">{c.case_id}</div>
                    <div className="text-xs text-muted">{c.root_cause?.replace(/_/g, ' ') || 'Pending diagnosis'}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-white">{fmt(c.revenue_at_risk)}</div>
                  <div className="text-xs text-muted">{c.outcome_status || c.status}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-xs text-muted/50 text-center pb-2">
        ⚠ All metrics calculated from synthetic simulation outcomes. Not actual payment processing results.
      </div>
    </div>
  );
}
