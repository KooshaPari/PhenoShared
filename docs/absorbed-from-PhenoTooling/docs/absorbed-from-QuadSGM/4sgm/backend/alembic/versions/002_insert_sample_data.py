"""Insert initial sample products data

Revision ID: 002
Revises: 001
Create Date: 2025-11-16 23:31:15.000000

"""

# noqa: E501 - Long SQL strings in migrations
from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert initial sample products (8 items)
    op.execute(
        """
        INSERT INTO products (id, sku, name, description, price, quantity_on_hand, category, product_metadata) VALUES
        ('prod-001', 'SKU-LAPTOP-001', 'Laptop Pro 15"', 'High-performance laptop with 16GB RAM', 1299.99, 5, 'electronics', '{"brand": "TechCorp", "color": "Silver", "weight": "1.8 kg", "warranty": "2 years"}'),
        ('prod-002', 'SKU-MOUSE-001', 'Wireless Mouse', 'Ergonomic wireless mouse with precision tracking', 29.99, 50, 'accessories', '{"brand": "PeripheralCo", "color": "Black", "weight": "0.1 kg", "warranty": "1 year"}'),
        ('prod-003', 'SKU-HUB-001', 'USB-C Hub', 'Multi-port USB-C hub with 7 ports', 49.99, 30, 'accessories', '{"brand": "ConnectTech", "color": "Gray", "weight": "0.2 kg", "warranty": "2 years"}'),
        ('prod-004', 'SKU-MONITOR-001', 'Monitor 4K', '4K UHD monitor 27 inch', 399.99, 10, 'electronics', '{"brand": "DisplayPro", "color": "Black", "weight": "5.5 kg", "warranty": "3 years"}'),
        ('prod-005', 'SKU-KEYBOARD-001', 'Keyboard Mechanical', 'Mechanical gaming keyboard RGB', 149.99, 20, 'accessories', '{"brand": "GamerGear", "color": "Black", "weight": "0.9 kg", "warranty": "2 years"}'),
        ('prod-006', 'SKU-WEBCAM-001', 'Webcam HD', '1080p HD webcam with auto-focus', 79.99, 15, 'electronics', '{"brand": "CameraWorks", "color": "Black", "weight": "0.15 kg", "warranty": "1 year"}'),
        ('prod-007', 'SKU-HEADPHONES-001', 'Headphones Pro', 'Noise-cancelling headphones', 199.99, 25, 'audio', '{"brand": "AudioMax", "color": "Black", "weight": "0.25 kg", "warranty": "2 years"}'),
        ('prod-008', 'SKU-LAMP-001', 'Desk Lamp LED', 'LED desk lamp with adjustable brightness', 59.99, 40, 'lighting', '{"brand": "LightWorks", "color": "White", "weight": "0.5 kg", "warranty": "1 year"}')
        ON CONFLICT (id) DO NOTHING
    """
    )


def downgrade() -> None:
    # Delete sample products
    op.execute("DELETE FROM products WHERE id LIKE 'prod-%'")
