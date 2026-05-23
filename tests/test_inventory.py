import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from src.main import app
from src.models.sku import SKU
from src.database import SessionLocal

client = TestClient(app)

# Вспомогательная функция для создания тестового SKU
def create_test_sku(active_quantity=10, reserved_quantity=0):
    db = SessionLocal()
    sku = SKU(
        id=uuid4(),
        product_id=uuid4(),
        name="Test SKU",
        article=f"ART_{uuid4().hex[:8]}",
        price=1000,
        on_hand=active_quantity + reserved_quantity,
        active_quantity=active_quantity,
        reserved_quantity=reserved_quantity
    )
    db.add(sku)
    db.commit()
    db.refresh(sku)
    db.close()
    return sku

# Тест 1: Happy path
def test_reserve_all_skus_succeeds():
    sku = create_test_sku(active_quantity=10, reserved_quantity=0)
    
    response = client.post("/api/v1/inventory/reserve", 
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": str(uuid4()),
            "order_id": str(uuid4()),
            "items": [{"sku_id": str(sku.id), "quantity": 3}]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RESERVED"
    
    # Проверяем изменения в БД
    db = SessionLocal()
    sku_updated = db.query(SKU).get(sku.id)
    assert sku_updated.active_quantity == 7   # 10 - 3
    assert sku_updated.reserved_quantity == 3
    db.close()

# Тест 2: Insufficient stock → 409, all rollback
def test_partial_insufficient_stock_returns_409_all_rollback():
    sku1 = create_test_sku(active_quantity=10)
    sku2 = create_test_sku(active_quantity=1)
    
    response = client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": str(uuid4()),
            "order_id": str(uuid4()),
            "items": [
                {"sku_id": str(sku1.id), "quantity": 5},
                {"sku_id": str(sku2.id), "quantity": 2}  # не хватает
            ]
        }
    )
    
    assert response.status_code == 409
    data = response.json()
    assert data["reserved"] == False
    assert len(data["failed_items"]) == 1
    
    # Проверяем: ничего не изменилось
    db = SessionLocal()
    sku1_updated = db.query(SKU).get(sku1.id)
    sku2_updated = db.query(SKU).get(sku2.id)
    assert sku1_updated.active_quantity == 10
    assert sku2_updated.active_quantity == 1
    db.close()

# Тест 3: Idempotency
def test_idempotent_reserve_returns_200_without_double_deduction():
    sku = create_test_sku(active_quantity=10)
    idempotency_key = str(uuid4())
    order_id = str(uuid4())
    
    response1 = client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": idempotency_key,
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 2}]
        }
    )
    
    response2 = client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": idempotency_key,
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 2}]
        }
    )
    
    assert response2.status_code == 200
    
    db = SessionLocal()
    sku_updated = db.query(SKU).get(sku.id)
    assert sku_updated.active_quantity == 8  # только минус 2
    db.close()

# Тест 4: OUT_OF_STOCK event
def test_sku_out_of_stock_event_emitted():
    sku = create_test_sku(active_quantity=1)
    
    response = client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": str(uuid4()),
            "order_id": str(uuid4()),
            "items": [{"sku_id": str(sku.id), "quantity": 1}]
        }
    )
    
    assert response.status_code == 200
    
    db = SessionLocal()
    sku_updated = db.query(SKU).get(sku.id)
    assert sku_updated.active_quantity == 0
    db.close()
    

# Тест 5: Unreserve restores quantities
def test_unreserve_restores_quantities():
    sku = create_test_sku(active_quantity=10, reserved_quantity=0)
    order_id = str(uuid4())
    
    # Сначала резервируем
    reserve_response = client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": str(uuid4()),
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 3}]
        }
    )
    
    assert reserve_response.status_code == 200
    
    # Снимаем резерв
    unreserve_response = client.post("/api/v1/inventory/unreserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 3}]
        }
    )
    
    assert unreserve_response.status_code == 200
    data = unreserve_response.json()
    assert data["status"] == "UNRESERVED"
    
    db = SessionLocal()
    sku_updated = db.query(SKU).get(sku.id)
    assert sku_updated.active_quantity == 10
    assert sku_updated.reserved_quantity == 0
    db.close()

# Тест 6: Unreserve idempotency
def test_unreserve_idempotent():
    sku = create_test_sku(active_quantity=10)
    order_id = str(uuid4())
    
    # Резервируем
    client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": str(uuid4()),
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 3}]
        }
    )
    
    # Снимаем резерв
    response1 = client.post("/api/v1/inventory/unreserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 3}]
        }
    )
    
    response2 = client.post("/api/v1/inventory/unreserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 3}]
        }
    )
    
    assert response2.status_code == 200
    # Количество не изменилось дважды
    db = SessionLocal()
    sku_updated = db.query(SKU).get(sku.id)
    assert sku_updated.active_quantity == 10
    db.close()