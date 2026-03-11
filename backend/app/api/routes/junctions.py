from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.db_models import Junction, SignalState
from app.schemas.schemas import JunctionCreate, JunctionOut, SignalStateOut, SignalOverrideIn
from app.services.signal_controller import SignalController

router = APIRouter()


@router.get("/", response_model=List[JunctionOut])
async def list_junctions(db: AsyncSession = Depends(get_db)):
    """Return all monitored junctions."""
    result = await db.execute(select(Junction).where(Junction.is_active == True))
    return result.scalars().all()


@router.get("/{junction_id}", response_model=JunctionOut)
async def get_junction(junction_id: int, db: AsyncSession = Depends(get_db)):
    junction = await db.get(Junction, junction_id)
    if not junction:
        raise HTTPException(status_code=404, detail="Junction not found")
    return junction


@router.post("/", response_model=JunctionOut, status_code=201)
async def create_junction(payload: JunctionCreate, db: AsyncSession = Depends(get_db)):
    junction = Junction(**payload.model_dump())
    db.add(junction)
    await db.flush()
    await db.refresh(junction)
    return junction


@router.get("/{junction_id}/state", response_model=SignalStateOut)
async def get_signal_state(junction_id: int, db: AsyncSession = Depends(get_db)):
    """Return the latest signal state for a junction."""
    result = await db.execute(
        select(SignalState)
        .where(SignalState.junction_id == junction_id)
        .order_by(SignalState.timestamp.desc())
        .limit(1)
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="No signal state found")
    return state


@router.post("/{junction_id}/override", response_model=SignalStateOut)
async def override_signal(
    junction_id: int,
    payload: SignalOverrideIn,
    db: AsyncSession = Depends(get_db),
):
    """Manually override a junction's signal phase."""
    junction = await db.get(Junction, junction_id)
    if not junction:
        raise HTTPException(status_code=404, detail="Junction not found")

    state = SignalState(
        junction_id=junction_id,
        phase=payload.phase,
        duration_seconds=payload.duration_seconds,
        is_emergency=False,
        decided_by="manual",
    )
    db.add(state)
    await db.flush()
    await db.refresh(state)
    return state
