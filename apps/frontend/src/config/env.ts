const DEFAULT_API_BASE_URL = 'http://localhost:8000/api'

/** Remove a trailing slash so callers can safely append `/reviews`, etc. */
function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

function resolveApiBaseUrl(rawValue: string | undefined): string {
  if (typeof rawValue !== 'string' || rawValue.trim() === '') {
    return DEFAULT_API_BASE_URL
  }
  return stripTrailingSlash(rawValue.trim())
}

export interface AppEnv {
  /** Base URL of the Guardian AI backend API, without a trailing slash. */
  readonly apiBaseUrl: string
}

export const env: AppEnv = {
  apiBaseUrl: resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL),
}
