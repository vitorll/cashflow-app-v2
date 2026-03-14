import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'

/**
 * Creates a fresh QueryClient configured for tests:
 * - retry: 0   — no retries so failures surface immediately
 * - gcTime: 0  — garbage-collect cache instantly between tests
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 0,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: 0,
      },
    },
  })
}

/**
 * Renders `ui` inside a fresh QueryClientProvider.
 * Pass `{ queryClient }` in options to supply your own client instance.
 */
export function renderWithQuery(ui, { queryClient, ...options } = {}) {
  const client = queryClient ?? createTestQueryClient()
  const Wrapper = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return render(ui, { wrapper: Wrapper, ...options })
}
