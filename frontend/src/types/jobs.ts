export type MatchTier = 'STRONG_MATCH' | 'GOOD_MATCH' | 'WEAK_MATCH'

export type JobStatus =
  | 'new'
  | 'reviewing'
  | 'applied'
  | 'interviewing'
  | 'rejected'
  | 'withdrawn'
  | 'expired'

export interface JobMatch {
  id: number
  run_timestamp: string
  platform: string
  title: string
  company: string
  location: string
  country: string
  job_url: string
  posted_date: string | null
  salary_raw: string | null
  salary_min_local: number | null
  salary_max_local: number | null
  currency: string | null
  remote_type: string
  match_score: number
  match_tier: MatchTier
  tech_flags: string[]
  domain_flags: string[]
  positive_flags: string[]
  disqualifier_flag: string | null
  rejection_reason: string | null
  ai_summary: string | null
  status: JobStatus
  applied_at: string | null
  notes: string | null
}

export interface MatchesResponse {
  count: number
  matches: JobMatch[]
}

export interface RunReport {
  report: string
  data: {
    timestamp: string
    platforms: string[]
    countries: string[]
    raw_count: number
    dedup_count: number
    hard_rejected_count: number
    hard_rejected_by_reason: Record<string, number>
    scored_count: number
    strong_matches: unknown[]
    good_matches: unknown[]
    rejection_log: Record<string, string[]>
    db_saved_this_run: number
    db_cumulative: number
  }
}

export interface RunResponse {
  status: string
  message: string
}

export interface Country {
  code: string
  name: string
}

export interface CountriesResponse {
  countries: Country[]
}

export type SortField = 'match_score' | 'run_timestamp' | 'company' | 'country'
export type SortDir = 'asc' | 'desc'
