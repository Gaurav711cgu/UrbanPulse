from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import IntEnum


class Phase(IntEnum):
    NS_GREEN = 0
    NS_YELLOW = 1
    EW_GREEN = 2
    EW_YELLOW = 3


# ── Junction ──────────────────────────────────────────────────

class JunctionBase(BaseModel):
    name: str
    lat: float
    lng: float
    num_phases: int = 4
    has_camera: bool = True
    has_sensors: bool = False


class JunctionCreate(JunctionBase):
    pass


class JunctionOut(JunctionBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Signal State ──────────────────────────────────────────────

class SignalStateOut(BaseModel):
    junction_id: int
    phase: Phase
    duration_seconds: int
    is_emergency: bool
    decided_by: str
    timestamp: datetime

    class Config:
        from_attributes = True


class SignalOverrideIn(BaseModel):
    phase: Phase
    duration_seconds: int = Field(ge=5, le=120)
    reason: Optional[str] = None


# ── Traffic ───────────────────────────────────────────────────

class DirectionFlow(BaseModel):
    direction: str
    vehicle_count: int
    avg_speed_kmh: float
    queue_length_m: float
    vehicle_types: Dict[str, int] = {}


class TrafficFlowOut(BaseModel):
    junction_id: int
    flows: List[DirectionFlow]
    total_vehicles: int
    congestion_level: float   # 0.0 – 1.0
    timestamp: datetime


# ── Forecast ──────────────────────────────────────────────────

class ForecastPoint(BaseModel):
    minutes_ahead: int
    predicted_vehicles: float
    confidence: float


class ForecastOut(BaseModel):
    junction_id: int
    direction: str
    horizon_minutes: int
    predictions: List[ForecastPoint]
    generated_at: datetime


# ── WebSocket events ──────────────────────────────────────────

class LiveEvent(BaseModel):
    event_type: str    # 'traffic_update' | 'signal_change' | 'emergency' | 'stats'
    payload: dict
    timestamp: datetime


# ── Dashboard stats ───────────────────────────────────────────

class DashboardStats(BaseModel):
    total_junctions: int
    active_junctions: int
    avg_wait_time_min: float
    total_vehicles_today: int
    emergencies_active: int
    co2_saved_kg: float
    avg_congestion: float
