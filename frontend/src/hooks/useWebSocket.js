import { useEffect, useRef } from 'react'
import { useStore } from '../store/useStore'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/live'

export function useWebSocket() {
  const ws = useRef(null)
  const { setConnected, updateTraffic, updateSignal, addEmergency, updateStats, pushChartPoint } = useStore()

  useEffect(() => {
    function connect() {
      ws.current = new WebSocket(WS_URL)

      ws.current.onopen = () => {
        setConnected(true)
        console.log('[WS] Connected')
      }

      ws.current.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data)
          const { event_type, payload } = event

          if (event_type === 'traffic_update') {
            updateTraffic(payload)
            // Push to chart history
            pushChartPoint(payload.junction_id, {
              time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              vehicles: payload.total_vehicles,
              congestion: payload.congestion_level,
            })
          } else if (event_type === 'signal_change') {
            updateSignal(payload)
          } else if (event_type === 'emergency') {
            addEmergency(payload)
          } else if (event_type === 'stats') {
            updateStats(payload)
          }
        } catch (err) {
          console.warn('[WS] Parse error', err)
        }
      }

      ws.current.onclose = () => {
        setConnected(false)
        console.log('[WS] Disconnected — retrying in 3s')
        setTimeout(connect, 3000)
      }

      ws.current.onerror = (err) => {
        console.error('[WS] Error', err)
        ws.current.close()
      }
    }

    connect()
    return () => {
      if (ws.current) ws.current.close()
    }
  }, [])
}
