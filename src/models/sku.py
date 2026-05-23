from sqlalchemy import JSON, Boolean, Column, String, Integer, Numeric, UUID, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
import uuid
from src.database import Base

class SKU(Base):
    __tablename__ = "skus"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    article = Column(String(100), unique=True, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    
    # Инвентарные поля
    on_hand = Column(Integer, default=0, nullable=False)
    active_quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
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