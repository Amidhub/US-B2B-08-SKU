from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from src.models.sku import SKU
from src.models.reserve_operation import ReserveOperation
from src.models.unreserve_operation import UnreserveOperation
from src.schemas.inventory import ReserveRequest, UnreserveRequest


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def reserve(self, request: ReserveRequest) -> dict:
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

            missing_ids = set(sku_ids) - set(sku_map.keys())
            if missing_ids:
                self.db.rollback()
                return {
                    "code": "SKU_NOT_FOUND",
                    "message": f"SKU not found: {missing_ids}"
                }

            failed_items = []
            for item in request.items:
                sku = sku_map[item.sku_id]
                if sku.active_quantity < item.quantity:
                    failed_items.append({
                        "sku_id": str(item.sku_id),
                        "requested": item.quantity,
                        "available": sku.active_quantity,
                        "reason": "INSUFFICIENT_STOCK"
                    })

            if failed_items:
                self.db.rollback()
                return {
                    "code": "PARTIAL_INSUFFICIENT_STOCK",
                    "message": "Some SKUs have insufficient stock",
                    "details": {"failed_items": failed_items}
                }

            for item in request.items:
                sku = sku_map[item.sku_id]
                sku.active_quantity -= item.quantity
                sku.reserved_quantity += item.quantity

                if sku.active_quantity == 0:
                    self._emit_out_of_stock_event(sku)

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
                if not sku:
                    self.db.rollback()
                    return {
                        "code": "SKU_NOT_FOUND",
                        "message": f"SKU {item.sku_id} not found"
                    }
                if sku.reserved_quantity < item.quantity:
                    self.db.rollback()
                    return {
                        "code": "INSUFFICIENT_RESERVATION",
                        "message": f"Cannot unreserve {item.quantity}, only {sku.reserved_quantity} reserved"
                    }

            for item in request.items:
                sku = sku_map[item.sku_id]
                sku.active_quantity += item.quantity
                sku.reserved_quantity -= item.quantity

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

    def _emit_out_of_stock_event(self, sku):
        from src.models.outbox_event import OutboxEvent
        
        event = OutboxEvent(
            event_type="SKU_OUT_OF_STOCK",
            aggregate_id=str(sku.id),
            payload={
                "sku_id": str(sku.id),
                "product_id": str(sku.product_id),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.db.add(event)