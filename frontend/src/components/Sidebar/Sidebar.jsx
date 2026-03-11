import React from 'react'
import { useStore } from '../../store/useStore'

const NAV = [
  { icon: '📊', label: 'Dashboard' },
  { icon: '🗺', label: 'Map View' },
  { icon: '🚦', label: 'Signals' },
  { icon: '📈', label: 'Analytics' },
  { icon: '🚨', label: 'Emergency' },
  { icon: '⚙️', label: 'Settings' },
]

export default function Sidebar() {
  const [active, setActive] = React.useState('Dashboard')
  const connected = useStore((s) => s.connected)
  const emergencies = useStore((s) => s.emergencies)

  return (
    <div style={{
      width: 64, background: 'var(--card)', borderRight: '1px solid var(--mid)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      paddingTop: 16, gap: 4, flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{ fontSize: 22, marginBottom: 16 }}>🏙️</div>

      {NAV.map(({ icon, label }) => (
        <button
          key={label}
          title={label}
          onClick={() => setActive(label)}
          style={{
            background: active === label ? 'rgba(13,148,136,0.2)' : 'none',
            border: active === label ? '1px solid var(--teal)' : '1px solid transparent',
            borderRadius: 8, width: 44, height: 44,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', position: 'relative', fontSize: 18,
          }}
        >
          {icon}
          {label === 'Emergency' && emergencies.length > 0 && (
            <span style={{
              position: 'absolute', top: 4, right: 4,
              background: 'var(--red)', color: '#fff',
              borderRadius: 999, fontSize: 9, padding: '1px 4px', fontWeight: 700,
            }}>
              {emergencies.length}
            </span>
          )}
        </button>
      ))}

      {/* Status dot at bottom */}
      <div style={{ marginTop: 'auto', marginBottom: 16 }}>
        <div className="pulse" style={{ background: connected ? 'var(--green)' : 'var(--red)' }} />
      </div>
    </div>
  )
}
