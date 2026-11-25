import { getProducts, type Product } from '@/db/queries';
import HomePageClient from '@/components/home-page-client';

interface NewArrival {
  id: string;
  name: string;
  price: string;
  qoh: string;
  cp: string;
  image: string;
}

interface DailyDeal extends NewArrival {
  originalPrice: string;
  salePrice: string;
  tag: string;
}

export default async function Home() {
  // Fetch products from Supabase database
  let products: Product[] = [];
  try {
    products = await getProducts();
  } catch (error) {
    console.error('Failed to fetch products:', error);
    // Fall back to empty array; client will show placeholder
  }

  // Transform products for display
  const newArrivals: NewArrival[] = products.slice(0, 8).map((p) => ({
    id: p.id,
    name: p.name,
    price: p.price?.toString() || '0.00',
    qoh: p.quantityOnHand?.toString() || '0',
    cp: '1',
    image: '/api/placeholder/200/200',
  }));

  const dailyDeals: DailyDeal[] = products
    .filter((p) => p.category === 'seasonal' || p.category === 'electronics')
    .slice(0, 4)
    .map((p) => ({
      id: p.id,
      name: p.name,
      price: p.price?.toString() || '0.00',
      originalPrice: ((p.price || 0) * 1.1).toFixed(2),
      salePrice: p.price?.toString() || '0.00',
      qoh: p.quantityOnHand?.toString() || '0',
      cp: '1',
      tag: 'MONTHLY SPECIAL',
      image: '/api/placeholder/200/200',
    }));

  return (
    <HomePageClient
      newArrivals={newArrivals}
      dailyDeals={dailyDeals}
      productsCount={products.length}
    />
  );
}
