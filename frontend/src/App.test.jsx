import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.jsx'

function renderEn(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <App />
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('Esqueleto de la aplicación', () => {
  it('muestra el estado del servicio cuando la API responde', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    renderEn('/')
    expect(screen.getByRole('heading', { name: 'Gestor SQA' })).toBeInTheDocument()
    expect(await screen.findByText('Servicio: disponible')).toBeInTheDocument()
  })

  it('indica cuando no hay conexión con la API', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('sin red'))
    renderEn('/')
    expect(await screen.findByText('Servicio: sin conexión')).toBeInTheDocument()
  })

  it('muestra "Página no encontrada" en una ruta desconocida', () => {
    renderEn('/ruta/que/no/existe')
    expect(screen.getByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument()
  })
})
