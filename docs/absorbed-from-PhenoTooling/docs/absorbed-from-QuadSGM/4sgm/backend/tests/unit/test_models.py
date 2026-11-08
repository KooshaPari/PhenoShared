"""Tests for Pydantic and SQLAlchemy models."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from models import ChatSession, Document, Product


class TestProductModel:
    """Tests for Product model."""

    def test_product_creation(self, db_session: Session):
        """Test creating a product."""
        product = Product(
            id="prod-1",
            sku="SKU-001",
            name="Test Product",
            description="Test description",
            price=99.99,
            quantity_on_hand=50,
            category="electronics",
            product_metadata={"brand": "TestBrand"},
        )
        db_session.add(product)
        db_session.commit()

        retrieved = db_session.query(Product).filter(Product.id == "prod-1").first()
        assert retrieved is not None
        assert retrieved.name == "Test Product"
        assert retrieved.price == 99.99
        assert retrieved.quantity_on_hand == 50

    def test_product_defaults(self, db_session: Session):
        """Test product default values."""
        product = Product(id="prod-2", sku="SKU-002", name="Product Default Test", price=50.0)
        db_session.add(product)
        db_session.commit()

        retrieved = db_session.query(Product).filter(Product.id == "prod-2").first()
        assert retrieved.quantity_on_hand == 0
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None

    def test_product_repr(self, db_session: Session):
        """Test product string representation."""
        product = Product(id="prod-3", sku="SKU-003", name="Repr Test", price=100.0)
        repr_str = repr(product)
        assert "Product" in repr_str
        assert "Repr Test" in repr_str
        assert "100" in repr_str

    def test_product_metadata_json(self, db_session: Session):
        """Test product metadata as JSON."""
        metadata = {"brand": "TestBrand", "color": "red", "weight": "2.5 kg", "warranty": "2 years"}
        product = Product(
            id="prod-4", sku="SKU-004", name="Metadata Test", price=75.0, product_metadata=metadata
        )
        db_session.add(product)
        db_session.commit()

        retrieved = db_session.query(Product).filter(Product.id == "prod-4").first()
        assert retrieved.product_metadata == metadata
        assert retrieved.product_metadata["brand"] == "TestBrand"

    def test_product_unique_sku(self, db_session: Session):
        """Test SKU uniqueness constraint."""
        product1 = Product(id="prod-5", sku="SKU-UNIQUE-001", name="Product 1", price=100.0)
        db_session.add(product1)
        db_session.commit()

        product2 = Product(
            id="prod-6",
            sku="SKU-UNIQUE-001",  # Same SKU
            name="Product 2",
            price=100.0,
        )
        db_session.add(product2)

        with pytest.raises(Exception):  # SQLAlchemy integrity error
            db_session.commit()

    def test_product_price_precision(self, db_session: Session):
        """Test product price decimal precision."""
        product = Product(id="prod-7", sku="SKU-007", name="Price Test", price=999.99)
        db_session.add(product)
        db_session.commit()

        retrieved = db_session.query(Product).filter(Product.id == "prod-7").first()
        assert retrieved.price == 999.99


class TestChatSessionModel:
    """Tests for ChatSession model."""

    def test_chat_session_creation(self, db_session: Session):
        """Test creating a chat session."""
        session = ChatSession(
            id="session-1",
            user_id="user-123",
            data={
                "messages": [{"role": "user", "content": "Hello"}],
                "metadata": {"ip": "192.168.1.1"},
            },
        )
        db_session.add(session)
        db_session.commit()

        retrieved = db_session.query(ChatSession).filter(ChatSession.id == "session-1").first()
        assert retrieved is not None
        assert retrieved.user_id == "user-123"
        assert len(retrieved.data["messages"]) == 1

    def test_chat_session_data_json(self, db_session: Session):
        """Test chat session data as JSON."""
        data = {
            "messages": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ],
            "metadata": {"user_agent": "Mozilla", "ip_address": "127.0.0.1"},
        }
        session = ChatSession(id="session-2", user_id="user-456", data=data)
        db_session.add(session)
        db_session.commit()

        retrieved = db_session.query(ChatSession).filter(ChatSession.id == "session-2").first()
        assert retrieved.data == data
        assert len(retrieved.data["messages"]) == 2
        assert retrieved.data["metadata"]["ip_address"] == "127.0.0.1"

    def test_chat_session_repr(self, db_session: Session):
        """Test chat session string representation."""
        session = ChatSession(id="session-3", user_id="user-789", data={"messages": []})
        repr_str = repr(session)
        assert "ChatSession" in repr_str
        assert "session-3" in repr_str

    def test_chat_session_multiple_messages(self, db_session: Session):
        """Test chat session with multiple messages."""
        messages = [
            {
                "role": "user",
                "content": f"Message {i}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(10)
        ]
        session = ChatSession(id="session-4", user_id="user-999", data={"messages": messages})
        db_session.add(session)
        db_session.commit()

        retrieved = db_session.query(ChatSession).filter(ChatSession.id == "session-4").first()
        assert len(retrieved.data["messages"]) == 10

    def test_chat_session_defaults(self, db_session: Session):
        """Test chat session default values."""
        session = ChatSession(id="session-5", user_id="user-111", data={"messages": []})
        db_session.add(session)
        db_session.commit()

        retrieved = db_session.query(ChatSession).filter(ChatSession.id == "session-5").first()
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None


class TestDocumentModel:
    """Tests for Document model."""

    def test_document_creation(self, db_session: Session):
        """Test creating a document."""
        doc = Document(
            id="doc-1",
            title="Test Document",
            content="This is test content",
            embedding=[0.1] * 768,
            doc_metadata={"author": "Test"},
        )
        db_session.add(doc)
        db_session.commit()

        retrieved = db_session.query(Document).filter(Document.id == "doc-1").first()
        assert retrieved is not None
        assert retrieved.title == "Test Document"
        assert retrieved.content == "This is test content"

    def test_document_embedding(self, db_session: Session):
        """Test document embedding as JSON."""
        embedding = [0.1 * i for i in range(100)]
        doc = Document(id="doc-2", title="Embedding Test", content="Content", embedding=embedding)
        db_session.add(doc)
        db_session.commit()

        retrieved = db_session.query(Document).filter(Document.id == "doc-2").first()
        assert retrieved.embedding == embedding
        assert len(retrieved.embedding) == 100

    def test_document_metadata(self, db_session: Session):
        """Test document metadata as JSON."""
        metadata = {
            "author": "Jane Doe",
            "source": "https://example.com/doc",
            "tags": ["important", "test", "documentation"],
            "language": "en",
        }
        doc = Document(id="doc-3", title="Metadata Test", content="Content", doc_metadata=metadata)
        db_session.add(doc)
        db_session.commit()

        retrieved = db_session.query(Document).filter(Document.id == "doc-3").first()
        assert retrieved.doc_metadata == metadata
        assert "important" in retrieved.doc_metadata["tags"]

    def test_document_repr(self, db_session: Session):
        """Test document string representation."""
        doc = Document(id="doc-4", title="Repr Test Doc", content="Content")
        repr_str = repr(doc)
        assert "Document" in repr_str
        assert "Repr Test Doc" in repr_str

    def test_document_content_large(self, db_session: Session):
        """Test document with large content."""
        large_content = "Word " * 10000  # Large content
        doc = Document(id="doc-5", title="Large Content Test", content=large_content)
        db_session.add(doc)
        db_session.commit()

        retrieved = db_session.query(Document).filter(Document.id == "doc-5").first()
        assert len(retrieved.content) > 40000

    def test_document_defaults(self, db_session: Session):
        """Test document default values."""
        doc = Document(id="doc-6", title="Default Test", content="Content")
        db_session.add(doc)
        db_session.commit()

        retrieved = db_session.query(Document).filter(Document.id == "doc-6").first()
        assert retrieved.created_at is not None
        assert retrieved.embedding is None
        assert retrieved.doc_metadata is None

    def test_document_title_index(self, db_session: Session):
        """Test that title index works."""
        doc = Document(id="doc-7", title="Indexed Title", content="Content")
        db_session.add(doc)
        db_session.commit()

        # Query by title should work due to index
        retrieved = db_session.query(Document).filter(Document.title == "Indexed Title").first()
        assert retrieved is not None
        assert retrieved.id == "doc-7"
