import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.jsx'

function respuestaJson(datos, status = 200) {
  return new Response(JSON.stringify(datos), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function respuestaVacia(status = 204) {
  return new Response(null, { status })
}

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

describe('Cuentas y sesión en el frontend (RF-01, HU-10, SDS 3.5)', () => {
  it('redirige a /login cuando se visita una ruta interna sin sesión', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(respuestaVacia(401))
    renderEn('/proyectos')
    expect(
      await screen.findByRole('heading', { name: 'Iniciar sesión' }),
    ).toBeInTheDocument()
  })

  it('PR-RF01-01: registra una cuenta válida y redirige a /proyectos/nuevo (RNF-04)', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') return Promise.resolve(respuestaVacia(401))
      if (url === '/api/auth/register/') {
        return Promise.resolve(
          respuestaJson({ id: 1, email: 'ana@correo.com' }, 201),
        )
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/registro')
    expect(
      await screen.findByRole('heading', { name: 'Crear cuenta' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Mínimo 8 caracteres.')).toBeInTheDocument()
    expect(
      screen.getByText('La cuenta queda activa al instante.'),
    ).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Correo'), {
      target: { value: 'ana@correo.com' },
    })
    fireEvent.change(screen.getByLabelText('Contraseña'), {
      target: { value: 'secreta123' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(
      await screen.findByRole('heading', { name: 'Registrar proyecto' }),
    ).toBeInTheDocument()
    expect(screen.getByText('ana@correo.com')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/register/',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('PR-RF01-02 (CA-01): muestra el error junto al correo cuando ya está registrado (409) y conserva lo capturado', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') return Promise.resolve(respuestaVacia(401))
      if (url === '/api/auth/register/') {
        return Promise.resolve(
          respuestaJson(
            { email: ['Ya existe una cuenta con este correo.'] },
            409,
          ),
        )
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/registro')
    const inputCorreo = await screen.findByLabelText('Correo')
    fireEvent.change(inputCorreo, { target: { value: 'ana@correo.com' } })
    fireEvent.change(screen.getByLabelText('Contraseña'), {
      target: { value: 'secreta123' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(
      await screen.findByText('Ya existe una cuenta con este correo.'),
    ).toBeInTheDocument()
    expect(inputCorreo).toHaveValue('ana@correo.com')
  })

  it('PR-RF01-03 (CA-02): rechaza contraseñas de menos de 8 caracteres en el registro', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(respuestaVacia(401))

    renderEn('/registro')
    fireEvent.change(await screen.findByLabelText('Correo'), {
      target: { value: 'ana@correo.com' },
    })
    fireEvent.change(screen.getByLabelText('Contraseña'), {
      target: { value: 'corta12' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(
      await screen.findByText(
        'La contraseña debe tener al menos 8 caracteres.',
      ),
    ).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalledWith(
      '/api/auth/register/',
      expect.anything(),
    )
  })

  it('inicia sesión y lleva a /proyectos cuando el usuario ya tiene proyectos', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') return Promise.resolve(respuestaVacia(401))
      if (url === '/api/auth/login/') {
        return Promise.resolve(
          respuestaJson({ id: 1, email: 'ana@correo.com' }, 200),
        )
      }
      if (url === '/api/projects/') {
        return Promise.resolve(
          respuestaJson([{ id: 10, nombre: 'Gestor SQA' }], 200),
        )
      }
      if (url === '/api/health/') {
        return Promise.resolve(respuestaJson({ status: 'ok' }, 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/login')
    fireEvent.change(await screen.findByLabelText('Correo'), {
      target: { value: 'ana@correo.com' },
    })
    fireEvent.change(screen.getByLabelText('Contraseña'), {
      target: { value: 'secreta123' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    expect(
      await screen.findByRole('heading', { name: 'Mis proyectos' }),
    ).toBeInTheDocument()
    expect(await screen.findByText('Servicio: disponible')).toBeInTheDocument()
  })

  it('inicia sesión y lleva a /proyectos/nuevo cuando el usuario no tiene proyectos (SDS 3.5)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') return Promise.resolve(respuestaVacia(401))
      if (url === '/api/auth/login/') {
        return Promise.resolve(
          respuestaJson({ id: 1, email: 'nuevo@correo.com' }, 200),
        )
      }
      if (url === '/api/projects/') {
        return Promise.resolve(respuestaJson([], 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/login')
    fireEvent.change(await screen.findByLabelText('Correo'), {
      target: { value: 'nuevo@correo.com' },
    })
    fireEvent.change(screen.getByLabelText('Contraseña'), {
      target: { value: 'secreta123' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    expect(
      await screen.findByRole('heading', { name: 'Registrar proyecto' }),
    ).toBeInTheDocument()
  })

  it('PR-RF01-04 (CA-03): muestra mensaje genérico con credenciales incorrectas (400)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') return Promise.resolve(respuestaVacia(401))
      if (url === '/api/auth/login/') {
        return Promise.resolve(
          respuestaJson({ detail: 'Correo o contraseña incorrectos.' }, 400),
        )
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/login')
    fireEvent.change(await screen.findByLabelText('Correo'), {
      target: { value: 'ana@correo.com' },
    })
    fireEvent.change(screen.getByLabelText('Contraseña'), {
      target: { value: 'equivocada' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent('Correo o contraseña incorrectos.')
  })

  it('PR-RNF05-02: informa cuando se excede el límite de intentos de inicio de sesión (429)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') return Promise.resolve(respuestaVacia(401))
      if (url === '/api/auth/login/') {
        return Promise.resolve(respuestaJson({ detail: 'Throttled' }, 429))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/login')
    fireEvent.change(await screen.findByLabelText('Correo'), {
      target: { value: 'ana@correo.com' },
    })
    fireEvent.change(screen.getByLabelText('Contraseña'), {
      target: { value: 'equivocada' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Demasiados intentos. Espera un momento y vuelve a intentarlo.',
    )
  })

  it('PR-RF01-05 (CA-04): cierra la sesión y vuelve a /login', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(
          respuestaJson({ id: 1, email: 'ana@correo.com' }, 200),
        )
      }
      if (url === '/api/health/') {
        return Promise.resolve(respuestaJson({ status: 'ok' }, 200))
      }
      if (url === '/api/auth/logout/') {
        return Promise.resolve(respuestaVacia(204))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/proyectos')
    expect(
      await screen.findByRole('heading', { name: 'Mis proyectos' }),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Iniciar sesión' }),
      ).toBeInTheDocument()
    })
  })

  it('solicita el token CSRF antes de hacer POST si la cookie no existe (ADR-05)', async () => {
    document.cookie = 'csrftoken=; Max-Age=0'
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') return Promise.resolve(respuestaVacia(401))
      if (url === '/api/auth/csrf/') {
        document.cookie = 'csrftoken=nuevo-csrf'
        return Promise.resolve(respuestaVacia(204))
      }
      if (url === '/api/auth/login/') {
        return Promise.resolve(
          respuestaJson({ detail: 'Correo o contraseña incorrectos.' }, 400),
        )
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/login')
    fireEvent.change(await screen.findByLabelText('Correo'), {
      target: { value: 'ana@correo.com' },
    })
    fireEvent.change(screen.getByLabelText('Contraseña'), {
      target: { value: 'secreta123' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    await screen.findByRole('alert')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/csrf/',
      expect.objectContaining({ credentials: 'same-origin' }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/login/',
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-CSRFToken': 'nuevo-csrf' }),
      }),
    )
  })

  it('muestra "Página no encontrada" en una ruta desconocida', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(respuestaVacia(401))
    renderEn('/ruta/que/no/existe')
    expect(
      await screen.findByRole('heading', { name: 'Página no encontrada' }),
    ).toBeInTheDocument()
  })
})
