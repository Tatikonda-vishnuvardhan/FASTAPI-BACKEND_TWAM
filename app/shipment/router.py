from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Shipment", tags=["Shipment"])


@router.post("/", response_model=schemas.ShipmentResponse)
def create_shipment(command: schemas.CreateShipmentRequest, db: Session = Depends(get_db)):
    try:
        result = repository.create_shipment(db, command)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/CancelShipment")
def cancel_shipment(command: schemas.CancelShipmentRequest, db: Session = Depends(get_db)):
    try:
        result = repository.cancel_shipment(db, command.orderId)
        return {"success": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/TrackShipment/{tracking_id}")
def track_shipment(tracking_id: str):
    # TODO: Integrate IDeliveryService.TrackShipmentAsync
    return {"trackingId": tracking_id, "message": "TODO: Integrate delivery service tracking."}


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
        result = repository.create_delhivery_shipment(db, command)
        return {"result": result}
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
        result = repository.create_return_shipment(db, command)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))