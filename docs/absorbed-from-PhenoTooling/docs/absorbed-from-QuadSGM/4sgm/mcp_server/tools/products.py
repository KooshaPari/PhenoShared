"""Product search and retrieval tools for 4SGM MCP server."""

import logging

from ..models import ProductResponse, SearchProductsResponse
from ..exceptions import ProductNotFoundError, ProductSearchError
from ..repositories import ProductRepository

logger = logging.getLogger(__name__)


def register_product_tools(mcp, product_repo: ProductRepository):
    """Register product tools with the FastMCP instance."""

    @mcp.tool
    async def get_product(product_id: str) -> dict:
        """Get detailed product information.

        Retrieves comprehensive product details including pricing, inventory,
        ratings, and descriptions from the product catalog.

        Args:
            product_id: The unique product identifier (SKU or product ID)

        Returns:
            ProductResponse with full product details including name, price,
            description, category, ratings, and stock information.

        Raises:
            ProductNotFoundError: If product doesn't exist in catalog
            ProductSearchError: If database query fails
        """
        try:
            if not product_repo:
                raise ProductSearchError("Product repository not initialized")

            product = await product_repo.get(product_id)
            if not product:
                raise ProductNotFoundError(f"Product {product_id} not found")

            response = ProductResponse(
                id=product.id,
                name=product.name,
                sku=product.sku,
                description=product.description,
                price=product.price,
                category=product.category,
                rating=product.rating,
                reviews=product.reviews,
                quantity_on_hand=product.quantity_on_hand,
                created_at=product.created_at,
                updated_at=product.updated_at,
            )
            return response.model_dump(exclude_none=True)

        except ProductNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            raise ProductSearchError(f"Failed to fetch product: {str(e)}")

    @mcp.tool
    async def search_products(query: str, limit: int = 10) -> dict:
        """Search product catalog by keyword.

        Performs full-text search across product names, descriptions, and categories
        with configurable result limit.

        Args:
            query: Search query string (minimum 1 character)
            limit: Maximum number of results (1-100, default 10)

        Returns:
            SearchProductsResponse with list of matching products and total count.

        Raises:
            ProductSearchError: If search operation fails
        """
        try:
            if not product_repo:
                raise ProductSearchError("Product repository not initialized")

            if not query or len(query.strip()) == 0:
                raise ProductSearchError("Search query cannot be empty")

            limit = min(max(1, limit), 100)  # Clamp between 1-100

            products = await product_repo.search(query, limit)

            response = SearchProductsResponse(
                products=[
                    ProductResponse(
                        id=p.id,
                        name=p.name,
                        sku=p.sku,
                        price=p.price,
                        description=p.description,
                        category=p.category,
                        rating=p.rating,
                        reviews=p.reviews,
                        quantity_on_hand=p.quantity_on_hand,
                        created_at=None,
                        updated_at=None,
                    )
                    for p in products
                ],
                total_results=len(products),
                query=query,
            )
            return response.model_dump(exclude_none=True)

        except ProductSearchError:
            raise
        except Exception as e:
            logger.error(f"Error searching products with query '{query}': {str(e)}")
            raise ProductSearchError(f"Failed to search products: {str(e)}")
