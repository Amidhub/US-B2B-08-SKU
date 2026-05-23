from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.database import Base

class UnreserveOperation(Base):
    __tablename__ = "unreserve_operations"
    
    order_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())