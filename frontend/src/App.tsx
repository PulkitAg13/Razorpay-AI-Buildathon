import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import LiveFeed from './pages/LiveFeed';
import CaseExplorer from './pages/CaseExplorer';
import AgentObservatory from './pages/AgentObservatory';
import SimulationLab from './pages/SimulationLab';
import HumanReviewPage from './pages/HumanReview';
import AuditExplorer from './pages/AuditExplorer';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="live" element={<LiveFeed />} />
          <Route path="cases" element={<CaseExplorer />} />
          <Route path="agents" element={<AgentObservatory />} />
          <Route path="lab" element={<SimulationLab />} />
          <Route path="review" element={<HumanReviewPage />} />
          <Route path="audit" element={<AuditExplorer />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
