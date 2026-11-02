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

const USUARIO_SESION = { id: 1, email: 'ana@correo.com' }

const PROYECTO_ADMIN = {
  id: 7,
  nombre: 'Gestor SQA',
  periodo_nombre: '2026-2',
  fecha_inicio: '2026-08-10',
  fecha_fin: '2026-12-04',
  mi_clase: 'ADMIN_CREADOR',
  codigo_union: 'ABC1234567',
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
        return Promise.resolve(respuestaJson(USUARIO_SESION, 201))
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
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === '/api/projects/') {
        return Promise.resolve(respuestaJson([PROYECTO_ADMIN], 200))
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
    expect(await screen.findAllByText('Gestor SQA')).not.toHaveLength(0)
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

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Correo o contraseña incorrectos.',
    )
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
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === '/api/projects/') {
        return Promise.resolve(respuestaJson([PROYECTO_ADMIN], 200))
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

describe('Proyectos y unión por código en el frontend (RF-02, RF-03, RF-06)', () => {
  it('PR-RF02-01: registra un proyecto válido y lleva a /proyectos/:id/metricas (RNF-04)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, opciones) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === '/api/projects/' && opciones?.method === 'POST') {
        return Promise.resolve(respuestaJson(PROYECTO_ADMIN, 201))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/`) {
        return Promise.resolve(respuestaJson(PROYECTO_ADMIN, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/metrics/`) {
        return Promise.resolve(respuestaJson([], 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/proyectos/nuevo')
    fireEvent.change(await screen.findByLabelText('Nombre del proyecto *'), {
      target: { value: 'Gestor SQA' },
    })
    fireEvent.change(screen.getByLabelText('Nombre del periodo *'), {
      target: { value: '2026-2' },
    })
    fireEvent.change(screen.getByLabelText('Fecha de inicio *'), {
      target: { value: '2026-08-10' },
    })
    fireEvent.change(screen.getByLabelText('Fecha de fin *'), {
      target: { value: '2026-12-04' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Registrar proyecto' }))

    expect(
      await screen.findByRole('heading', { name: 'Métricas por sprint' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Tu clase: Admin Creador'),
    ).toBeInTheDocument()
  })

  it('PR-RF02-02 (CA-02, Lámina 04b): muestra aviso general y error junto al campo cuando el proyecto está duplicado (409)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, opciones) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === '/api/projects/' && opciones?.method === 'POST') {
        return Promise.resolve(
          respuestaJson(
            {
              detail:
                'Ya registraste un proyecto con este nombre en este periodo.',
            },
            409,
          ),
        )
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/proyectos/nuevo')
    const inputNombre = await screen.findByLabelText('Nombre del proyecto *')
    fireEvent.change(inputNombre, { target: { value: 'gestor SQA' } })
    fireEvent.change(screen.getByLabelText('Nombre del periodo *'), {
      target: { value: '2026-2' },
    })
    fireEvent.change(screen.getByLabelText('Fecha de inicio *'), {
      target: { value: '2026-08-10' },
    })
    fireEvent.change(screen.getByLabelText('Fecha de fin *'), {
      target: { value: '2026-12-04' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Registrar proyecto' }))

    expect(
      await screen.findByText(
        'Ya registraste un proyecto con este nombre en este periodo. Cambia el nombre o el periodo.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Nombre repetido en el periodo 2026-2.'),
    ).toBeInTheDocument()
    expect(inputNombre).toHaveValue('gestor SQA')
  })

  it('PR-RF02-04 (CA-01): valida que la fecha de fin no sea anterior a la de inicio', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/proyectos/nuevo')
    fireEvent.change(await screen.findByLabelText('Nombre del proyecto *'), {
      target: { value: 'Gestor SQA' },
    })
    fireEvent.change(screen.getByLabelText('Nombre del periodo *'), {
      target: { value: '2026-2' },
    })
    fireEvent.change(screen.getByLabelText('Fecha de inicio *'), {
      target: { value: '2026-12-04' },
    })
    fireEvent.change(screen.getByLabelText('Fecha de fin *'), {
      target: { value: '2026-08-10' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Registrar proyecto' }))

    expect(
      await screen.findByText(
        'La fecha de fin no puede ser anterior a la fecha de inicio.',
      ),
    ).toBeInTheDocument()
  })

  it('PR-RF03-01 a 03: permite unirse con código válido y muestra errores en 400 y 409', async () => {
    let estadoRespuesta = 400
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === '/api/projects/join/') {
        if (estadoRespuesta === 400) {
          return Promise.resolve(
            respuestaJson({ detail: 'El código no es válido.' }, 400),
          )
        }
        if (estadoRespuesta === 409) {
          return Promise.resolve(
            respuestaJson({ detail: 'Ya eres miembro de este proyecto.' }, 409),
          )
        }
        return Promise.resolve(
          respuestaJson({ ...PROYECTO_ADMIN, mi_clase: 'COLABORADOR' }, 201),
        )
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/`) {
        return Promise.resolve(
          respuestaJson({ ...PROYECTO_ADMIN, mi_clase: 'COLABORADOR' }, 200),
        )
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/proyectos/unirse')
    const inputCodigo = await screen.findByLabelText('Código del proyecto')

    // PR-RF03-02: código inválido -> 400
    fireEvent.change(inputCodigo, { target: { value: 'NOEXISTE00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Unirse' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El código no es válido.',
    )

    // PR-RF03-03: ya es miembro -> 409
    estadoRespuesta = 409
    fireEvent.click(screen.getByRole('button', { name: 'Unirse' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ya eres miembro de este proyecto.',
    )

    // PR-RF03-01: código válido -> va al reporte del proyecto como Colaborador
    estadoRespuesta = 201
    fireEvent.click(screen.getByRole('button', { name: 'Unirse' }))
    expect(
      await screen.findByText('Tu clase: Colaborador'),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Configuración' }),
    ).not.toBeInTheDocument()
  })

  it('PR-RF03-04 (Lámina 10): regenera el código de unión desde Configuración tras confirmar', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/`) {
        return Promise.resolve(respuestaJson(PROYECTO_ADMIN, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/codigo/regenerar/`) {
        return Promise.resolve(
          respuestaJson({ codigo_union: 'NUEVO99999' }, 200),
        )
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn(`/proyectos/${PROYECTO_ADMIN.id}/configuracion`)
    expect(
      await screen.findByText(PROYECTO_ADMIN.codigo_union),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Regenerar código' }))
    expect(
      screen.getByText('¿Regenerar el código de unión?'),
    ).toBeInTheDocument()

    fireEvent.click(
      screen.getByRole('button', { name: 'Confirmar regeneración' }),
    )
    expect(await screen.findByText('NUEVO99999')).toBeInTheDocument()
  })

  it('PR-RNF03-01 (ADR-06): muestra "Proyecto no encontrado" cuando el usuario no es miembro (404)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn('/proyectos/999')
    expect(
      await screen.findByRole('heading', { name: 'Proyecto no encontrado' }),
    ).toBeInTheDocument()
  })
})

describe('Métricas por sprint en el frontend (RF-07, HU-06, Lámina 07)', () => {
  it('PR-RF07-01 y 05: captura métricas distinguiendo vacío (null) de 0 y actualiza la tabla', async () => {
    let cuerpoEnviado = null
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, opciones) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/`) {
        return Promise.resolve(respuestaJson(PROYECTO_ADMIN, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/metrics/`) {
        if (opciones?.method === 'POST') {
          cuerpoEnviado = JSON.parse(opciones.body)
          return Promise.resolve(
            respuestaJson(
              {
                sprint: 1,
                defectos_encontrados: 0,
                defectos_corregidos: 5,
                horas_correccion: 10,
                kloc: 1.5,
                cobertura_pct: null,
              },
              201,
            ),
          )
        }
        return Promise.resolve(respuestaJson([], 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn(`/proyectos/${PROYECTO_ADMIN.id}/metricas`)
    const inputSprint = await screen.findByLabelText('Sprint *')
    expect(inputSprint).toHaveValue(1)

    fireEvent.change(screen.getByLabelText('Def. encontrados'), {
      target: { value: '0' },
    })
    fireEvent.change(screen.getByLabelText('Def. corregidos'), {
      target: { value: '5' },
    })
    fireEvent.change(screen.getByLabelText('Horas de corrección'), {
      target: { value: '10' },
    })
    fireEvent.change(screen.getByLabelText('KLOC (total)'), {
      target: { value: '1.5' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(cuerpoEnviado).toEqual({
        sprint: 1,
        defectos_encontrados: 0,
        defectos_corregidos: 5,
        horas_correccion: 10,
        kloc: 1.5,
        cobertura_pct: null,
      })
    })
    expect(await screen.findByText('Sprint 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Sprint *')).toHaveValue(2)
  })

  it('PR-RF07-02 a 04: valida rangos y muestra error cuando el sprint está repetido (409)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, opciones) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/`) {
        return Promise.resolve(respuestaJson(PROYECTO_ADMIN, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/metrics/`) {
        if (opciones?.method === 'POST') {
          return Promise.resolve(
            respuestaJson(
              {
                sprint: [
                  'El sprint 1 ya tiene métricas registradas; usa Editar.',
                ],
              },
              409,
            ),
          )
        }
        return Promise.resolve(respuestaJson([], 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn(`/proyectos/${PROYECTO_ADMIN.id}/metricas`)
    await screen.findByLabelText('Sprint *')

    // PR-RF07-03 y 04: cobertura > 100 y negativos
    fireEvent.change(screen.getByLabelText('Def. encontrados'), {
      target: { value: '-2' },
    })
    fireEvent.change(screen.getByLabelText('Cobertura (%)'), {
      target: { value: '120' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(
      await screen.findByText('El valor no puede ser negativo.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('La cobertura debe estar entre 0 y 100.'),
    ).toBeInTheDocument()

    // PR-RF07-02: sprint repetido (409)
    fireEvent.change(screen.getByLabelText('Def. encontrados'), {
      target: { value: '3' },
    })
    fireEvent.change(screen.getByLabelText('Cobertura (%)'), {
      target: { value: '80' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(
      await screen.findByText(
        'El sprint 1 ya tiene métricas registradas; usa Editar.',
      ),
    ).toBeInTheDocument()
  })

  it('PR-RF05-01: oculta el formulario de captura de métricas para el Auditor', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/`) {
        return Promise.resolve(
          respuestaJson({ ...PROYECTO_ADMIN, mi_clase: 'AUDITOR' }, 200),
        )
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/metrics/`) {
        return Promise.resolve(respuestaJson([], 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn(`/proyectos/${PROYECTO_ADMIN.id}/metricas`)
    expect(
      await screen.findByRole('heading', { name: 'Métricas por sprint' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Capturar sprint' }),
    ).not.toBeInTheDocument()
  })
})

describe('Actividades SQA en el frontend (RF-08, HU-04, HU-05, Láminas 08 a 08c)', () => {
  const ACTIVIDAD_REALIZADA = {
    id: 101,
    sprint: 3,
    tipo: 'PRUEBAS',
    nombre_otra: '',
    nombre: 'Pruebas',
    estado: 'REALIZADA',
    resultado: 'CON_HALLAZGOS',
    fecha: '2026-09-15',
    responsable: USUARIO_SESION,
    descripcion: 'Pruebas de integración de la API',
    hallazgos: 'Dos rutas sin validación',
    evidencia_url: 'https://github.com/ejemplo/evidencia',
  }

  it('PR-RF08-01 a 03: valida campos condicionales (Otra y Realizada) y registra actividad', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, opciones) => {
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/`) {
        return Promise.resolve(respuestaJson(PROYECTO_ADMIN, 200))
      }
      if (url.startsWith(`/api/projects/${PROYECTO_ADMIN.id}/activities/`)) {
        if (opciones?.method === 'POST') {
          return Promise.resolve(respuestaJson(ACTIVIDAD_REALIZADA, 201))
        }
        return Promise.resolve(respuestaJson([], 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn(`/proyectos/${PROYECTO_ADMIN.id}/actividades`)
    fireEvent.click(
      await screen.findByRole('button', { name: 'Registrar actividad' }),
    )

    // En estado Planeada, Resultado está oculto (Lámina 08c)
    expect(
      screen.queryByRole('group', { name: 'Resultado *' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByLabelText('Nombre de la actividad *'),
    ).not.toBeInTheDocument()

    // PR-RF08-03: elegir "Otra" exige nombre
    fireEvent.change(screen.getByLabelText('Tipo *'), {
      target: { value: 'OTRA' },
    })
    expect(
      screen.getByLabelText('Nombre de la actividad *'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(
      await screen.findByText(
        'Escribe el nombre de la actividad cuando el tipo es Otra.',
      ),
    ).toBeInTheDocument()

    // PR-RF08-01: elegir "Realizada" exige resultado
    fireEvent.change(screen.getByLabelText('Tipo *'), {
      target: { value: 'PRUEBAS' },
    })
    fireEvent.click(screen.getByLabelText('Realizada'))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(
      await screen.findByText('Una actividad Realizada necesita un resultado.'),
    ).toBeInTheDocument()

    // Selecciona resultado y guarda
    fireEvent.click(screen.getByLabelText('Con hallazgos'))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findAllByText('Pruebas')).not.toHaveLength(0)
  })

  it('PR-RF08-05 y detalle: filtra por sprint y estado, abre el detalle con "Ver" y oculta captura al Auditor', async () => {
    const urlsConsultadas = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      urlsConsultadas.push(url)
      if (url === '/api/auth/me/') {
        return Promise.resolve(respuestaJson(USUARIO_SESION, 200))
      }
      if (url === `/api/projects/${PROYECTO_ADMIN.id}/`) {
        return Promise.resolve(
          respuestaJson({ ...PROYECTO_ADMIN, mi_clase: 'AUDITOR' }, 200),
        )
      }
      if (url.startsWith(`/api/projects/${PROYECTO_ADMIN.id}/activities/`)) {
        return Promise.resolve(respuestaJson([ACTIVIDAD_REALIZADA], 200))
      }
      return Promise.resolve(respuestaVacia(404))
    })

    renderEn(`/proyectos/${PROYECTO_ADMIN.id}/actividades`)
    expect(await screen.findAllByText('Pruebas')).not.toHaveLength(0)
    // Lámina 08b: el Auditor no ve el botón "Registrar actividad"
    expect(
      screen.queryByRole('button', { name: 'Registrar actividad' }),
    ).not.toBeInTheDocument()

    // Abrir detalle con "Ver" (Lámina 08)
    fireEvent.click(screen.getAllByRole('button', { name: 'Ver' })[0])
    expect(
      await screen.findByText('Pruebas de integración de la API'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', {
        name: 'https://github.com/ejemplo/evidencia',
      }),
    ).toBeInTheDocument()

    // PR-RF08-05: filtrar por estado
    fireEvent.change(screen.getByLabelText('Estado'), {
      target: { value: 'REALIZADA' },
    })
    await waitFor(() => {
      expect(
        urlsConsultadas.some((u) => u.includes('estado=REALIZADA')),
      ).toBe(true)
    })
  })
})


