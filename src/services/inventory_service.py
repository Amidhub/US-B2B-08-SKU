from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID
from datetime import datetime
from src.models.sku import SKU
from src.models.reserve_operation import ReserveOperation
from src.models.unreserve_operation import UnreserveOperation
from src.schemas.inventory import (
    ReserveRequest, ReserveSuccessResponse, ReserveFailedResponse, ReserveFailedItem,
    UnreserveRequest, UnreserveResponse
)

class InventoryService:
    def __init__(self, db: Session):
        self.db = db
    
    def reserve(self, request: ReserveRequest) -> dict:
        """All-or-nothing резервирование с SELECT FOR UPDATE"""
        
        existing = self.db.query(ReserveOperation).filter(
            ReserveOperation.idempotency_key == str(request.idempotency_key)
        ).first()
        
        if existing:
            return existing.result
        
        try:
            sku_ids = [item.sku_id for item in request.items]
            skus = self.db.query(SKU).filter(
                SKU.id.in_(sku_ids)
            ).with_for_update().all()
            
            sku_map = {sku.id: sku for sku in skus}
            
            failed_items = []
            for item in request.items:
                sku = sku_map.get(item.sku_id)
                if not sku:
                    failed_items.append(ReserveFailedItem(
                        sku_id=item.sku_id,
                        requested=item.quantity,
                        available=0,
                        reason="SKU_NOT_FOUND"
                    ))
                elif sku.active_quantity == 0:
                    failed_items.append(ReserveFailedItem(
                        sku_id=item.sku_id,
                        requested=item.quantity,
                        available=0,
                        reason="OUT_OF_STOCK"
                    ))
                elif sku.active_quantity < item.quantity:
                    failed_items.append(ReserveFailedItem(
                        sku_id=item.sku_id,
                        requested=item.quantity,
                        available=sku.active_quantity,
                        reason="INSUFFICIENT_STOCK"
                    ))
            
            if failed_items:
                self.db.rollback()
                response_data = {
                "reserved": False,
                "failed_items": [
                    {
                        "sku_id": str(item.sku_id),  # ← превращаем UUID в строку
                        "requested": item.requested,
                        "available": item.available,
                        "reason": item.reason
                    }
                    for item in failed_items
                    ]
                }
                
                op = ReserveOperation(
                    idempotency_key=str(request.idempotency_key),
                    result=response_data
                )
                self.db.add(op)
                self.db.commit()
                return response_data
            
            result_items = []
            for item in request.items:
                sku = sku_map[item.sku_id]
                sku.active_quantity -= item.quantity
                sku.reserved_quantity += item.quantity
                
                result_items.append({
                    "sku_id": str(sku.id),
                    "reserved_quantity": item.quantity,
                    "remaining_stock": sku.active_quantity
                })
                
                if sku.active_quantity == 0:
                    self._emit_out_of_stock_event(sku)
            
            self.db.commit()
            
            response_data = {
                "order_id": str(request.order_id),
                "status": "RESERVED",
                "reserved_at": datetime.utcnow().isoformat()
            }
            
            op = ReserveOperation(
                idempotency_key=str(request.idempotency_key),
                result=response_data
            )
            self.db.add(op)
            self.db.commit()
            
            return response_data
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def unreserve(self, request: UnreserveRequest) -> dict:
        """Снятие резерва с идемпотентностью по order_id"""
        
        existing = self.db.query(UnreserveOperation).filter(
            UnreserveOperation.order_id == request.order_id
        ).first()
        
        if existing:
            return existing.result
        
        try:
            sku_ids = [item.sku_id for item in request.items]
            skus = self.db.query(SKU).filter(
                SKU.id.in_(sku_ids)
            ).with_for_update().all()
            
            sku_map = {sku.id: sku for sku in skus}
            
            for item in request.items:
                sku = sku_map.get(item.sku_id)
                if sku:
                    sku.active_quantity += item.quantity
                    sku.reserved_quantity -= item.quantity
            
            self.db.commit()
            
            response_data = {
                "order_id": str(request.order_id),
                "status": "UNRESERVED",
                "processed_at": datetime.utcnow().isoformat()
            }
            
            op = UnreserveOperation(
                order_id=request.order_id,
                result=response_data
            )
            self.db.add(op)
            self.db.commit()
            
            return response_data
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _emit_out_of_stock_event(self, sku: SKU):
        """Отправка события SKU_OUT_OF_STOCK в B2C"""
        print(f"EVENT: SKU_OUT_OF_STOCK - sku_id={sku.id}, product_id={sku.product_id}")