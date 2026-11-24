"""RFQ repository interface."""

from abc import abstractmethod
from .base import BaseRepository
from typing import Optional, List


class RFQRepository(BaseRepository):
    """Repository for RFQ (Request for Quote) operations."""

    @abstractmethod
    async def create_rfq(
        self,
        customer_name: str,
        customer_email: str,
        items: List[dict],
        special_requirements: Optional[str] = None,
    ) -> dict:
        """Create a new RFQ."""
        pass

    @abstractmethod
    async def get_rfq_status(self, rfq_id: str) -> dict:
        """Get RFQ status."""
        pass

    @abstractmethod
    async def accept_rfq(
        self, rfq_id: str, purchase_order_number: Optional[str] = None
    ) -> dict:
        """Accept an RFQ and create order."""
        pass

    @abstractmethod
    async def rfq_exists(self, rfq_id: str) -> bool:
        """Check if an RFQ exists."""
        pass

    @abstractmethod
    async def get_customer_rfqs(self, customer_email: str) -> List[dict]:
        """Get all RFQs for a customer."""
        pass
