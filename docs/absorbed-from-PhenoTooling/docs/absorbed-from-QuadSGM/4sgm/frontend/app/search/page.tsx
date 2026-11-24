'use client'

import { useState } from 'react'
import { Search, Grid, List, ArrowLeft, Package, SlidersHorizontal } from 'lucide-react'
import Link from 'next/link'

export default function SearchPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [showFilters, setShowFilters] = useState(false)
  const [sortBy, setSortBy] = useState('relevance')

  const [filters, setFilters] = useState({
    category: '',
    brand: '',
    priceRange: '',
    inStock: true,
    casePack: '',
    hasLicense: false
  })

  // Mock search results
  const searchResults = [
    {
      id: '12132',
      name: 'AFA Messi 10 Official Licensed Soccer Ball, Size 5, Black',
      price: 6.75,
      qoh: 1733,
      cp: 8,
      brand: 'AFA',
      category: 'Sports Equipment',
      hasLicense: true,
      image: '/api/placeholder/200/200'
    },
    {
      id: '12127',
      name: 'AFA Messi 10 Official Licensed Soccer Ball, Size 5, Blue',
      price: 6.75,
      qoh: 1637,
      cp: 8,
      brand: 'AFA',
      category: 'Sports Equipment',
      hasLicense: true,
      image: '/api/placeholder/200/200'
    },
    {
      id: '36530',
      name: 'American Lifetime Swimming Aid Kickboard, Blue and Yellow, Groove Grip',
      price: 1.45,
      qoh: 188,
      cp: 12,
      brand: 'American Lifetime',
      category: 'Swimming & Water Sports',
      hasLicense: false,
      image: '/api/placeholder/200/200'
    },
    {
      id: '14286',
      name: 'American Lifetime Swimming Aid Kickboard, Pink and Yellow, Groove Grip',
      price: 1.45,
      qoh: 224,
      cp: 12,
      brand: 'American Lifetime',
      category: 'Swimming & Water Sports',
      hasLicense: false,
      image: '/api/placeholder/200/200'
    }
  ]

  const categories = [
    'All Categories',
    'Sports Equipment',
    'Swimming & Water Sports',
    'Health & Beauty',
    'Housewares',
    'Toys & Games',
    'Baby Items',
    'Licensed Goods'
  ]

  const brands = [
    'All Brands',
    'AFA',
    'American Lifetime',
    'Disney',
    'Spiderman',
    'Star Wars',
    'Batman',
    'Hello Kitty'
  ]

  const casePacks = ['Any Case Pack', 'CP: 1-6', 'CP: 7-12', 'CP: 13-24', 'CP: 25+']

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center text-blue-600 hover:text-blue-700">
              <ArrowLeft className="h-5 w-5 mr-2" />
              Back to Homepage
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">4sgm.com Search</h1>
            <div className="flex items-center space-x-4">
              <button className="text-gray-600 hover:text-blue-600">
                <Grid className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Search Bar */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products, brands, or categories..."
                className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <button className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors font-semibold">
              Search
            </button>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <SlidersHorizontal className="h-5 w-5 mr-2" />
              Filters
            </button>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Filters Sidebar */}
          <div className={`lg:w-64 ${showFilters ? 'block' : 'hidden lg:block'}`}>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Filters</h3>

              <div className="space-y-6">
                {/* Category Filter */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Category
                  </label>
                  <select
                    value={filters.category}
                    onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {categories.map(category => (
                      <option key={category} value={category === 'All Categories' ? '' : category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Brand Filter */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Brand
                  </label>
                  <select
                    value={filters.brand}
                    onChange={(e) => setFilters(prev => ({ ...prev, brand: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {brands.map(brand => (
                      <option key={brand} value={brand === 'All Brands' ? '' : brand}>
                        {brand}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Case Pack Filter */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Case Pack
                  </label>
                  <select
                    value={filters.casePack}
                    onChange={(e) => setFilters(prev => ({ ...prev, casePack: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {casePacks.map(pack => (
                      <option key={pack} value={pack === 'Any Case Pack' ? '' : pack}>
                        {pack}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Checkboxes */}
                <div className="space-y-3">
                  <div className="flex items-center">
                    <input
                      id="inStock"
                      type="checkbox"
                      checked={filters.inStock}
                      onChange={(e) => setFilters(prev => ({ ...prev, inStock: e.target.checked }))}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="inStock" className="ml-2 text-sm text-gray-700">
                      In Stock Only
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      id="hasLicense"
                      type="checkbox"
                      checked={filters.hasLicense}
                      onChange={(e) => setFilters(prev => ({ ...prev, hasLicense: e.target.checked }))}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="hasLicense" className="ml-2 text-sm text-gray-700">
                      Licensed Products
                    </label>
                  </div>
                </div>

                {/* Clear Filters */}
                <button
                  onClick={() => setFilters({
                    category: '',
                    brand: '',
                    priceRange: '',
                    inStock: true,
                    casePack: '',
                    hasLicense: false
                  })}
                  className="w-full text-blue-600 hover:text-blue-700 text-sm font-medium py-2 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
                >
                  Clear All Filters
                </button>
              </div>
            </div>
          </div>

          {/* Results Section */}
          <div className="flex-1">
            {/* Results Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Search Results for "{searchQuery || 'All Products'}"
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Showing {searchResults.length} products
                </p>
              </div>

              <div className="flex items-center space-x-4 mt-4 sm:mt-0">
                {/* Sort Dropdown */}
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                >
                  <option value="relevance">Sort by Relevance</option>
                  <option value="price-low">Price: Low to High</option>
                  <option value="price-high">Price: High to Low</option>
                  <option value="name">Name A-Z</option>
                  <option value="stock">Stock Level</option>
                </select>

                {/* View Toggle */}
                <div className="flex border border-gray-300 rounded-lg">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 ${viewMode === 'grid' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'} transition-colors`}
                  >
                    <Grid className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 ${viewMode === 'list' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'} transition-colors`}
                  >
                    <List className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Results Grid/List */}
            {viewMode === 'grid' ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {searchResults.map(product => (
                  <div key={product.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow">
                    <Link href={`/product/${product.id}`}>
                      <div className="aspect-square bg-gray-100 flex items-center justify-center">
                        <Package className="h-16 w-16 text-gray-400" />
                      </div>
                    </Link>
                    <div className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-sm text-green-600 font-bold">${product.price}/each</span>
                        <span className="text-xs text-gray-500">CP: {product.cp}</span>
                      </div>
                      <h3 className="font-medium text-gray-900 text-sm mb-2 line-clamp-2">
                        <Link href={`/product/${product.id}`} className="hover:text-blue-600">
                          {product.name}
                        </Link>
                      </h3>
                      <div className="text-xs text-gray-600 mb-3">
                        <div>Item#: {product.id}</div>
                        <div>QOH: {product.qoh} | {product.brand}</div>
                        {product.hasLicense && (
                          <span className="inline-block bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs mt-1">
                            Licensed
                          </span>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        <button className="flex-1 bg-blue-600 text-white px-3 py-2 rounded text-xs hover:bg-blue-700 transition-colors">
                          Login to Order
                        </button>
                        <button className="bg-gray-200 text-gray-700 px-2 py-2 rounded text-xs hover:bg-gray-300 transition-colors">
                          Cart
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {searchResults.map(product => (
                  <div key={product.id} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow">
                    <div className="flex items-start space-x-6">
                      <Link href={`/product/${product.id}`}>
                        <div className="w-24 h-24 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Package className="h-12 w-12 text-gray-400" />
                        </div>
                      </Link>
                      <div className="flex-1">
                        <div className="flex justify-between items-start mb-2">
                          <h3 className="text-lg font-medium text-gray-900">
                            <Link href={`/product/${product.id}`} className="hover:text-blue-600">
                              {product.name}
                            </Link>
                          </h3>
                          <span className="text-xl font-bold text-green-600 ml-4">${product.price}/each</span>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600 mb-3">
                          <div><strong>Item #:</strong> {product.id}</div>
                          <div><strong>Brand:</strong> {product.brand}</div>
                          <div><strong>Category:</strong> {product.category}</div>
                          <div><strong>Case Pack:</strong> {product.cp}</div>
                          <div><strong>Stock:</strong> {product.qoh} units</div>
                          <div><strong>Price per case:</strong> ${(product.price * product.cp).toFixed(2)}</div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                            Login to Order
                          </button>
                          <button className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors">
                            Add to Cart
                          </button>
                          {product.hasLicense && (
                            <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-xs font-medium">
                              Licensed Product
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Load More / Pagination */}
            <div className="text-center mt-12">
              <button className="bg-white border border-gray-300 text-gray-700 px-8 py-3 rounded-lg hover:bg-gray-50 transition-colors">
                Load More Products
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
