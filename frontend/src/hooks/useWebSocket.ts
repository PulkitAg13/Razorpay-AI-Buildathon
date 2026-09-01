import { useEffect, useRef } from 'react';
import { useAppStore } from '../store';
import type { LiveEvent } from '../types';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/live-feed`;

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const { addLiveEvent, setWsConnected, setSimulationProgress, setSimulationResults, setSimulationRunning } = useAppStore();

  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      try {
        ws.current = new WebSocket(WS_URL);

        ws.current.onopen = () => {
          setWsConnected(true);
        };

        ws.current.onmessage = (e) => {
          try {
            const event: LiveEvent = JSON.parse(e.data);
            addLiveEvent(event);
            if (event.type === 'simulation_progress') {
              setSimulationProgress((event as unknown as { pct: number }).pct ?? 0);
            }
            if (event.type === 'simulation_complete') {
              setSimulationRunning(false);
              const result = (event as unknown as { results: unknown }).results;
              if (result) setSimulationResults(result as import('../types').SimulationResult);
            }
          } catch { /* ignore parse errors */ }
        };

        ws.current.onclose = () => {
          setWsConnected(false);
          reconnectTimeout = setTimeout(connect, 3000);
        };

        ws.current.onerror = () => {
          ws.current?.close();
        };
      } catch {
        reconnectTimeout = setTimeout(connect, 3000);
      }
    }

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      ws.current?.close();
    };
  }, []);
}
