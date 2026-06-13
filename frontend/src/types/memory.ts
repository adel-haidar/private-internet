export interface Memory {
  memory_id: string
  title: string
  content: string
  tags: string[]
  created_at: string
  updated_at: string | null
}

export interface MemoryListResponse {
  items: Memory[]
  total: number
  page: number
  pages: number
}

export interface MemoryStats {
  total: number
  last_updated: string | null
}

export interface CreateMemoryPayload {
  title: string
  content: string
  tags: string[]
}

export interface CreateMemoryResponse {
  memory_id: string
}
