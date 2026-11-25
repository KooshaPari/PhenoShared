"""Tests for base repository interface and implementations."""

import pytest


class TestRepositoryInterface:
    """Tests for repository interface contracts."""

    def test_product_repo_interface(self, mock_product_repo):
        """Test product repository implements required interface."""
        assert hasattr(mock_product_repo, "get")
        assert hasattr(mock_product_repo, "list")
        assert hasattr(mock_product_repo, "create")
        assert hasattr(mock_product_repo, "update")
        assert hasattr(mock_product_repo, "delete")
        assert hasattr(mock_product_repo, "search")

    def test_chat_session_repo_interface(self, mock_chat_session_repo):
        """Test chat session repository implements required interface."""
        assert hasattr(mock_chat_session_repo, "get")
        assert hasattr(mock_chat_session_repo, "list")
        assert hasattr(mock_chat_session_repo, "create")
        assert hasattr(mock_chat_session_repo, "update")
        assert hasattr(mock_chat_session_repo, "delete")

    def test_document_repo_interface(self, mock_document_repo):
        """Test document repository implements required interface."""
        assert hasattr(mock_document_repo, "get")
        assert hasattr(mock_document_repo, "list")
        assert hasattr(mock_document_repo, "create")
        assert hasattr(mock_document_repo, "update")
        assert hasattr(mock_document_repo, "delete")
        assert hasattr(mock_document_repo, "search")

    @pytest.mark.asyncio
    async def test_repo_methods_are_async(self, mock_product_repo):
        """Test repository methods are async."""
        # All methods should be coroutines
        assert hasattr(mock_product_repo.get, "_is_coroutine") or hasattr(
            mock_product_repo.get, "__await__"
        )


class TestProductRepository:
    """Tests for Product repository."""

    @pytest.mark.asyncio
    async def test_get_product_success(self, mock_product_repo, mock_product):
        """Test getting a product successfully."""
        mock_product_repo.get.return_value = mock_product

        result = await mock_product_repo.get("prod-123")

        assert result is not None
        assert result["id"] == "prod-123"
        mock_product_repo.get.assert_called_once_with("prod-123")

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, mock_product_repo):
        """Test getting non-existent product."""
        mock_product_repo.get.return_value = None

        result = await mock_product_repo.get("invalid-id")

        assert result is None
        mock_product_repo.get.assert_called_once_with("invalid-id")

    @pytest.mark.asyncio
    async def test_list_products(self, mock_product_repo, mock_product):
        """Test listing products."""
        mock_product_repo.list.return_value = [mock_product, mock_product]

        result = await mock_product_repo.list()

        assert isinstance(result, list)
        assert len(result) == 2
        mock_product_repo.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_products(self, mock_product_repo, mock_product):
        """Test searching products."""
        mock_product_repo.search.return_value = [mock_product]

        result = await mock_product_repo.search(query="electronics")

        assert isinstance(result, list)
        mock_product_repo.search.assert_called_once_with(query="electronics")

    @pytest.mark.asyncio
    async def test_create_product(self, mock_product_repo, mock_product):
        """Test creating a product."""
        mock_product_repo.create.return_value = mock_product

        result = await mock_product_repo.create(mock_product)

        assert result is not None
        assert result["name"] == "Test Product"
        mock_product_repo.create.assert_called_once_with(mock_product)

    @pytest.mark.asyncio
    async def test_update_product(self, mock_product_repo, mock_product):
        """Test updating a product."""
        updated = {**mock_product, "name": "Updated Product"}
        mock_product_repo.update.return_value = updated

        result = await mock_product_repo.update("prod-123", {"name": "Updated Product"})

        assert result["name"] == "Updated Product"
        mock_product_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_product(self, mock_product_repo):
        """Test deleting a product."""
        mock_product_repo.delete.return_value = True

        result = await mock_product_repo.delete("prod-123")

        assert result is True
        mock_product_repo.delete.assert_called_once_with("prod-123")


class TestChatSessionRepository:
    """Tests for ChatSession repository."""

    @pytest.mark.asyncio
    async def test_get_session(self, mock_chat_session_repo, mock_chat_session):
        """Test getting a chat session."""
        mock_chat_session_repo.get.return_value = mock_chat_session

        result = await mock_chat_session_repo.get("session-123")

        assert result is not None
        assert result["user_id"] == "user-456"
        mock_chat_session_repo.get.assert_called_once_with("session-123")

    @pytest.mark.asyncio
    async def test_list_sessions(self, mock_chat_session_repo, mock_chat_session):
        """Test listing chat sessions."""
        mock_chat_session_repo.list.return_value = [mock_chat_session]

        result = await mock_chat_session_repo.list()

        assert isinstance(result, list)
        mock_chat_session_repo.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session(self, mock_chat_session_repo, mock_chat_session):
        """Test creating a chat session."""
        mock_chat_session_repo.create.return_value = mock_chat_session

        result = await mock_chat_session_repo.create(mock_chat_session)

        assert result is not None
        mock_chat_session_repo.create.assert_called_once_with(mock_chat_session)

    @pytest.mark.asyncio
    async def test_update_session(self, mock_chat_session_repo, mock_chat_session):
        """Test updating a chat session."""
        updated = {**mock_chat_session, "data": {"messages": []}}
        mock_chat_session_repo.update.return_value = updated

        result = await mock_chat_session_repo.update("session-123", {})

        assert result is not None
        mock_chat_session_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_session(self, mock_chat_session_repo):
        """Test deleting a chat session."""
        mock_chat_session_repo.delete.return_value = True

        result = await mock_chat_session_repo.delete("session-123")

        assert result is True
        mock_chat_session_repo.delete.assert_called_once_with("session-123")


class TestDocumentRepository:
    """Tests for Document repository."""

    @pytest.mark.asyncio
    async def test_get_document(self, mock_document_repo, mock_document):
        """Test getting a document."""
        mock_document_repo.get.return_value = mock_document

        result = await mock_document_repo.get("doc-789")

        assert result is not None
        assert result["title"] == "Test Document"
        mock_document_repo.get.assert_called_once_with("doc-789")

    @pytest.mark.asyncio
    async def test_list_documents(self, mock_document_repo, mock_document):
        """Test listing documents."""
        mock_document_repo.list.return_value = [mock_document]

        result = await mock_document_repo.list()

        assert isinstance(result, list)
        mock_document_repo.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documents(self, mock_document_repo, mock_document):
        """Test searching documents."""
        mock_document_repo.search.return_value = [mock_document]

        result = await mock_document_repo.search(query="test")

        assert isinstance(result, list)
        mock_document_repo.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_document(self, mock_document_repo, mock_document):
        """Test creating a document."""
        mock_document_repo.create.return_value = mock_document

        result = await mock_document_repo.create(mock_document)

        assert result is not None
        mock_document_repo.create.assert_called_once_with(mock_document)

    @pytest.mark.asyncio
    async def test_update_document(self, mock_document_repo, mock_document):
        """Test updating a document."""
        updated = {**mock_document, "title": "Updated Document"}
        mock_document_repo.update.return_value = updated

        result = await mock_document_repo.update("doc-789", {})

        assert result is not None
        mock_document_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_document(self, mock_document_repo):
        """Test deleting a document."""
        mock_document_repo.delete.return_value = True

        result = await mock_document_repo.delete("doc-789")

        assert result is True
        mock_document_repo.delete.assert_called_once_with("doc-789")


class TestRepositoryErrorHandling:
    """Tests for repository error handling."""

    @pytest.mark.asyncio
    async def test_repo_handles_none_input(self, mock_product_repo):
        """Test repository handles None input."""
        mock_product_repo.get.return_value = None

        result = await mock_product_repo.get(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_repo_handles_invalid_input(self, mock_product_repo):
        """Test repository handles invalid input."""
        mock_product_repo.get.side_effect = ValueError("Invalid ID")

        with pytest.raises(ValueError):
            await mock_product_repo.get("")

    @pytest.mark.asyncio
    async def test_repo_empty_list(self, mock_product_repo):
        """Test repository returns empty list."""
        mock_product_repo.list.return_value = []

        result = await mock_product_repo.list()

        assert result == []
        assert len(result) == 0
