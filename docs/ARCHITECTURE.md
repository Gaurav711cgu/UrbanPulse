# UrbanPulse — Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EDGE LAYER                               │
│  CCTV Cameras  →  YOLOv8 on Jetson  →  MQTT  →  Kafka         │
│  IoT Sensors   →  Raw counts/speed  →  MQTT  →  Kafka         │
│  GPS Vehicles  →  Position data     →  REST   →  Backend       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PROCESSING LAYER                            │
│                                                                 │
│  FastAPI Backend                                                │
│  ├── Kafka Consumer (real-time ingestion)                       │
│  ├── Redis Cache (latest states per junction)                   │
│  ├── PostgreSQL + TimescaleDB (time-series history)             │
│  ├── LSTM Service (demand forecasting)                          │
│  ├── Signal Controller (DQN inference loop)                     │
│  └── WebSocket broadcaster (→ frontend)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                            │
│  React Dashboard  ←  WebSocket  ←  Backend                     │
│  Bus Operator App ←  REST API   ←  Backend                     │
│  Emergency Portal ←  REST API   ←  Backend                     │
└─────────────────────────────────────────────────────────────────┘
```

## AI Pipeline

```
Camera Frame
    │
    ▼
YOLOv8 Detection
    │
    ├── vehicle_count per lane
    ├── vehicle_types dict
    └── avg_speed estimate
         │
         ▼
    State Vector: [ns_count, ew_count, ns_queue, ew_queue, phase, time]
         │
         ├──────────────► LSTM Forecaster → predicted demand (t+5 to t+15 min)
         │
         └──────────────► DQN Agent → action (phase + duration)
                                │
                                ▼
                      Signal Hardware / SUMO
```

## Data Flow

1. **Sense** — Camera + sensor data arrives via MQTT every 2 seconds
2. **Ingest** — Kafka consumer writes to TimescaleDB + Redis
3. **Analyze** — LSTM model pulls last 30 samples, predicts next 15 min
4. **Decide** — DQN agent reads Redis state, outputs (phase, duration)
5. **Act** — Signal command sent to hardware; WebSocket broadcasts to dashboard
6. **Learn** — Every night, new data used to retrain LSTM; RL agent continues online

## Database Schema

```
junctions         — static junction metadata
signal_states     — time-series signal decisions (partitioned by day)
traffic_records   — time-series vehicle counts (partitioned by day)
emergency_events  — emergency vehicle incidents
```

## Security

- All external connections over TLS 1.3
- JWT authentication for API endpoints
- Edge devices store no PII; only anonymized flow data
- GDPR-aligned: no facial recognition, no license plate storage
