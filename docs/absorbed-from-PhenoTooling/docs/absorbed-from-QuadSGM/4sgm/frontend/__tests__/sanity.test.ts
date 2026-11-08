import { describe, it, expect } from 'vitest'

describe('Sanity Tests', () => {
  it('should pass basic math', () => {
    expect(1 + 1).toBe(2)
  })

  it('should pass string test', () => {
    expect('hello').toBe('hello')
  })

  it('should pass array test', () => {
    const arr = [1, 2, 3]
    expect(arr).toHaveLength(3)
  })
})
