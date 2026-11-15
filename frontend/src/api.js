// Cliente de la API REST (SDS 3.4). La sesión viaja en una cookie del mismo
// dominio, y toda petición que modifica datos lleva el token CSRF (ADR-05).

export function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[2]) : null
}

export async function apiFetch(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET') {
    if (!getCookie('csrftoken')) {
      await fetch('/api/auth/csrf/', { credentials: 'same-origin' })
    }
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

// Descarga un archivo de la API, como el reporte en CSV (RF-12). Si el servidor
// responde con error (por ejemplo, la sesión expiró), no descarga nada: devuelve
// ok: false con el detalle en JSON para mostrar un mensaje en la página.
export async function apiDescargar(path) {
  const response = await fetch(`/api/${path}`, {
    headers: { Accept: 'text/csv, application/json' },
    credentials: 'same-origin',
  })
  if (!response.ok) {
    const data = response.headers.get('content-type')?.includes('application/json')
      ? await response.json()
      : null
    return { ok: false, status: response.status, data }
  }
  const disposicion = response.headers.get('content-disposition') || ''
  const nombre = disposicion.match(/filename="([^"]+)"/)?.[1] ?? null
  return { ok: true, status: response.status, blob: await response.blob(), nombre }
}
