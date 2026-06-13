export interface User {
  id: string
  email: string
  display_name: string
  is_admin: boolean
  onboarding_completed: boolean
  onboarding_step: number
  language_preference: string
}

export interface AuthTokenPayload {
  exp: number
  [key: string]: unknown
}
