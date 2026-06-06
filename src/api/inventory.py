from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.dependencies.service_key import verify_service_key
from src.schemas.inventory import (
    ReserveRequest, ReserveSuccessResponse,
    UnreserveRequest, UnreserveResponse
)
from src.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory"])


@router.post("/reserve")
def reserve(
    request: ReserveRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = InventoryService(db)
    result = service.reserve(request)

    if "code" in result:
        status_code = {
            "INVALID_QUANTITY": 400,
            "SKU_NOT_FOUND": 404,
            "PARTIAL_INSUFFICIENT_STOCK": 409,
        }.get(result["code"], 409)

        return JSONResponse(
            status_code=status_code,
            content={
                "code": result["code"],
                "message": result["message"],
                "details": result.get("details")
            }
        )

    return result


@router.post("/unreserve")
def unreserve(
    request: UnreserveRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = InventoryService(db)
    result = service.unreserve(request)

    if "code" in result:
        status_code = {
            "INVALID_QUANTITY": 400,
            "SKU_NOT_FOUND": 404,
            "INSUFFICIENT_RESERVATION": 409,
        }.get(result["code"], 409)

        return JSONResponse(
            status_code=status_code,
            content={
                "code": result["code"],
                "message": result["message"],
                "details": result.get("details")
            }
        )

    return result