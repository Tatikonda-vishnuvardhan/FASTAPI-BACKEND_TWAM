"""
app/shipment/router.py  (UPDATED)
──────────────────────────────────
Key change: /TrackShipment/{tracking_id} now calls track_shipment_live()
which queries Ekart Elite API for live events AND merges DB state.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, get_current_admin_user

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    prefix="/api/Shipment",
    tags=["Shipment"],
)


@router.post("", response_model=schemas.ShipmentResponse)
def create_shipment(command: schemas.CreateShipmentRequest, db: Session = Depends(get_db)):
    try:
        return repository.create_shipment(db, command)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/CancelShipment")
def cancel_shipment(command: schemas.CancelShipmentRequest, db: Session = Depends(get_db)):
    try:
        return {"success": repository.cancel_shipment(db, command.orderId)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/TrackShipment/{tracking_id}")
def track_shipment(tracking_id: str, db: Session = Depends(get_db)):
    """
    Returns LIVE tracking events from Ekart Elite API merged with DB state.
    Falls back to DB-only data if Ekart API is unreachable.
    """
    result = repository.track_shipment_live(db, tracking_id)
    if not result.get("trackingId"):
        raise HTTPException(status_code=404, detail="Tracking ID not found.")
    return result


@router.post("/GetShipmentOrderDetail", response_model=schemas.ShipmentData)
def get_shipment_order_detail(command: schemas.ShipmentDataRequest, db: Session = Depends(get_db)):
    try:
        return repository.get_shipment_data(db, command.orderId)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/GetDelhiveryShipmentOrderDetail", response_model=schemas.DelhiveryShipmentData)
def get_delhivery_shipment_detail(command: schemas.ShipmentDataRequest, db: Session = Depends(get_db)):
    try:
        return repository.get_delhivery_shipment_data(db, command.orderId)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/CreateDelhiveryShipment")
def create_delhivery_shipment(command: schemas.CreateDelhiveryShipmentRequest, db: Session = Depends(get_db)):
    try:
        return {"result": repository.create_delhivery_shipment(db, command)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/GetReturnShipmentOrderDetail", response_model=schemas.ReturnShipmentData)
def get_return_shipment_detail(command: schemas.ShipmentDataRequest, db: Session = Depends(get_db)):
    try:
        return repository.get_return_shipment_data(db, command.orderId)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/CreateReturnShipment")
def create_return_shipment(command: schemas.CreateReturnShipmentRequest, db: Session = Depends(get_db)):
    try:
        return {"result": repository.create_return_shipment(db, command)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))