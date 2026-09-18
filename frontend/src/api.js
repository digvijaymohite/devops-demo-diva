const BASE = '/api'

async function parse(response) {
  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }
  if (!response.ok) {
    const error = new Error(body?.error || `Request failed (${response.status}).`)
    error.field = body?.field
    error.status = response.status
    throw error
  }
  return body
}

export async function fetchShoutouts({ limit = 20, cursor = null } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) params.set('cursor', cursor)
  return parse(await fetch(`${BASE}/shoutouts?${params}`))
}

export async function postShoutout({ firstName, lastName, message, image }) {
  const form = new FormData()
  form.append('first_name', firstName)
  form.append('last_name', lastName)
  form.append('message', message)
  if (image) form.append('image', image)
  return parse(await fetch(`${BASE}/shoutouts`, { method: 'POST', body: form }))
}
