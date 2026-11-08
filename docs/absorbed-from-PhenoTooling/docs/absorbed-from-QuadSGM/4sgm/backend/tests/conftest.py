"""
Pytest configuration and shared fixtures for 4SGM backend tests.

Provides:
- Database fixtures with transactional rollback
- Async client fixtures
- Authentication fixtures
- Mock service fixtures
- Factory fixtures for common test data
"""

# ============================================================================
# CRITICAL: Mock psycopg2 BEFORE any imports
# ============================================================================
import sys
from unittest.mock import MagicMock

# Mock psycopg2 and related modules before any imports
psycopg2_mock = MagicMock()
sys.modules["psycopg2"] = psycopg2_mock
sys.modules["psycopg2.extensions"] = MagicMock()
sys.modules["psycopg2.pool"] = MagicMock()
sys.modules["psycopg2.compat"] = MagicMock()

# Import models - try multiple import paths
from datetime import datetime, timezone  # noqa: E402 -- psycopg2 mock setup
from pathlib import Path  # noqa: E402 -- psycopg2 mock setup
from unittest.mock import AsyncMock, Mock  # noqa: E402 -- psycopg2 mock setup

import pytest  # noqa: E402 -- psycopg2 mock setup
import pytest_asyncio  # noqa: E402 -- psycopg2 mock setup
from sqlalchemy import create_engine  # noqa: E402 -- psycopg2 mock setup
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402 -- psycopg2 mock setup
from sqlalchemy.pool import StaticPool  # noqa: E402 -- psycopg2 mock setup

# Add backend directory to path if needed
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

try:
    from backend.models import Base
except ImportError:
    try:
        from models import Base
    except ImportError:
        # Create a stub Base if models not available
        from sqlalchemy.orm import declarative_base

        Base = declarative_base()

try:
    from backend.app import app
    from backend.database import get_db
except ImportError:
    try:
        from app import app

        try:
            from database import get_db
        except ImportError:
            # Create stub get_db if database module not available
            async def get_db():
                yield None

    except ImportError:
        # Skip app imports for conftest-only use
        app = None
        get_db = None


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_database_url():
    """Return test database URL."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine(test_database_url):
    """Create test database engine."""
    engine = create_engine(
        test_database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Drop and recreate tables for fresh state (checkfirst prevents duplicate errors)
    Base.metadata.drop_all(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine, checkfirst=True)
    yield engine
    Base.metadata.drop_all(bind=engine, checkfirst=True)
    engine.dispose()


@pytest.fixture
def db_session(engine):
    """Create test database session with transaction rollback."""
    # Start a connection and transaction
    connection = engine.raw_connection()
    connection.isolation_level = None  # Autocommit off
    connection.execute("BEGIN EXCLUSIVE")

    session = sessionmaker(autocommit=False, autoflush=False)(bind=engine)
    session.connection = connection

    yield session

    session.close()
    try:
        connection.execute("ROLLBACK")
    except Exception:
        pass
    finally:
        connection.close()


@pytest.fixture
def test_db(engine) -> Session:
    """
    Provides a database session for tests with automatic rollback.

    Uses the shared engine fixture to avoid duplicate table creation.

    Yields:
        Session: Test database session
    """
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_local()
    yield session
    session.close()


@pytest_asyncio.fixture
async def async_client(test_db: Session, monkeypatch):
    """
    Provides an HTTP client for testing API endpoints.

    Args:
        test_db: Test database session
        monkeypatch: pytest monkeypatch fixture

    Yields:
        Client: HTTP client for the app
    """
    if app is None:
        pytest.skip("FastAPI app not available")
        return

    # Mock the agent and init_agent before using the app
    mock_agent = AsyncMock()
    mock_message = Mock()
    mock_message.content = "Mock response from agent"

    async def mock_ainvoke(input_dict):
        return {"messages": [{"type": "human", "content": "test"}, mock_message]}

    mock_agent.ainvoke = mock_ainvoke

    async def mock_init_agent():
        # Don't actually initialize, just return True
        return True

    # Patch the app module's agent and init_agent
    try:
        from backend import app as app_module

        monkeypatch.setattr(app_module, "agent", mock_agent)
        monkeypatch.setattr(app_module, "init_agent", mock_init_agent)
    except ImportError:
        pass

    def override_get_db():
        yield test_db

    try:
        app.dependency_overrides[get_db] = override_get_db

        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def mock_user_auth() -> dict:
    """
    Provides mock user authentication data.

    Returns:
        dict: User authentication context with ID and email
    """
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture
def mock_jwt_token() -> str:
    """
    Provides a mock JWT token for authenticated requests.

    Returns:
        str: Mock JWT token
    """
    return "mock.jwt.token"  # noqa: E501 -- mock token for testing


@pytest.fixture
def auth_headers(mock_jwt_token: str) -> dict:
    """
    Provides authorization headers with JWT token.

    Args:
        mock_jwt_token: Mock JWT token

    Returns:
        dict: Headers with authorization
    """
    return {
        "Authorization": f"Bearer {mock_jwt_token}",
        "Content-Type": "application/json",
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_service() -> Mock:
    """
    Provides a mock LLM service for testing.

    Returns:
        Mock: Mock LLM service
    """
    mock = AsyncMock()
    mock.generate_response.return_value = {
        "text": "Test response from LLM",
        "confidence": 0.95,
        "sources": ["doc1.pdf", "doc2.pdf"],
    }
    return mock


@pytest.fixture
def mock_vector_db() -> Mock:
    """
    Provides a mock vector database service for testing.

    Returns:
        Mock: Mock vector DB service
    """
    mock = AsyncMock()
    mock.search.return_value = [
        {
            "id": "doc1",
            "text": "Document 1 content",
            "score": 0.92,
            "source": "doc1.pdf",
        },
        {
            "id": "doc2",
            "text": "Document 2 content",
            "score": 0.87,
            "source": "doc2.pdf",
        },
    ]
    return mock


@pytest.fixture
def mock_cache() -> Mock:
    """
    Provides a mock cache service for testing.

    Returns:
        Mock: Mock cache service
    """
    mock = Mock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


# ============================================================================
# Repository Fixtures
# ============================================================================


@pytest.fixture
def mock_product_repo():
    """Create mock product repository."""
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.list = AsyncMock()
    repo.search = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_chat_session_repo():
    """Create mock chat session repository."""
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.list = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_document_repo():
    """Create mock document repository."""
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.list = AsyncMock()
    repo.search = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def mock_product():
    """Create mock product data."""
    return {
        "id": "prod-123",
        "sku": "SKU-123",
        "name": "Test Product",
        "description": "A test product",
        "price": 99.99,
        "quantity_on_hand": 100,
        "category": "test-category",
        "product_metadata": {"brand": "TestBrand"},
    }


@pytest.fixture
def mock_product_list():
    """Create list of mock products."""
    return [
        {
            "id": f"prod-{i}",
            "sku": f"SKU-{i}",
            "name": f"Product {i}",
            "price": 10.00 * i,
            "quantity_on_hand": 50,
            "category": "test-category",
        }
        for i in range(1, 6)
    ]


@pytest.fixture
def mock_cart():
    """Create mock cart data."""
    return {
        "id": "cart-123",
        "user_id": "user-123",
        "items": [
            {"product_id": "prod-1", "quantity": 2, "price": 10.00},
            {"product_id": "prod-2", "quantity": 1, "price": 20.00},
        ],
        "total": 40.00,
    }


@pytest.fixture
def mock_order():
    """Create mock order data."""
    return {
        "id": "order-123",
        "user_id": "user-123",
        "cart_id": "cart-123",
        "status": "pending",
        "total": 40.00,
        "shipping_address": {
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345",
        },
    }


@pytest.fixture
def mock_inventory():
    """Create mock inventory data."""
    return {
        "product_id": "prod-123",
        "quantity_available": 100,
        "quantity_reserved": 10,
        "reorder_level": 20,
    }


@pytest.fixture
def mock_inventory_repo():
    """Create mock inventory repository."""
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.update = AsyncMock()
    repo.reserve = AsyncMock()
    repo.release = AsyncMock()
    repo.check_availability = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_cart_repo():
    """Create mock cart repository."""
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.create = AsyncMock()
    repo.add_item = AsyncMock()
    repo.remove_item = AsyncMock()
    repo.update_quantity = AsyncMock()
    repo.clear = AsyncMock()
    repo.get_total = AsyncMock(return_value=40.00)
    return repo


@pytest.fixture
def mock_order_repo():
    """Create mock order repository."""
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.create = AsyncMock()
    repo.update_status = AsyncMock()
    repo.cancel = AsyncMock()
    return repo


@pytest.fixture
def mock_pricing_repo():
    """Create mock pricing repository."""
    repo = AsyncMock()
    repo.get_price = AsyncMock(return_value=99.99)
    repo.get_bulk_price = AsyncMock(return_value=89.99)
    repo.apply_coupon = AsyncMock(return_value={"discount": 10.00, "final_price": 79.99})
    repo.get_discounts = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_chat_session():
    """Create mock chat session data."""
    return {
        "id": "session-123",
        "user_id": "user-456",
        "data": {"messages": [], "context": {}},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_document():
    """Create mock document data."""
    return {
        "id": "doc-123",
        "title": "Test Document",
        "content": "This is test document content.",
        "embedding": [0.1] * 1536,
        "doc_metadata": {"source": "test", "category": "faq"},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_rfq():
    """Create mock RFQ data."""
    return {
        "id": "rfq-123",
        "customer_id": "customer-456",
        "items": [
            {"product_id": "prod-1", "quantity": 100, "requested_price": 8.50},
            {"product_id": "prod-2", "quantity": 50, "requested_price": 18.00},
        ],
        "status": "pending",
        "total_requested": 1750.00,
        "notes": "Need bulk discount",
        "expires_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_rfq_repo():
    """Create mock RFQ repository."""
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.update_status = AsyncMock()
    repo.list_by_customer = AsyncMock(return_value=[])
    repo.list_by_status = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_shipping_repo():
    """Create mock shipping repository."""
    repo = AsyncMock()
    repo.get_rates = AsyncMock(
        return_value=[
            {"carrier": "UPS", "service": "Ground", "price": 9.99, "days": 5},
            {"carrier": "FedEx", "service": "Express", "price": 24.99, "days": 2},
        ]
    )
    repo.validate_address = AsyncMock(return_value=True)
    repo.create_shipment = AsyncMock()
    repo.track = AsyncMock()
    return repo


@pytest.fixture
def mock_customer():
    """Create mock customer data."""
    return {
        "id": "customer-123",
        "email": "customer@example.com",
        "name": "Test Customer",
        "tier": "wholesale",
        "discount_rate": 0.15,
    }


@pytest.fixture
def mock_customer_repo():
    """Create mock customer repository."""
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.get_by_email = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.get_tier = AsyncMock(return_value="wholesale")
    return repo


# ============================================================================
# Agent and MCP Fixtures
# ============================================================================


class MockMessage:
    """Mock message object with content attribute."""

    def __init__(self, text):
        self.content = text


@pytest.fixture
def mock_agent():
    """Create mock DeepAgent for testing."""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(
        return_value={
            "messages": [
                {"type": "human", "content": "Mock input"},
                {"type": "assistant", "content": "Mock response from agent"},
            ]
        }
    )

    # Override the mock to properly handle accessing .content
    async def invoke_impl(msg_dict):
        msg_obj = MockMessage("Mock response from agent")
        return {"messages": [{"type": "human"}, msg_obj]}

    mock.ainvoke.side_effect = invoke_impl
    return mock


# ============================================================================
# Marker Registration
# ============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: Mark test as a unit test")
    config.addinivalue_line("markers", "integration: Mark test as an integration test")
    config.addinivalue_line("markers", "e2e: Mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: Mark test as slow running")
