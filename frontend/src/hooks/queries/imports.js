import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '../../api/client'

export function useImports() {
  return useQuery({
    queryKey: ['imports'],
    queryFn: () => client.get('/imports').then(r => r.data),
  })
}

export function useDeleteImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id) => client.delete(`/imports/${id}`).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['imports'] }),
  })
}

export function useUploadFile(importId) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file) => {
      const formData = new FormData()
      formData.append('file', file)
      // Omit Content-Type — browser sets it automatically with the correct boundary
      return client.patch(`/imports/${importId}/file`, formData).then(r => r.data)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['imports'] }),
  })
}
