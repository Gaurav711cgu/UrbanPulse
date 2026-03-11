import React from 'react'
import { useStore } from '../../store/useStore'

const icons = { ambulance: '🚑', fire_truck: '🚒', police: '🚔' }

export default function EmergencyFeed() {
  const emergencies = useStore((s) => s.emergencies)
  const clearEmergency = useStore((s) => s.clearEmergency)

  return (
    <div className="card" style={{ minHeight: 160 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--silver)' }}>🚨 Emergency Events</span>
        <span className="badge badge-red">{emergencies.length} active</span>
      </div>

      {emergencies.length === 0 ? (
        <div style={{ color: 'var(--muted)', fontSize: 12, textAlign: 'center', padding: '20px 0' }}>
          ✅ No active emergencies
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {emergencies.slice(0, 6).map((e, i) => (
            <div key={i} style={{
              background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 7, padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
            }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#fca5a5' }}>
                  {icons[e.vehicle_type] || '🚨'} {e.vehicle_type?.replace('_', ' ').toUpperCase()}
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
                  {e.junction_name} — Dir: {e.direction}
                </div>
                {e.estimated_time_saved_seconds && (
                  <div style={{ fontSize: 10, color: 'var(--green)', marginTop: 1 }}>
                    ⏱ ~{Math.round(e.estimated_time_saved_seconds / 60)} min saved
                  </div>
                )}
              </div>
              <button
                onClick={() => clearEmergency(e.junction_id)}
                style={{ background: 'none', border: '1px solid var(--muted)', borderRadius: 5,
                  color: 'var(--muted)', padding: '3px 8px', cursor: 'pointer', fontSize: 11 }}
              >
                Resolve
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
