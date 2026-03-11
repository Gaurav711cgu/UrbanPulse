import React from 'react'
import { useStore } from '../../store/useStore'

const PHASE_LABELS = {
  0: { label: 'NS GREEN',  color: '#10b981', icon: '🟢' },
  1: { label: 'NS YELLOW', color: '#f59e0b', icon: '🟡' },
  2: { label: 'EW GREEN',  color: '#10b981', icon: '🟢' },
  3: { label: 'EW YELLOW', color: '#f59e0b', icon: '🟡' },
}

const JUNCTION_NAMES = [
  'Sitabuldi', 'Dharampeth', 'Ramdaspeth', 'Shankar Ngr',
  'Laxmi Ngr', 'Bajaj Ngr', 'Pratap Ngr', 'Hingna T-Pt',
  'Mankapur', 'Gokulpeth', 'Wardhaman', 'Bhandara Rd',
  'Kamptee Rd', 'Wadi Jctn', 'Itwari Sq', 'Mahal Chowk',
]

export default function SignalPanel() {
  const signalMap = useStore((s) => s.signalMap)
  const trafficMap = useStore((s) => s.trafficMap)
  const junctions = Array.from({ length: 16 }, (_, i) => i + 1)

  return (
    <div className="card">
      <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--silver)', marginBottom: 10 }}>
        🚦 Signal States
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        {junctions.map((id) => {
          const sig = signalMap[id]
          const traf = trafficMap[id]
          const phase = sig?.phase ?? null
          const info = phase !== null ? PHASE_LABELS[phase] : null
          const congestion = traf?.congestion_level ?? null

          return (
            <div
              key={id}
              style={{
                background: 'rgba(14,58,94,0.4)',
                border: `1px solid ${info ? info.color + '55' : 'var(--mid)'}`,
                borderRadius: 7, padding: '6px 8px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--silver)' }}>
                  J{id} {JUNCTION_NAMES[id - 1]}
                </div>
                <div style={{ fontSize: 10, color: info?.color || 'var(--muted)', marginTop: 1 }}>
                  {info ? `${info.icon} ${info.label}` : '⏳ waiting'}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                {sig?.duration_seconds && (
                  <div style={{ fontSize: 11, color: 'var(--cyan)' }}>{sig.duration_seconds}s</div>
                )}
                {congestion !== null && (
                  <div style={{
                    fontSize: 10,
                    color: congestion > 0.7 ? '#ef4444' : congestion > 0.4 ? '#f59e0b' : '#10b981'
                  }}>
                    {Math.round(congestion * 100)}%
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
