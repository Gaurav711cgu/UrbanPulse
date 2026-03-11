import React from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './store/useStore'
import Sidebar from './components/Sidebar/Sidebar'
import StatsBar from './components/Dashboard/StatsBar'
import CityMap from './components/Map/CityMap'
import TrafficChart from './components/Charts/TrafficChart'
import SignalPanel from './components/Signals/SignalPanel'
import EmergencyFeed from './components/Dashboard/EmergencyFeed'

export default function App() {
  useWebSocket()
  const connected = useStore((s) => s.connected)

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--navy)' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header */}
        <header style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 20px', background: 'var(--card)',
          borderBottom: '1px solid var(--mid)', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--cyan)' }}>UrbanPulse</span>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>AI Traffic Control Dashboard</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className={`pulse`} style={{ background: connected ? 'var(--green)' : 'var(--red)' }} />
            <span style={{ fontSize: 12, color: connected ? 'var(--green)' : 'var(--red)' }}>
              {connected ? 'LIVE' : 'RECONNECTING...'}
            </span>
          </div>
        </header>

        {/* Stats bar */}
        <StatsBar />

        {/* Main content grid */}
        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 360px', gap: 12, padding: '0 12px 12px', overflow: 'hidden' }}>
          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflow: 'hidden' }}>
            <div style={{ flex: '0 0 320px' }}>
              <CityMap />
            </div>
            <div style={{ flex: 1, minHeight: 0 }}>
              <TrafficChart />
            </div>
          </div>
          {/* Right column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflow: 'auto' }}>
            <SignalPanel />
            <EmergencyFeed />
          </div>
        </div>
      </div>
    </div>
  )
}
