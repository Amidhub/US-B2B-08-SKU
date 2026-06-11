def test_error_response_format_on_409():
    sku = create_test_sku(active_quantity=1)

    response = client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": str(uuid4()),
            "order_id": str(uuid4()),
            "items": [{"sku_id": str(sku.id), "quantity": 5}]
        }
    )

    assert response.status_code == 409
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert data["code"] == "PARTIAL_INSUFFICIENT_STOCK"


def test_cannot_unreserve_more_than_reserved():
    sku = create_test_sku(active_quantity=10)
    order_id = str(uuid4())

    client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": str(uuid4()),
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 3}]
        }
    )

    response = client.post("/api/v1/inventory/unreserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "order_id": order_id,
            "items": [{"sku_id": str(sku.id), "quantity": 5}]
        }
    )

    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "INSUFFICIENT_RESERVATION"


def test_zero_quantity_rejected():
    sku = create_test_sku(active_quantity=10)

    response = client.post("/api/v1/inventory/reserve",
        headers={"X-Service-Key": "your-b2c-service-key"},
        json={
            "idempotency_key": str(uuid4()),
            "order_id": str(uuid4()),
            "items": [{"sku_id": str(sku.id), "quantity": 0}]
        }
    )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"