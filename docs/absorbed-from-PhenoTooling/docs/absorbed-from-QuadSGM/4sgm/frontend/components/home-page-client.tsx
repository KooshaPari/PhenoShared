'use client';

import { useState } from 'react';
import { Search, ShoppingCart, User, Menu, X } from 'lucide-react';

interface Product {
  id: string;
  name: string;
  price: string;
  qoh: string;
  cp: string;
  image: string;
}

interface DailyDeal extends Product {
  originalPrice: string;
  salePrice: string;
  tag: string;
}

interface HomePageClientProps {
  newArrivals: Product[];
  dailyDeals: DailyDeal[];
  productsCount: number;
}

export default function HomePageClient({
  newArrivals,
  dailyDeals,
  productsCount,
}: HomePageClientProps) {
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <div className="text-2xl font-bold text-blue-600">4SGM</div>
            <div className="hidden md:flex items-center space-x-6">
              <a href="#" className="text-gray-600 hover:text-blue-600">
                Catalog
              </a>
              <a href="#" className="text-gray-600 hover:text-blue-600">
                Pricing
              </a>
              <a href="#" className="text-gray-600 hover:text-blue-600">
                Support
              </a>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <button className="hidden md:flex items-center space-x-2 bg-gray-100 px-4 py-2 rounded-lg">
              <Search size={18} />
              <input
                type="text"
                placeholder="Search products..."
                className="bg-transparent outline-none w-48"
              />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg">
              <ShoppingCart size={20} />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg">
              <User size={20} />
            </button>
            <button
              className="md:hidden p-2"
              onClick={() => setShowMobileMenu(!showMobileMenu)}
            >
              {showMobileMenu ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="bg-gradient-to-r from-blue-600 to-blue-800 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <h1 className="text-4xl font-bold mb-4">Everything Your Store Needs</h1>
          <p className="text-xl mb-8">Since 1984 • {productsCount} Products • Wholesale Pricing</p>
          <button className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100">
            Browse Catalog
          </button>
        </div>
      </section>

      {/* New Arrivals */}
      <section className="max-w-7xl mx-auto px-4 py-12">
        <h2 className="text-3xl font-bold mb-8">New Arrivals</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {newArrivals.map((product) => (
            <div key={product.id} className="bg-white rounded-lg shadow hover:shadow-lg transition">
              <img src={product.image} alt={product.name} className="w-full h-48 object-cover rounded-t-lg" />
              <div className="p-4">
                <h3 className="font-semibold text-sm mb-2 line-clamp-2">{product.name}</h3>
                <div className="flex justify-between items-center">
                  <span className="text-lg font-bold text-blue-600">${product.price}</span>
                  <span className="text-xs text-gray-500">QOH: {product.qoh}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Daily Deals */}
      <section className="max-w-7xl mx-auto px-4 py-12">
        <h2 className="text-3xl font-bold mb-8">Daily Deals</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {dailyDeals.map((deal) => (
            <div key={deal.id} className="bg-white rounded-lg shadow hover:shadow-lg transition relative">
              <div className="absolute top-2 right-2 bg-red-600 text-white px-3 py-1 rounded text-xs font-semibold">
                {deal.tag}
              </div>
              <img src={deal.image} alt={deal.name} className="w-full h-48 object-cover rounded-t-lg" />
              <div className="p-4">
                <h3 className="font-semibold text-sm mb-2 line-clamp-2">{deal.name}</h3>
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-sm line-through text-gray-500">${deal.originalPrice}</span>
                  <span className="text-lg font-bold text-red-600">${deal.salePrice}</span>
                </div>
                <span className="text-xs text-gray-500">QOH: {deal.qoh}</span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
