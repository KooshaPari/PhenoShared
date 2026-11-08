'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { ArrowLeft, Package, Grid, List, SlidersHorizontal } from 'lucide-react'
import Link from 'next/link'

interface Product {
  id: string
  name: string
  price: number
  qoh: number
  cp: number
  brand: string
  category: string
  hasLicense: boolean
  image: string
}

export default function CategoryPage() {
  const params = useParams<{ category: string }>()
  const category = params.category || ''
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [showFilters, setShowFilters] = useState(false)
  const [sortBy, setSortBy] = useState('relevance')

  const [filters, setFilters] = useState({
    brand: '',
    priceRange: '',
    inStock: true,
    casePack: '',
    hasLicense: false
  })

  // Mock products by category
  const getProductsByCategory = (cat: string): Product[] => {
    const allProducts: Record<string, Product[]> = {
      housewares: [
        {
          id: '10388',
          name: 'BATH TOWEL, 27 X 54", NATURAL',
          price: 2.65,
          qoh: 468,
          cp: 36,
          brand: 'Generic',
          category: 'Housewares',
          hasLicense: false,
          image: '/api/placeholder/200/200'
        },
        {
          id: '14739',
          name: 'BATH TOWEL, 27X54 ", GREY',
          price: 2.65,
          qoh: 360,
          cp: 36,
          brand: 'Generic',
          category: 'Housewares',
          hasLicense: false,
          image: '/api/placeholder/200/200'
        },
        {
          id: '10385',
          name: 'BATH TOWEL, 27X54", WHITE',
          price: 2.65,
          qoh: 2910,
          cp: 30,
          brand: 'Generic',
          category: 'Housewares',
          hasLicense: false,
          image: '/api/placeholder/200/200'
        }
      ],
      toys: [
        {
          id: '14297',
          name: 'Animal Empire Friction Stunt Animal Motorcycle, 4", Assorted',
          price: 0.69,
          qoh: 1428,
          cp: 12,
          brand: 'Animal Empire',
          category: 'Toys',
          hasLicense: false,
          image: '/api/placeholder/200/200'
        },
        {
          id: '54766',
          name: '256pg Spanish Spiral Puzzle Book- 2 Assortments',
          price: 1.55,
          qoh: 4788,
          cp: 36,
          brand: 'Generic',
          category: 'Toys',
          hasLicense: false,
          image: '/api/placeholder/200/200'
        }
      ],
      licensed: [
        {
          id: '12132',
          name: 'AFA Messi 10 Official Licensed Soccer Ball, Size 5, Black',
          price: 6.75,
          qoh: 1733,
          cp: 8,
          brand: 'AFA',
          category: 'Licensed Goods',
          hasLicense: true,
          image: '/api/placeholder/200/200'
        },
        {
          id: '99643',
          name: 'Bluey Reusable Tote Bags, 16 in, Assorted Colors',
          price: 0.79,
          qoh: 26492,
          cp: 72,
          brand: 'Bluey',
          category: 'Licensed Goods',
          hasLicense: true,
          image: '/api/placeholder/200/200'
        }
      ]
    }
    return allProducts[cat] || []
  }

  const categoryProducts = getProductsByCategory(category)

  const categoryNames: Record<string, string> = {
    housewares: 'Housewares',
    toys: 'Toys & Games',
    licensed: 'Licensed Goods',
    health: 'Health & Beauty',
    baby: 'Baby Items',
    seasonal: 'Seasonal Items'
  }

  const currentCategoryName = categoryNames[category] || category

  const brands = ['All Brands', 'AFA', 'Animal Empire', 'Bluey', 'Generic']
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
            <h1 className="text-2xl font-bold text-gray-900">4sgm.com</h1>
            <div className="flex items-center space-x-4">
              <button className="text-gray-600 hover:text-blue-600">
                <Grid className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Category Header */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{currentCategoryName}</h1>
              <p className="text-gray-600">
                Browse our complete selection of {currentCategoryName.toLowerCase()} with wholesale pricing.
                {category === 'licensed' && ' Featuring official licensed characters and brands.'}
              </p>
            </div>
            <div className="mt-4 md:mt-0">
              <div className="bg-red-600 text-white text-center py-2 px-4 rounded-lg">
                <p className="font-semibold text-sm">Minimum Order: $500</p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Filters Sidebar */}
          <div className={`lg:w-64 ${showFilters ? 'block' : 'hidden lg:block'}`}>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Filters</h3>

              <div className="space-y-6">
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
                  {category === 'licensed' && (
                    <div className="flex items-center">
                      <input
                        id="hasLicense"
                        type="checkbox"
                        checked={filters.hasLicense}
                        onChange={(e) => setFilters(prev => ({ ...prev, hasLicense: e.target.checked }))}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <label htmlFor="hasLicense" className="ml-2 text-sm text-gray-700">
                        Licensed Products Only
                      </label>
                    </div>
                  )}

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
                </div>

                {/* Clear Filters */}
                <button
                  onClick={() => setFilters({
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

          {/* Products Section */}
          <div className="flex-1">
            {/* Controls */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {currentCategoryName} Products
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Showing {categoryProducts.length} products
                </p>
              </div>

              <div className="flex items-center space-x-4 mt-4 sm:mt-0">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="lg:hidden flex items-center px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm"
                >
                  <SlidersHorizontal className="h-4 w-4 mr-2" />
                  Filters
                </button>

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

            {/* Products Grid/List */}
            {categoryProducts.length > 0 ? (
              viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {categoryProducts.map(product => (
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
                  {categoryProducts.map(product => (
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
              )
            ) : (
              <div className="text-center py-16">
                <Package className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No products found</h3>
                <p className="text-gray-600 mb-6">We couldn't find any products in this category with the current filters.</p>
                <button
                  onClick={() => setFilters({
                    brand: '',
                    priceRange: '',
                    inStock: true,
                    casePack: '',
                    hasLicense: false
                  })}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Clear Filters
                </button>
              </div>
            )}

            {/* Load More / Pagination */}
            {categoryProducts.length > 0 && (
              <div className="text-center mt-12">
                <button className="bg-white border border-gray-300 text-gray-700 px-8 py-3 rounded-lg hover:bg-gray-50 transition-colors">
                  Load More Products
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
