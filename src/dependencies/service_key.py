from fastapi import Header, HTTPException

B2C_SERVICE_KEY = "your-b2c-service-key"  # нужно хранить в .env

async def verify_service_key(X_Service_Key: str = Header(...)):
    if X_Service_Key != B2C_SERVICE_KEY:
        raise HTTPException(status_code=401, detail="Invalid X-Service-Key")
    return True