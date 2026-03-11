from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.models.db_models import TrafficRecord, Junction
from app.schemas.schemas import ForecastOut, ForecastPoint
from app.services.lstm_service import LSTMForecastService

router = APIRouter()

_forecast_service: LSTMForecastService | None = None


def get_forecast_service() -> LSTMForecastService:
    global _forecast_service
    if _forecast_service is None:
        _forecast_service = LSTMForecastService()
    return _forecast_service


@router.get("/{junction_id}", response_model=ForecastOut)
async def get_forecast(
    junction_id: int,
    direction: str = Query(default="N", regex="^[NSEW]$"),
    horizon: int = Query(default=15, ge=5, le=60, description="Minutes ahead to forecast"),
    db: AsyncSession = Depends(get_db),
    svc: LSTMForecastService = Depends(get_forecast_service),
):
    """
    Predict traffic demand for the next `horizon` minutes at a junction
    in a given direction using the LSTM forecasting model.
    """
    junction = await db.get(Junction, junction_id)
    if not junction:
        raise HTTPException(status_code=404, detail="Junction not found")

    # Pull last 60 minutes of data as input sequence
    result = await db.execute(
        select(TrafficRecord)
        .where(
            TrafficRecord.junction_id == junction_id,
            TrafficRecord.direction == direction,
        )
        .order_by(TrafficRecord.timestamp.desc())
        .limit(30)
    )
    records = list(reversed(result.scalars().all()))

    if len(records) < 5:
        # Not enough history — return heuristic forecast
        predictions = svc.heuristic_forecast(horizon)
    else:
        counts = [r.vehicle_count for r in records]
        predictions = svc.predict(counts, horizon_minutes=horizon)

    return ForecastOut(
        junction_id=junction_id,
        direction=direction,
        horizon_minutes=horizon,
        predictions=predictions,
        generated_at=datetime.utcnow(),
    )
