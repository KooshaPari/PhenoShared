"""SQLAlchemy ORM models for 4SGM."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Index, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Product(Base):
    """Product model."""

    __tablename__ = "products"

    id = Column(String, primary_key=True)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    quantity_on_hand = Column(Integer, default=0)
    category = Column(String)
    product_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_products_sku", "sku"),
        Index("ix_products_category", "category"),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, price={self.price})>"


class ChatSession(Base):
    """Chat session model."""

    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_chat_sessions_user_id", "user_id"),)

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id})>"


class Document(Base):
    """Document model for RAG."""

    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(JSON)
    doc_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_documents_title", "title"),)

    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title})>"
