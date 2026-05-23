from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

import uuid
from src.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    
    status = Column(String(50), nullable=False, default="CREATED")
    deleted = Column(Boolean, default=False)
    blocked = Column(Boolean, default=False)
    blocking_reason_id = Column(UUID(as_uuid=True), nullable=True)
    moderator_comment = Column(Text, nullable=True)
    
    images = Column(JSON, nullable=False, default=list)
    characteristics = Column(JSON, default=list)
    skus = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())