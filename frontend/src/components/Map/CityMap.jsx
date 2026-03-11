import React, { useEffect, useRef } from 'react'
import { useStore } from '../../store/useStore'

// Nagpur junction coords
const JUNCTIONS = Array.from({ length: 16 }, (_, i) => ({
  id: i + 1,
  name: [
    'Sitabuldi Crossing','Dharampeth Square','Ramdaspeth Chowk','Shankar Nagar',
    'Laxmi Nagar Square','Bajaj Nagar','Pratap Nagar','Hingna T-Point',
    'Mankapur Circle','Gokulpeth Square','Wardhaman Nagar','Bhandara Road',
    'Kamptee Road Chowk','Wadi Junction','Itwari Square','Mahal Chowk'
  ][i],
  lat: 21.120 + (i % 4) * 0.015,
  lng: 79.080 + Math.floor(i / 4) * 0.015,
}))

function congestionColor(level) {
  if (level < 0.3) return '#10b981'
  if (level < 0.6) return '#f59e0b'
  return '#ef4444'
}

export default function CityMap() {
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const markers = useRef({})
  const trafficMap = useStore((s) => s.trafficMap)
  const signalMap = useStore((s) => s.signalMap)
  const selectJunction = useStore((s) => s.selectJunction)

  useEffect(() => {
    if (mapInstance.current) return
    if (typeof window === 'undefined') return

    import('leaflet').then((L) => {
      const map = L.default.map(mapRef.current, {
        center: [21.132, 79.088],
        zoom: 13,
        zoomControl: true,
      })

      L.default.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap © CartoDB',
        maxZoom: 18,
      }).addTo(map)

      JUNCTIONS.forEach((j) => {
        const marker = L.default.circleMarker([j.lat, j.lng], {
          radius: 10,
          fillColor: '#0d9488',
          color: '#22d3ee',
          weight: 2,
          fillOpacity: 0.9,
        })
          .addTo(map)
          .bindPopup(`<b>${j.name}</b><br/>Junction #${j.id}`)
          .on('click', () => selectJunction(j.id))

        markers.current[j.id] = marker
      })

      mapInstance.current = map
    })
  }, [])

  // Update marker colors on traffic changes
  useEffect(() => {
    if (!mapInstance.current) return
    Object.values(trafficMap).forEach((payload) => {
      const marker = markers.current[payload.junction_id]
      if (!marker) return
      const color = congestionColor(payload.congestion_level || 0)
      marker.setStyle({ fillColor: color, color: color })
      marker.bindPopup(`
        <b>${payload.junction_name}</b><br/>
        Vehicles: ${payload.total_vehicles}<br/>
        Congestion: ${Math.round((payload.congestion_level || 0) * 100)}%<br/>
        Signal: ${signalMap[payload.junction_id]?.phase_name || '—'}
      `)
    })
  }, [trafficMap, signalMap])

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', height: '100%', minHeight: 280 }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--mid)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--silver)' }}>🗺 City Junction Map</span>
        <div style={{ display: 'flex', gap: 10, fontSize: 11 }}>
          <span>🟢 Clear</span>
          <span>🟡 Moderate</span>
          <span>🔴 Heavy</span>
        </div>
      </div>
      <div ref={mapRef} style={{ height: 260, width: '100%' }} />
    </div>
  )
}
