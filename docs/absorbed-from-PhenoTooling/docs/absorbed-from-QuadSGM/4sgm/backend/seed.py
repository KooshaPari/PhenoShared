"""Seed database with Faker-generated data."""

import os
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, ChatSession, Document, Product

# Initialize Faker
fake = Faker()

# Database setup
DATABASE_URL = os.getenv(
    "SUPABASE_DB_URL",
    "postgresql://postgres:ASD3on54_Pax90@db.xerrnwvpdkywwugdtlma.supabase.co:5432/postgres",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed_products(session, count: int = 1000):
    """Seed products table with Faker data."""
    categories = ["electronics", "accessories", "audio", "lighting", "furniture", "software"]
    batch_size = 100

    products = []
    for i in range(count):
        product = Product(
            id=str(uuid.uuid4()),
            sku=fake.bothify(text="SKU-????-####", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            name=fake.word().title() + " " + fake.word().title(),
            description=fake.sentence(nb_words=10),
            price=round(
                fake.pyfloat(
                    left_digits=4,
                    right_digits=2,
                    positive=True,
                    min_value=10,
                    max_value=5000,
                ),
                2,
            ),
            quantity_on_hand=fake.random_int(min=0, max=1000),
            category=fake.random_element(categories),
            product_metadata={
                "brand": fake.company(),
                "color": fake.color_name(),
                "weight": f"{fake.pyfloat(left_digits=2, right_digits=2, positive=True, min_value=0.1, max_value=50)} kg",  # noqa: E501
                "warranty": f"{fake.random_int(min=1, max=5)} years",
            },
            created_at=datetime.now(timezone.utc) - timedelta(days=fake.random_int(min=0, max=365)),
            updated_at=datetime.now(timezone.utc),
        )
        products.append(product)

        # Batch insert every 100 records
        if len(products) >= batch_size:
            session.add_all(products)
            session.commit()
            print(f"  ✓ Inserted {len(products)} products ({i + 1}/{count})")
            products = []

    # Insert remaining products
    if products:
        session.add_all(products)
        session.commit()
        print(f"  ✓ Inserted {len(products)} products ({count}/{count})")

    print(f"✅ Seeded {count} products")


def seed_chat_sessions(session, count: int = 1000):
    """Seed chat_sessions table with Faker data."""
    batch_size = 100
    sessions = []

    for i in range(count):
        session_obj = ChatSession(
            id=str(uuid.uuid4()),
            user_id=fake.uuid4(),
            data={
                "messages": [
                    {
                        "role": "user",
                        "content": fake.sentence(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    {
                        "role": "assistant",
                        "content": fake.paragraph(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ],
                "metadata": {
                    "user_agent": fake.user_agent(),
                    "ip_address": fake.ipv4(),
                },
            },
            created_at=datetime.now(timezone.utc) - timedelta(days=fake.random_int(min=0, max=30)),
            updated_at=datetime.now(timezone.utc),
        )
        sessions.append(session_obj)

        # Batch insert every 100 records
        if len(sessions) >= batch_size:
            session.add_all(sessions)
            session.commit()
            print(f"  ✓ Inserted {len(sessions)} chat sessions ({i + 1}/{count})")
            sessions = []

    # Insert remaining sessions
    if sessions:
        session.add_all(sessions)
        session.commit()
        print(f"  ✓ Inserted {len(sessions)} chat sessions ({count}/{count})")

    print(f"✅ Seeded {count} chat sessions")


def seed_documents(session, count: int = 1000):
    """Seed documents table with Faker data."""
    batch_size = 100
    documents = []

    for i in range(count):
        doc = Document(
            id=str(uuid.uuid4()),
            title=fake.sentence(nb_words=6),
            content=fake.paragraph(nb_sentences=10),
            embedding=[
                fake.pyfloat(
                    left_digits=0,
                    right_digits=6,
                    positive=True,
                    min_value=-1,
                    max_value=1,
                )
                for _ in range(768)
            ],
            doc_metadata={
                "author": fake.name(),
                "source": fake.url(),
                "tags": [fake.word() for _ in range(3)],
                "language": "en",
            },
            created_at=datetime.now(timezone.utc) - timedelta(days=fake.random_int(min=0, max=90)),
        )
        documents.append(doc)

        # Batch insert every 100 records
        if len(documents) >= batch_size:
            session.add_all(documents)
            session.commit()
            print(f"  ✓ Inserted {len(documents)} documents ({i + 1}/{count})")
            documents = []

    # Insert remaining documents
    if documents:
        session.add_all(documents)
        session.commit()
        print(f"  ✓ Inserted {len(documents)} documents ({count}/{count})")

    print(f"✅ Seeded {count} documents")


def main():
    """Run all seeders."""
    print("🌱 Starting database seeding with 1000 of each entity...\n")

    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created\n")

    # Create session
    db = SessionLocal()

    try:
        # Seed data - 1000 of each
        print("📦 Seeding products...")
        seed_products(db, count=1000)

        print("💬 Seeding chat sessions...")
        seed_chat_sessions(db, count=1000)

        print("📄 Seeding documents...")
        seed_documents(db, count=1000)

        print("\n✅ Database seeding complete!")
        print("   - 1000 products")
        print("   - 1000 chat sessions")
        print("   - 1000 documents")
        print("   - Total: 3000 entities")
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
