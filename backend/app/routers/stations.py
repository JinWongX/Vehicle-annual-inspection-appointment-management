from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, auth, crud
from ..database import get_db

router = APIRouter(prefix="/stations", tags=["stations"])

TIME_SLOTS = ["08:00-10:00", "10:00-12:00", "13:00-15:00", "15:00-17:00"]


def _slot_capacity(daily_capacity: int) -> int:
    return max(1, daily_capacity // len(TIME_SLOTS))


@router.post("/", response_model=schemas.StationResponse, status_code=status.HTTP_201_CREATED)
def create_station(
    station: schemas.StationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_role("admin")),
):
    return crud.create_station(db, station)


@router.get("/", response_model=List[schemas.StationResponse])
def list_stations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    return crud.list_stations(db, skip=skip, limit=limit)


@router.get("/available", response_model=List[schemas.StationAvailabilityResponse])
def list_available_stations(
    vehicle_type: str,
    date: date,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    stations = crud.list_stations(db)
    result = []
    target_type = vehicle_type.strip().lower()
    for station in stations:
        allowed = [
            t.strip().lower()
            for t in (station.allowed_vehicle_types or "").split(",")
            if t.strip()
        ]
        if target_type not in allowed:
            continue
        time_slots = []
        slot_capacity = _slot_capacity(station.daily_capacity)
        for slot in TIME_SLOTS:
            count = crud.count_appointments_in_slot(db, station.id, date, slot)
            remaining = max(0, slot_capacity - count)
            time_slots.append(schemas.TimeSlotAvailability(time_slot=slot, remaining=remaining))
        result.append(
            schemas.StationAvailabilityResponse(station=station, time_slots=time_slots)
        )
    return result


@router.get("/{station_id}", response_model=schemas.StationResponse)
def get_station(
    station_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    station = crud.get_station_by_id(db, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@router.put("/{station_id}", response_model=schemas.StationResponse)
def update_station(
    station_id: int,
    updates: schemas.StationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_role("admin")),
):
    station = crud.get_station_by_id(db, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return crud.update_station(db, station, updates)


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_station(
    station_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_role("admin")),
):
    station = crud.get_station_by_id(db, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    if station.appointments or station.staff:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该检测站存在关联的预约或工作人员，无法删除",
        )
    crud.delete_station(db, station)
    return None
