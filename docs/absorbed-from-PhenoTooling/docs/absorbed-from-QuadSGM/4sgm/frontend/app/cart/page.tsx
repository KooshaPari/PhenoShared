'use client'

import { useState } from 'react'
import { ArrowLeft, Plus, Minus, Trash2, ShoppingCart, Package, CreditCard, ShieldCheck, Truck } from 'lucide-react'
import Link from 'next/link'

export default function CartPage() {
  const [cartItems, setCartItems] = useState([
    {
      id: '12132',
      name: 'AFA Messi 10 Official Licensed Soccer Ball, Size 5, Black',
      price: 6.75,
      quantity: 8,
      cp: 8,
      image: '/api/placeholder/80/80',
      total: 54.00
    },
    {
      id: '36530',
      name: 'American Lifetime Swimming Aid Kickboard, Blue and Yellow, Groove Grip',
      price: 1.45,
      quantity: 12,
      cp: 12,
      image: '/api/placeholder/80/80',
      total: 17.40
    },
    {
      id: '14309',
      name: 'Awaken by Quality Choice Makeup Remover Wet Towelettes, Gentle Cleansing, 25 Count',
      price: 0.45,
      quantity: 24,
      cp: 24,
      image: '/api/placeholder/80/80',
      total: 10.80
    }
  ])

  const [isCheckingOut, setIsCheckingOut] = useState(false)

  const updateQuantity = (id: string, newQuantity: number) => {
    if (newQuantity <= 0) {
      removeItem(id)
      return
    }

    setCartItems(prev => prev.map(item => {
      if (item.id === id) {
        const casePack = item.cp
        // Ensure quantity is multiple of case pack
        const adjustedQuantity = Math.ceil(newQuantity / casePack) * casePack
        return {
          ...item,
          quantity: adjustedQuantity,
          total: adjustedQuantity * item.price
        }
      }
      return item
    }))
  }

  const removeItem = (id: string) => {
    setCartItems(prev => prev.filter(item => item.id !== id))
  }

  const getSubtotal = () => {
    return cartItems.reduce((sum, item) => sum + item.total, 0)
  }

  const getTotalItems = () => {
    return cartItems.reduce((sum, item) => sum + item.quantity, 0)
  }

  const getTotalCases = () => {
    return cartItems.reduce((sum, item) => sum + Math.ceil(item.quantity / item.cp), 0)
  }

  const handleCheckout = () => {
    setIsCheckingOut(true)
    setTimeout(() => {
      alert('Order placed successfully! (This is a demo)')
      setIsCheckingOut(false)
    }, 2000)
  }

  if (cartItems.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <Link href="/" className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-6">
            <ArrowLeft className="h-5 w-5 mr-2" />
            Continue Shopping
          </Link>

          <div className="text-center py-16">
            <ShoppingCart className="h-24 w-24 text-gray-300 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">Your cart is empty</h2>
            <p className="text-gray-600 mb-8">Add some products to get started with your order.</p>
            <Link
              href="/"
              className="inline-flex items-center bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Browse Products
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Link href="/" className="inline-flex items-center text-blue-600 hover:text-blue-700">
            <ArrowLeft className="h-5 w-5 mr-2" />
            Continue Shopping
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Shopping Cart</h1>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Cart Items ({getTotalItems()} units, {getTotalCases()} cases)
                  </h2>
                  <span className="text-sm text-gray-600">Minimum order: $500</span>
                </div>
              </div>

              <div className="divide-y divide-gray-200">
                {cartItems.map((item) => (
                  <div key={item.id} className="p-6">
                    <div className="flex items-start space-x-4">
                      {/* Product Image */}
                      <div className="flex-shrink-0">
                        <div className="w-20 h-20 bg-gray-100 rounded-lg flex items-center justify-center">
                          <Package className="h-10 w-10 text-gray-400" />
                        </div>
                      </div>

                      {/* Product Details */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-900 line-clamp-2">
                          {item.name}
                        </h3>
                        <div className="mt-1 text-sm text-gray-600">
                          <span>Item #{item.id} | CP: {item.cp}</span>
                        </div>
                        <div className="mt-2 flex items-center space-x-4">
                          <span className="text-lg font-semibold text-green-600">
                            ${item.price}/each
                          </span>
                          <span className="text-sm text-gray-500">
                            ${(item.price * item.cp).toFixed(2)} per case
                          </span>
                        </div>
                      </div>

                      {/* Quantity Controls */}
                      <div className="flex flex-col items-end space-y-2">
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => updateQuantity(item.id, item.quantity - item.cp)}
                            className="p-1 text-gray-400 hover:text-gray-600"
                          >
                            <Minus className="h-4 w-4" />
                          </button>
                          <span className="w-16 text-center font-medium">{item.quantity}</span>
                          <button
                            onClick={() => updateQuantity(item.id, item.quantity + item.cp)}
                            className="p-1 text-gray-400 hover:text-gray-600"
                          >
                            <Plus className="h-4 w-4" />
                          </button>
                        </div>
                        <div className="text-sm text-gray-500">
                          {Math.ceil(item.quantity / item.cp)} case(s)
                        </div>
                      </div>

                      {/* Total and Remove */}
                      <div className="text-right">
                        <div className="text-lg font-semibold text-gray-900">
                          ${item.total.toFixed(2)}
                        </div>
                        <button
                          onClick={() => removeItem(item.id)}
                          className="mt-2 text-red-600 hover:text-red-800 text-sm flex items-center"
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Order Summary</h2>

              <div className="space-y-3 mb-6">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Subtotal ({getTotalItems()} units)</span>
                  <span className="font-medium">${getSubtotal().toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total Cases</span>
                  <span className="font-medium">{getTotalCases()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Shipping</span>
                  <span className="font-medium text-green-600">FREE</span>
                </div>
                <div className="border-t border-gray-200 pt-3">
                  <div className="flex justify-between text-lg font-semibold">
                    <span>Total</span>
                    <span className="text-green-600">${getSubtotal().toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Minimum Order Alert */}
              {getSubtotal() < 500 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                  <p className="text-sm text-yellow-800">
                    Add <strong>${(500 - getSubtotal()).toFixed(2)}</strong> more to reach the minimum order requirement of $500.
                  </p>
                </div>
              )}

              {/* Checkout Button */}
              <button
                onClick={handleCheckout}
                disabled={isCheckingOut || getSubtotal() < 500}
                className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-semibold mb-4"
              >
                {isCheckingOut ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Processing...
                  </div>
                ) : (
                  <div className="flex items-center justify-center">
                    <CreditCard className="h-5 w-5 mr-2" />
                    Proceed to Checkout
                  </div>
                )}
              </button>

              {/* Login Button */}
              <button className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition-colors font-semibold mb-6">
                Login to Place Order
              </button>

              {/* Security and Trust */}
              <div className="space-y-3 text-sm text-gray-600">
                <div className="flex items-center">
                  <ShieldCheck className="h-4 w-4 mr-2 text-green-600" />
                  <span>Secure checkout with SSL encryption</span>
                </div>
                <div className="flex items-center">
                  <Truck className="h-4 w-4 mr-2 text-blue-600" />
                  <span>Fast shipping within 24-48 hours</span>
                </div>
              </div>

              {/* Order Notes */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-sm font-medium text-gray-900 mb-2">Order Notes</h3>
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  rows={3}
                  placeholder="Special instructions for your order..."
                />
              </div>
            </div>
          </div>
        </div>

        {/* Continue Shopping */}
        <div className="mt-8 text-center">
          <Link
            href="/"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Continue Shopping
          </Link>
        </div>
      </div>
    </div>
  )
}
