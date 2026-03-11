import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // Connection
  connected: false,
  setConnected: (v) => set({ connected: v }),

  // Junctions
  junctions: [],
  setJunctions: (j) => set({ junctions: j }),
  selectedJunctionId: null,
  selectJunction: (id) => set({ selectedJunctionId: id }),

  // Live traffic state — map of junction_id → latest traffic update
  trafficMap: {},
  updateTraffic: (payload) =>
    set((s) => ({
      trafficMap: { ...s.trafficMap, [payload.junction_id]: payload },
    })),

  // Signal states — map of junction_id → latest signal
  signalMap: {},
  updateSignal: (payload) =>
    set((s) => ({
      signalMap: { ...s.signalMap, [payload.junction_id]: payload },
    })),

  // Emergency events
  emergencies: [],
  addEmergency: (e) =>
    set((s) => ({ emergencies: [e, ...s.emergencies].slice(0, 20) })),
  clearEmergency: (jid) =>
    set((s) => ({ emergencies: s.emergencies.filter((e) => e.junction_id !== jid) })),

  // Dashboard stats
  stats: {
    avg_wait_time_min: 0,
    total_vehicles_today: 0,
    active_junctions: 0,
    avg_congestion: 0,
    co2_saved_kg: 0,
    emergencies_resolved_today: 0,
  },
  updateStats: (s) => set({ stats: s }),

  // Traffic history for charts: junction_id → [{time, count}]
  chartHistory: {},
  pushChartPoint: (junctionId, point) =>
    set((s) => {
      const prev = s.chartHistory[junctionId] || []
      return {
        chartHistory: {
          ...s.chartHistory,
          [junctionId]: [...prev, point].slice(-60),
        },
      }
    }),
}))
