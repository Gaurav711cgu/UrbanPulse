import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { useStore } from '../../store/useStore'

export default function TrafficChart() {
  const [selectedJunction, setSelectedJunction] = useState(1)
  const chartHistory = useStore((s) => s.chartHistory)
  const data = chartHistory[selectedJunction] || []

  const junctionOptions = Array.from({ length: 16 }, (_, i) => i + 1)

  return (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--silver)' }}>📈 Live Traffic Flow</span>
        <select
          value={selectedJunction}
          onChange={(e) => setSelectedJunction(Number(e.target.value))}
          style={{
            background: 'var(--mid)', border: '1px solid var(--muted)', color: 'var(--silver)',
            borderRadius: 6, padding: '4px 10px', fontSize: 12, cursor: 'pointer'
          }}
        >
          {junctionOptions.map((id) => (
            <option key={id} value={id}>Junction #{id}</option>
          ))}
        </select>
      </div>

      {data.length < 2 ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 13 }}>
          Waiting for live data...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%" minHeight={140}>
          <AreaChart data={data} margin={{ top: 4, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="vehicleGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#0d9488" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="congGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
            <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: '#112240', border: '1px solid #0e3a5e', borderRadius: 8 }}
              labelStyle={{ color: '#cbd5e1' }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
            <Area type="monotone" dataKey="vehicles" stroke="#0d9488" fill="url(#vehicleGrad)" strokeWidth={2} dot={false} name="Vehicles" />
            <Area type="monotone" dataKey="congestion" stroke="#f59e0b" fill="url(#congGrad)" strokeWidth={2} dot={false} name="Congestion" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
