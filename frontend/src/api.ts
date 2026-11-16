import { AppSnapshot } from './types'

export async function postAction<T = AppSnapshot>(path: string, body: Record<string, unknown> = {}): Promise<T> {
  const resp = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return resp.json() as Promise<T>
}

export async function fetchState(): Promise<AppSnapshot> {
  const resp = await fetch('/api/state')
  return resp.json() as Promise<AppSnapshot>
}
