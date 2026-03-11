from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Junction(Base):
    __tablename__ = "junctions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    num_phases = Column(Integer, default=4)
    is_active = Column(Boolean, default=True)
    has_camera = Column(Boolean, default=True)
    has_sensors = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    signals = relationship("SignalState", back_populates="junction", lazy="select")
    traffic_records = relationship("TrafficRecord", back_populates="junction", lazy="select")


class SignalState(Base):
    __tablename__ = "signal_states"

    id = Column(Integer, primary_key=True, index=True)
    junction_id = Column(Integer, ForeignKey("junctions.id"), nullable=False)
    phase = Column(Integer, nullable=False)       # 0=N-S Green, 1=N-S Yellow, 2=E-W Green, 3=E-W Yellow
    duration_seconds = Column(Integer, nullable=False)
    is_emergency = Column(Boolean, default=False)
    decided_by = Column(String, default="dqn")    # 'dqn' | 'manual' | 'emergency'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    junction = relationship("Junction", back_populates="signals")


class TrafficRecord(Base):
    __tablename__ = "traffic_records"

    id = Column(Integer, primary_key=True, index=True)
    junction_id = Column(Integer, ForeignKey("junctions.id"), nullable=False)
    direction = Column(String, nullable=False)   # 'N', 'S', 'E', 'W'
    vehicle_count = Column(Integer, default=0)
    avg_speed_kmh = Column(Float, default=0.0)
    queue_length_m = Column(Float, default=0.0)
    vehicle_types = Column(JSON, default=dict)   # {"car": 10, "bus": 2, "truck": 1}
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    junction = relationship("Junction", back_populates="traffic_records")


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"

    id = Column(Integer, primary_key=True, index=True)
    junction_id = Column(Integer, ForeignKey("junctions.id"), nullable=False)
    vehicle_type = Column(String, default="ambulance")   # 'ambulance' | 'fire' | 'police'
    direction = Column(String, nullable=False)
    time_saved_seconds = Column(Float, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
