import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import type { TraceRow } from '../components/LiveTraceFeed';

export interface AgentStep {
  id: number;
  incident_id: string;
  service: string;
  step_order: number;
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_output: Record<string, unknown>;
  status: string;
  created_at: string;
}

export interface Report {
  id: number;
  incident_id: string;
  service: string;
  root_cause: string;
  impact_level: string;
  explanation: string;
  recommended_action: string;
  confidence_score: number;
  evidence: string[];
  gemma_model: string;
  tools_used: string[];
  created_at: string;
}

export interface IncidentData {
  incident: { incident_id: string; service: string; created_at: string } | null;
  report: Report | null;
  steps: AgentStep[];
  analyzing: boolean;
  analysis_status: string | null;
}

export interface SystemStatus {
  analysis_states: Record<string, string>;
  incident_ids: Record<string, string>;
  availability: string;
  confidence: string;
  report_count: number;
  gemma_model: string;
}

export function useIncident() {
  const [incident, setIncident] = useState<IncidentData | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [traces, setTraces] = useState<TraceRow[]>([]);
  const [triggering, setTriggering] = useState(false);
  const [connected, setConnected] = useState(true);
  const [highlightIds, setHighlightIds] = useState<Set<number>>(new Set());
  const prevTraceIds = useRef<Set<number>>(new Set());

  const fetchAll = useCallback(async () => {
    try {
      const [incRes, statusRes, tracesRes] = await Promise.all([
        axios.get<IncidentData>('/api/v1/incidents/latest'),
        axios.get<SystemStatus>('/api/v1/system-status'),
        axios.get<TraceRow[]>('/api/v1/traces'),
      ]);
      setIncident(incRes.data);
      setStatus(statusRes.data);
      const newTraces = tracesRes.data;

      const newIds = new Set<number>();
      for (const t of newTraces) {
        if (!prevTraceIds.current.has(t.id)) {
          newIds.add(t.id);
        }
      }
      prevTraceIds.current = new Set(newTraces.map((t) => t.id));
      if (newIds.size > 0) {
        setHighlightIds(newIds);
        setTimeout(() => setHighlightIds(new Set()), 1500);
      }

      setTraces(newTraces);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }, []);

  const triggerSpike = async () => {
    setTriggering(true);
    prevTraceIds.current = new Set(traces.map((t) => t.id));
    try {
      await axios.post('/api/v1/demo/trigger-spike');
    } finally {
      setTriggering(false);
    }
    await fetchAll();
  };

  const analyzing = incident?.analyzing ?? false;

  useEffect(() => {
    fetchAll();
    const ms = analyzing ? 800 : 2500;
    const interval = setInterval(fetchAll, ms);
    return () => clearInterval(interval);
  }, [fetchAll, analyzing]);

  const errorRate = (() => {
    const payment = traces.filter((t) => t.service === 'payment-service');
    if (payment.length === 0) return undefined;
    const errors = payment.filter((t) => t.status === 'error').length;
    return errors / payment.length;
  })();

  return {
    incident,
    status,
    traces,
    triggerSpike,
    triggering,
    connected,
    highlightIds,
    analyzing,
    errorRate,
    refetch: fetchAll,
  };
}
