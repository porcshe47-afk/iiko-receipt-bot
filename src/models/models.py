from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProductMapping(Base):
    __tablename__ = "product_mappings"
    
    id = Column(Integer, primary_key=True)
    external_name = Column(String, nullable=False)  # Имя из накладной/чека
    iiko_product_id = Column(String, nullable=False) # UUID товара в iiko
    iiko_product_name = Column(String)
    supplier_inn = Column(String) # Чтобы маппинг был привязан к поставщику
    
    created_at = Column(DateTime, default=datetime.utcnow)

class InvoiceSession(Base):
    __tablename__ = "invoice_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_url = Column(String)
    raw_recognition_result = Column(JSON) # Что вернул AI
    status = Column(String, default="pending") # pending, confirmed, uploaded, error
    
    created_at = Column(DateTime, default=datetime.utcnow)
