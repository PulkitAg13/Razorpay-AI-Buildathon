import { create } from 'zustand';
import type { DashboardMetrics, LiveEvent, SimulationResult } from '../types';

interface AppStore {
  metrics: DashboardMetrics | null;
  setMetrics: (m: DashboardMetrics) => void;
  liveEvents: LiveEvent[];
  addLiveEvent: (e: LiveEvent) => void;
  wsConnected: boolean;
  setWsConnected: (v: boolean) => void;
  simulationResults: SimulationResult | null;
  setSimulationResults: (r: SimulationResult) => void;
  simulationRunning: boolean;
  setSimulationRunning: (v: boolean) => void;
  simulationProgress: number;
  setSimulationProgress: (n: number) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  metrics: null,
  setMetrics: (m) => set({ metrics: m }),
  liveEvents: [],
  addLiveEvent: (e) => set((s) => ({ liveEvents: [e, ...s.liveEvents].slice(0, 200) })),
  wsConnected: false,
  setWsConnected: (v) => set({ wsConnected: v }),
  simulationResults: null,
  setSimulationResults: (r) => set({ simulationResults: r }),
  simulationRunning: false,
  setSimulationRunning: (v) => set({ simulationRunning: v }),
  simulationProgress: 0,
  setSimulationProgress: (n) => set({ simulationProgress: n }),
}));
