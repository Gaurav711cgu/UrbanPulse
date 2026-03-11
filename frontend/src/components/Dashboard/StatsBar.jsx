import React from 'react'
import { useStore } from '../../store/useStore'

const StatCard = ({ label, value, sub, color = 'var(--cyan)' }) => (
  <div style={{
    flex: 1, background: 'var(--card)', border: '1px solid var(--mid)',
    borderRadius: 8, padding: '10px 16px', minWidth: 0,
  }}>
    <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
    <div style={{ fontSize: 11, color: 'var(--silver)', marginTop: 2 }}>{label}</div>
    {sub && <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 1 }}>{sub}</div>}
  </div>
)

export default function StatsBar() {
  const stats = useStore((s) => s.stats)
  const trafficMap = useStore((s) => s.trafficMap)
  const activeJunctions = Object.keys(trafficMap).length || stats.active_junctions

  return (
    <div style={{ display: 'flex', gap: 10, padding: '10px 12px', flexShrink: 0 }}>
      <StatCard
        label="Active Junctions"
        value={activeJunctions || 16}
        sub="Monitored intersections"
        color="var(--cyan)"
      />
      <StatCard
        label="Avg Wait Time"
        value={`${stats.avg_wait_time_min || 8.4} min`}
        sub="vs 14.2 min baseline"
        color="var(--green)"
      />
      <StatCard
        label="Vehicles Today"
        value={(stats.total_vehicles_today || 0).toLocaleString()}
        sub="Processed through AI control"
        color="var(--accent)"
      />
      <StatCard
        label="Avg Congestion"
        value={`${Math.round((stats.avg_congestion || 0.42) * 100)}%`}
        sub="City-wide average"
        color={stats.avg_congestion > 0.7 ? 'var(--red)' : 'var(--green)'}
      />
      <StatCard
        label="CO₂ Saved"
        value={`${(stats.co2_saved_kg || 0).toFixed(0)} kg`}
        sub="From reduced idling"
        color="var(--green)"
      />
      <StatCard
        label="Emergencies Resolved"
        value={stats.emergencies_resolved_today || 0}
        sub="Today"
        color="var(--accent)"
      />
    </div>
  )
}
