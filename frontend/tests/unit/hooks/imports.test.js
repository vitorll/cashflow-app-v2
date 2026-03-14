import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { createTestQueryClient } from '../../utils'

// RED: frontend/src/hooks/queries/imports.js does not exist yet.
import {
  useImports,
  useDeleteImport,
  useUploadFile,
} from '../../../src/hooks/queries/imports'

// Mock the axios client used by the hooks.
vi.mock('../../../src/api/client', () => ({
  default: {
    get: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  },
}))

import client from '../../../src/api/client'

function makeWrapper() {
  const queryClient = createTestQueryClient()
  return ({ children }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useImports', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns data from GET /imports', async () => {
    const fakeImports = [{ id: 'abc', status: 'complete' }]
    client.get.mockResolvedValue({ data: fakeImports })

    const { result } = renderHook(() => useImports(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(client.get).toHaveBeenCalledWith('/imports')
    expect(result.current.data).toEqual(fakeImports)
  })

  it('is in loading state before data resolves', () => {
    // Never resolves — keeps the hook in loading state.
    client.get.mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useImports(), { wrapper: makeWrapper() })

    expect(result.current.isLoading).toBe(true)
  })

  it('exposes error when request fails', async () => {
    const networkError = new Error('Network Error')
    client.get.mockRejectedValue(networkError)

    const { result } = renderHook(() => useImports(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(networkError)
  })
})

describe('useDeleteImport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls DELETE /imports/{id} with the correct URL', async () => {
    client.delete.mockResolvedValue({ data: null })

    const { result } = renderHook(() => useDeleteImport(), {
      wrapper: makeWrapper(),
    })

    result.current.mutate('import-uuid-123')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(client.delete).toHaveBeenCalledWith('/imports/import-uuid-123')
  })
})

describe('useUploadFile', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls PATCH /imports/{id}/file with FormData and no manual Content-Type', async () => {
    const importId = 'import-uuid-456'
    const fakeFile = new File(['content'], 'upload.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const fakeResponse = { id: importId, status: 'complete' }
    client.patch.mockResolvedValue({ data: fakeResponse })

    const { result } = renderHook(() => useUploadFile(importId), {
      wrapper: makeWrapper(),
    })

    result.current.mutate(fakeFile)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(client.patch).toHaveBeenCalledOnce()
    const [url, body, config] = client.patch.mock.calls[0]
    expect(url).toBe(`/imports/${importId}/file`)
    expect(body).toBeInstanceOf(FormData)
    // Content-Type must NOT be set manually — browser sets it with the correct boundary
    expect(config?.headers?.['Content-Type']).toBeUndefined()
    // mutation.data is the unwrapped response, not the Axios envelope
    expect(result.current.data).toEqual(fakeResponse)
  })
})
