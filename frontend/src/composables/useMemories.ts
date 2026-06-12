import { requireAuth } from './useAuth'

import { API_BASE } from '../config/env'

export interface UpdateMemoryPayload {
  title?: string
  content?: string
  tags?: string[]
  append_content?: boolean
}

export interface UpdatedMemory {
  memory_id: string
  title: string
  content: string
  tags: string[]
  updated_at: string | null
}

export async function updateMemory(id: string, payload: UpdateMemoryPayload): Promise<UpdatedMemory> {
  const token = await requireAuth()
  const res = await fetch(`${API_BASE}/api/memory/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function deleteMemory(id: string): Promise<{ deleted: boolean; memory_id: string }> {
  const token = await requireAuth()
  const res = await fetch(`${API_BASE}/api/memory/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}
