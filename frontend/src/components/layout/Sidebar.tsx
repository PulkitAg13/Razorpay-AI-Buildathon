import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAppStore } from '../../store';
import {
  LayoutDashboard, Zap, Search, Eye, FlaskConical,
  UserCheck, ScrollText, Activity, Wifi, WifiOff
} from 'lucide-react';

const NAV = [
  { to: '/',              icon: LayoutDashboard, label: 'Executive Dashboard' },
  { to: '/live',          icon: Zap,             label: 'Live Recovery Feed' },
  { to: '/cases',         icon: Search,          label: 'Case Explorer' },
  { to: '/agents',        icon: Eye,             label: 'Agent Observatory' },
  { to: '/lab',           icon: FlaskConical,    label: 'Simulation Lab' },
  { to: '/review',        icon: UserCheck,       label: 'Human Review' },
  { to: '/audit',         icon: ScrollText,      label: 'Audit Explorer' },
];

export function Layout() {
  useWebSocket();
  const wsConnected = useAppStore(s => s.wsConnected);
  const liveEvents = useAppStore(s => s.liveEvents);
  const location = useLocation();

  const recentActivity = liveEvents.filter(e => e.type === 'agent_step').length;

  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 flex flex-col border-r border-bg-border bg-bg-card">
        {/* Logo */}
        <div className="p-5 border-b border-bg-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white font-bold text-sm">RX</div>
            <div>
              <div className="text-sm font-bold text-white tracking-wide">RECOVERX AI</div>
              <div className="text-xs text-muted">Revenue Recovery OS</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => isActive ? 'nav-item-active block' : 'nav-item block'}
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-bg-border space-y-2">
          <div className="flex items-center gap-2 text-xs">
            {wsConnected
              ? <><Wifi size={12} className="text-success" /><span className="text-success">Live Feed Connected</span></>
              : <><WifiOff size={12} className="text-muted" /><span className="text-muted">Connecting...</span></>
            }
          </div>
          <div className="flex items-center gap-2 text-xs text-muted">
            <Activity size={12} className="text-primary" />
            <span>{recentActivity} agent steps</span>
          </div>
          <div className="text-xs text-muted/60 leading-tight">
            Synthetic simulation data.<br/>Not real transactions.
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
