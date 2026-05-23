from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.dependencies.service_key import verify_service_key
from src.schemas.inventory import (
    ReserveRequest, ReserveSuccessResponse, ReserveFailedResponse,
    UnreserveRequest, UnreserveResponse, ErrorResponse
)
from src.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory"])

@router.post(
    "/reserve",
    response_model=ReserveSuccessResponse,
    status_code=200,
    responses={
        200: {"model": ReserveSuccessResponse},
        409: {"model": ReserveFailedResponse},
        401: {"model": ErrorResponse}
    }
)
def reserve(
    request: ReserveRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = InventoryService(db)
    result = service.reserve(request)
    
    if result.get("reserved") is False:
        return JSONResponse(status_code=409, content=result)
    
    return result

@router.post(
    "/unreserve",
    response_model=UnreserveResponse,
    status_code=200,
    responses={
        200: {"model": UnreserveResponse},
        401: {"model": ErrorResponse}
    }
)
def unreserve(
    request: UnreserveRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = InventoryService(db)
    result = service.unreserve(request)
    return result