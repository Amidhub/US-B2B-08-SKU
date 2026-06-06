from fastapi import Header, HTTPException


async def verify_service_key(X_Service_Key: str = Header(None)):
    B2C_SERVICE_KEY = "your-b2c-service-key"
    if X_Service_Key != B2C_SERVICE_KEY:
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "ServiceKey"},
            detail={
                "code": "INVALID_SERVICE_KEY",
                "message": "Invalid X-Service-Key header"
            }
        )
    return True