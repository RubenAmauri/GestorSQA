// Cliente de la API REST (SDS 3.4). La sesión viaja en una cookie del mismo
// dominio, y toda petición que modifica datos lleva el token CSRF (ADR-05).

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[2]) : null
}

export async function apiFetch(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET') {
    const token = getCookie('csrftoken')
    if (token) headers['X-CSRFToken'] = token
  }
  const response = await fetch(`/api/${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = response.headers.get('content-type')?.includes('application/json')
    ? await response.json()
    : null
  return { ok: response.ok, status: response.status, data }
}
