'use client'

import { useState, use } from 'react'
import { ArrowLeft, ShoppingCart, Heart, Share2, Package, Star, Truck, Shield } from 'lucide-react'

export default function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [quantity, setQuantity] = useState(1)
  const [activeTab, setActiveTab] = useState('description')

  // Mock product data - in real app, this would fetch from API
  const product = {
    id,
    name: 'AFA Messi 10 Official Licensed Soccer Ball, Size 5, Black',
    price: 6.75,
    originalPrice: null,
    qoh: 1733,
    cp: 8,
    category: 'Sports Equipment',
    brand: 'AFA',
    rating: 4.5,
    reviews: 23,
    image: '/api/placeholder/400/400',
    description: 'Official FIFA-approved soccer ball featuring Messi\'s signature design. Perfect for professional and recreational play.',
    specifications: [
      'Size 5 (Ages 12+)',
      'Official FIFA certification',
      'Synthetic leather construction',
      'Machine-stitched seams',
      'Inflatable air bladder',
      'Messi signature branding'
    ],
    features: [
      'High-quality synthetic leather',
      'Durable construction for outdoor play',
      'Official sizing and weight',
      'Licensed AFA merchandise',
      'Professional grade performance'
    ]
  }

  const relatedProducts = [
    { id: '12127', name: 'AFA Messi 10 Official Licensed Soccer Ball, Size 5, Blue', price: 6.75, image: '/api/placeholder/200/200' },
    { id: '12133', name: 'FIFA Quality Soccer Ball - Professional Grade', price: 12.99, image: '/api/placeholder/200/200' },
    { id: '12134', name: 'Training Soccer Ball - Size 4', price: 8.50, image: '/api/placeholder/200/200' },
    { id: '12135', name: 'Youth Soccer Ball - Size 3', price: 7.25, image: '/api/placeholder/200/200' },
  ]

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => window.history.back()}
                className="flex items-center text-gray-600 hover:text-blue-600"
              >
                <ArrowLeft className="h-5 w-5 mr-2" />
                Back to Products
              </button>
            </div>
            <div className="flex items-center space-x-4">
              <button className="text-gray-600 hover:text-blue-600">
                <ShoppingCart className="h-6 w-6" />
              </button>
              <button className="text-gray-600 hover:text-blue-600">
                <Heart className="h-6 w-6" />
              </button>
              <button className="text-gray-600 hover:text-blue-600">
                <Share2 className="h-6 w-6" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-12">
          {/* Product Image */}
          <div className="space-y-4">
            <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center">
              <Package className="h-32 w-32 text-gray-400" />
            </div>
            <div className="grid grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="aspect-square bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center cursor-pointer hover:bg-gray-200 transition-colors">
                  <Package className="h-12 w-12 text-gray-400" />
                </div>
              ))}
            </div>
          </div>

          {/* Product Details */}
          <div className="space-y-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{product.name}</h1>
              <div className="flex items-center space-x-4 mb-4">
                <div className="flex items-center">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star
                      key={star}
                      className={`h-5 w-5 ${
                        star <= Math.floor(product.rating)
                          ? 'text-yellow-400 fill-current'
                          : 'text-gray-300'
                      }`}
                    />
                  ))}
                  <span className="ml-2 text-sm text-gray-600">
                    {product.rating} ({product.reviews} reviews)
                  </span>
                </div>
                <span className="text-sm text-gray-500">|</span>
                <span className="text-sm text-gray-600">Brand: {product.brand}</span>
              </div>
            </div>

            {/* Pricing */}
            <div className="space-y-2">
              <div className="flex items-baseline space-x-4">
                <span className="text-4xl font-bold text-green-600">${product.price}</span>
                <span className="text-lg text-gray-500">/each</span>
                {product.originalPrice && (
                  <span className="text-xl text-gray-400 line-through">${product.originalPrice}</span>
                )}
              </div>
              <div className="text-sm text-gray-600">
                <span>Case Pack: {product.cp} | In Stock: {product.qoh} units</span>
              </div>
            </div>

            {/* Quantity and Add to Cart */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity (Case Pack: {product.cp})
                </label>
                <div className="flex items-center space-x-4">
                  <div className="flex items-center border border-gray-300 rounded-lg">
                    <button
                      onClick={() => setQuantity(Math.max(1, quantity - 1))}
                      className="px-4 py-2 text-gray-600 hover:bg-gray-100"
                    >
                      -
                    </button>
                    <span className="px-4 py-2 border-x border-gray-300">{quantity}</span>
                    <button
                      onClick={() => setQuantity(quantity + 1)}
                      className="px-4 py-2 text-gray-600 hover:bg-gray-100"
                    >
                      +
                    </button>
                  </div>
                  <span className="text-sm text-gray-600">
                    Total: ${(quantity * product.price).toFixed(2)}
                  </span>
                </div>
              </div>

              <div className="flex space-x-4">
                <button className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors font-semibold">
                  Add to Cart
                </button>
                <button className="bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 transition-colors font-semibold">
                  Login to Order
                </button>
              </div>
            </div>

            {/* Key Features */}
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="font-semibold text-gray-900 mb-3">Key Features</h3>
              <ul className="space-y-1 text-sm text-gray-700">
                {product.features.slice(0, 3).map((feature, index) => (
                  <li key={index} className="flex items-center">
                    <span className="w-2 h-2 bg-blue-600 rounded-full mr-3"></span>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>

            {/* Trust Indicators */}
            <div className="grid grid-cols-3 gap-4 py-4 border-t border-b border-gray-200">
              <div className="text-center">
                <Truck className="h-8 w-8 text-green-600 mx-auto mb-2" />
                <p className="text-sm text-gray-600">Fast Shipping</p>
              </div>
              <div className="text-center">
                <Shield className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                <p className="text-sm text-gray-600">Quality Guaranteed</p>
              </div>
              <div className="text-center">
                <Package className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                <p className="text-sm text-gray-600">Wholesale Pricing</p>
              </div>
            </div>
          </div>
        </div>

        {/* Product Information Tabs */}
        <div className="mt-16">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8">
              {['description', 'specifications', 'reviews'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </nav>
          </div>

          <div className="py-8">
            {activeTab === 'description' && (
              <div className="space-y-4">
                <p className="text-gray-700">{product.description}</p>
                <div className="grid md:grid-cols-2 gap-8">
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Product Features</h4>
                    <ul className="space-y-2 text-gray-700">
                      {product.features.map((feature, index) => (
                        <li key={index} className="flex items-center">
                          <span className="w-2 h-2 bg-green-600 rounded-full mr-3"></span>
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Specifications</h4>
                    <ul className="space-y-2 text-gray-700">
                      {product.specifications.map((spec, index) => (
                        <li key={index} className="flex items-center">
                          <span className="w-2 h-2 bg-blue-600 rounded-full mr-3"></span>
                          {spec}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'specifications' && (
              <div className="grid md:grid-cols-2 gap-8">
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3">Technical Specifications</h4>
                  <dl className="space-y-2">
                    {product.specifications.map((spec, index) => (
                      <div key={index} className="flex justify-between py-2 border-b border-gray-200">
                        <dt className="text-gray-600">Specification {index + 1}</dt>
                        <dd className="text-gray-900 font-medium">{spec}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3">Product Details</h4>
                  <dl className="space-y-2">
                    <div className="flex justify-between py-2 border-b border-gray-200">
                      <dt className="text-gray-600">Item Number</dt>
                      <dd className="text-gray-900 font-medium">{product.id}</dd>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-200">
                      <dt className="text-gray-600">Category</dt>
                      <dd className="text-gray-900 font-medium">{product.category}</dd>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-200">
                      <dt className="text-gray-600">Brand</dt>
                      <dd className="text-gray-900 font-medium">{product.brand}</dd>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-200">
                      <dt className="text-gray-600">Case Pack</dt>
                      <dd className="text-gray-900 font-medium">{product.cp} units</dd>
                    </div>
                  </dl>
                </div>
              </div>
            )}

            {activeTab === 'reviews' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-gray-900">Customer Reviews</h4>
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                    Write Review
                  </button>
                </div>
                <div className="text-center py-8 text-gray-500">
                  <p>No reviews yet. Be the first to review this product!</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Related Products */}
        <div className="mt-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-8">Related Products</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {relatedProducts.map((relatedProduct) => (
              <div key={relatedProduct.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer">
                <div className="aspect-square bg-gray-100 flex items-center justify-center">
                  <Package className="h-16 w-16 text-gray-400" />
                </div>
                <div className="p-4">
                  <h3 className="font-medium text-gray-900 text-sm mb-2 line-clamp-2">
                    {relatedProduct.name}
                  </h3>
                  <p className="text-lg font-bold text-green-600">${relatedProduct.price}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
