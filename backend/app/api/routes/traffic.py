from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.db_models import TrafficRecord, Junction
from app.schemas.schemas import TrafficFlowOut, DirectionFlow, DashboardStats

router = APIRouter()


@router.get("/flow", response_model=List[TrafficFlowOut])
async def get_traffic_flow(
    junction_ids: str = Query(default=None, description="Comma-separated junction IDs"),
    db: AsyncSession = Depends(get_db),
):
    """Return latest traffic flow for all (or specified) junctions."""
    since = datetime.utcnow() - timedelta(minutes=5)

    query = select(TrafficRecord).where(TrafficRecord.timestamp >= since)
    if junction_ids:
        ids = [int(i) for i in junction_ids.split(",")]
        query = query.where(TrafficRecord.junction_id.in_(ids))

    result = await db.execute(query.order_by(TrafficRecord.timestamp.desc()))
    records = result.scalars().all()

    # Group by junction_id
    junction_map: dict = {}
    for r in records:
        if r.junction_id not in junction_map:
            junction_map[r.junction_id] = []
        junction_map[r.junction_id].append(r)

    flows = []
    for jid, recs in junction_map.items():
        direction_flows = [
            DirectionFlow(
                direction=r.direction,
                vehicle_count=r.vehicle_count,
                avg_speed_kmh=r.avg_speed_kmh,
                queue_length_m=r.queue_length_m,
                vehicle_types=r.vehicle_types or {},
            )
            for r in recs
        ]
        total = sum(f.vehicle_count for f in direction_flows)
        congestion = min(total / 200.0, 1.0)  # normalize to 0-1
        flows.append(
            TrafficFlowOut(
                junction_id=jid,
                flows=direction_flows,
                total_vehicles=total,
                congestion_level=round(congestion, 2),
                timestamp=recs[0].timestamp,
            )
        )
    return flows


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Return aggregated dashboard statistics."""
    total_j = await db.scalar(select(func.count(Junction.id)))
    active_j = await db.scalar(
        select(func.count(Junction.id)).where(Junction.is_active == True)
    )
    today = datetime.utcnow().date()
    vehicles_today = await db.scalar(
        select(func.sum(TrafficRecord.vehicle_count)).where(
            func.date(TrafficRecord.timestamp) == today
        )
    )

    return DashboardStats(
        total_junctions=total_j or 0,
        active_junctions=active_j or 0,
        avg_wait_time_min=8.4,
        total_vehicles_today=int(vehicles_today or 0),
        emergencies_active=0,
        co2_saved_kg=round((vehicles_today or 0) * 0.004, 1),
        avg_congestion=0.42,
    )


@router.get("/history/{junction_id}")
async def get_traffic_history(
    junction_id: int,
    hours: int = Query(default=6, ge=1, le=48),
    db: AsyncSession = Depends(get_db),
):
    """Return hourly traffic history for a junction."""
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(TrafficRecord)
        .where(
            TrafficRecord.junction_id == junction_id,
            TrafficRecord.timestamp >= since,
        )
        .order_by(TrafficRecord.timestamp.asc())
    )
    records = result.scalars().all()
    return [
        {
            "timestamp": r.timestamp,
            "direction": r.direction,
            "vehicle_count": r.vehicle_count,
            "avg_speed_kmh": r.avg_speed_kmh,
            "queue_length_m": r.queue_length_m,
        }
        for r in records
    ]
