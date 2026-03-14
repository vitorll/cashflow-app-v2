import { describe, it, expect } from 'vitest'
// RED: frontend/src/queryClient.js does not exist yet.
import queryClient from '../../src/queryClient'

describe('queryClient', () => {
  it('has staleTime of 30_000 ms for queries', () => {
    const defaults = queryClient.getDefaultOptions()
    expect(defaults.queries?.staleTime).toBe(30_000)
  })

  it('has retry of 1 for queries', () => {
    const defaults = queryClient.getDefaultOptions()
    expect(defaults.queries?.retry).toBe(1)
  })
})
