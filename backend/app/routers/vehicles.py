from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, auth, crud
from ..database import get_db

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("/", response_model=schemas.VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    vehicle: schemas.VehicleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    if crud.get_vehicle_by_plate(db, vehicle.plate_number):
        raise HTTPException(status_code=400, detail="Plate number already registered")
    vehicle_data = vehicle.model_dump()
    if not vehicle_data.get("next_inspection_date") and vehicle_data.get("register_date"):
        vehicle_data["next_inspection_date"] = crud.calculate_next_inspection_date(vehicle_data["register_date"])
    vehicle_in = schemas.VehicleCreate(**vehicle_data)
    owner_id = current_user.id if current_user.role == "owner" else (getattr(vehicle, "owner_id", None) or current_user.id)
    return crud.create_vehicle(db, vehicle_in, owner_id)


@router.get("/", response_model=List[schemas.VehicleResponse])
def list_vehicles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    if current_user.role == "owner":
        return crud.list_vehicles_by_owner(db, current_user.id, skip=skip, limit=limit)
    return crud.list_vehicles(db, skip=skip, limit=limit)


@router.get("/{vehicle_id}", response_model=schemas.VehicleResponse)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    vehicle = crud.get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if current_user.role == "owner" and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return vehicle


@router.put("/{vehicle_id}", response_model=schemas.VehicleResponse)
def update_vehicle(
    vehicle_id: int,
    updates: schemas.VehicleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    vehicle = crud.get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if current_user.role == "owner" and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    update_data = updates.model_dump(exclude_unset=True)
    if update_data.get("register_date") and not update_data.get("next_inspection_date"):
        update_data["next_inspection_date"] = crud.calculate_next_inspection_date(update_data["register_date"])
    vehicle_updates = schemas.VehicleUpdate(**update_data)
    return crud.update_vehicle(db, vehicle, vehicle_updates)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    vehicle = crud.get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if current_user.role == "owner" and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    if vehicle.appointments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该车辆存在关联的预约，无法删除",
        )
    crud.delete_vehicle(db, vehicle)
    return None
