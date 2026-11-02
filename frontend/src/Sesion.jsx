import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiFetch } from './api.js'

const MENSAJE_CREDENCIALES = 'Correo o contraseña incorrectos.'
const MENSAJE_LIMITE_INTENTOS =
  'Demasiados intentos. Espera un momento y vuelve a intentarlo.'
const MENSAJE_CORREO_INVALIDO = 'Ingresa un correo electrónico válido.'
const MENSAJE_CONTRASENA_CORTA = 'La contraseña debe tener al menos 8 caracteres.'
const MENSAJE_SIN_CONEXION = 'No se pudo conectar con el servidor.'

export function BarraSuperior({ usuario, alCerrarSesion }) {
  const [menuAbierto, setMenuAbierto] = useState(false)

  async function manejarCierre() {
    setMenuAbierto(false)
    await alCerrarSesion()
  }

  return (
    <header className="barra-superior">
      <div className="barra-superior-interior">
        <div className="barra-izquierda">
          {usuario && (
            <button
              type="button"
              className="boton-menu-movil"
              aria-label="Menú"
              aria-expanded={menuAbierto}
              onClick={() => setMenuAbierto((actual) => !actual)}
            >
              ☰
            </button>
          )}
          <span className="logo-marca" aria-hidden="true">
            LOGO
          </span>
          <span className="nombre-marca">Gestor SQA</span>
          {usuario && (
            <Link to="/proyectos" className="enlace-barra solo-escritorio">
              Mis proyectos
            </Link>
          )}
        </div>

        {usuario && (
          <div className="barra-derecha solo-escritorio">
            <span className="correo-usuario">{usuario.email}</span>
            <button type="button" className="boton-secundario" onClick={manejarCierre}>
              Cerrar sesión
            </button>
          </div>
        )}
      </div>

      {usuario && menuAbierto && (
        <nav className="menu-movil" aria-label="Menú principal">
          <span className="correo-usuario">{usuario.email}</span>
          <Link
            to="/proyectos"
            className="enlace-barra"
            onClick={() => setMenuAbierto(false)}
          >
            Mis proyectos
          </Link>
          <button type="button" className="boton-secundario" onClick={manejarCierre}>
            Cerrar sesión
          </button>
        </nav>
      )}
    </header>
  )
}

export function InicioSesion({ alAutenticar }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function manejarEnvio(evento) {
    evento.preventDefault()
    setError('')

    if (!email.trim() || !password) {
      setError(MENSAJE_CREDENCIALES)
      return
    }

    setEnviando(true)
    try {
      const { ok, status, data } = await apiFetch('auth/login/', {
        method: 'POST',
        body: { email, password },
      })

      if (ok) {
        alAutenticar(data)
        const destino = await resolverDestinoInicial()
        navigate(destino, { replace: true })
        return
      }

      if (status === 429) {
        setError(MENSAJE_LIMITE_INTENTOS)
      } else {
        setError(data?.detail || MENSAJE_CREDENCIALES)
      }
    } catch {
      setError(MENSAJE_SIN_CONEXION)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="contenedor-sesion">
      <div className="tarjeta-sesion">
        <h1>Iniciar sesión</h1>
        <form onSubmit={manejarEnvio} noValidate>
          <div className="campo-formulario">
            <label htmlFor="login-correo">Correo</label>
            <input
              id="login-correo"
              type="email"
              placeholder="nombre@correo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="campo-formulario">
            <label htmlFor="login-password">Contraseña</label>
            <input
              id="login-password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div className="alerta-error" role="alert">
              {error}
            </div>
          )}

          <button type="submit" className="boton-primario" disabled={enviando}>
            Iniciar sesión
          </button>
        </form>

        <p className="pie-tarjeta">
          ¿No tienes cuenta? <Link to="/registro">Crear cuenta</Link>
        </p>
      </div>
    </section>
  )
}

export function Registro({ alAutenticar }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errores, setErrores] = useState({})
  const [enviando, setEnviando] = useState(false)

  async function manejarEnvio(evento) {
    evento.preventDefault()
    const nuevosErrores = validarFormularioRegistro(email, password)
    if (Object.keys(nuevosErrores).length > 0) {
      setErrores(nuevosErrores)
      return
    }

    setErrores({})
    setEnviando(true)
    try {
      const { ok, data } = await apiFetch('auth/register/', {
        method: 'POST',
        body: { email, password },
      })

      if (ok) {
        alAutenticar(data)
        // Flujo de RNF-04 (SDS 3.5): tras registrarse, va directo a /proyectos/nuevo.
        navigate('/proyectos/nuevo', { replace: true })
        return
      }

      setErrores(extraerErroresRegistro(data))
    } catch {
      setErrores({ general: MENSAJE_SIN_CONEXION })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="contenedor-sesion">
      <div className="tarjeta-sesion">
        <h1>Crear cuenta</h1>
        <form onSubmit={manejarEnvio} noValidate>
          <div className="campo-formulario">
            <label htmlFor="registro-correo">Correo</label>
            <input
              id="registro-correo"
              type="email"
              placeholder="nombre@correo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              aria-invalid={Boolean(errores.email)}
              required
            />
            {errores.email && (
              <p className="error-campo" role="alert">
                {errores.email}
              </p>
            )}
          </div>

          <div className="campo-formulario">
            <label htmlFor="registro-password">Contraseña</label>
            <input
              id="registro-password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              minLength={8}
              aria-invalid={Boolean(errores.password)}
              required
            />
            <p className="texto-ayuda">Mínimo 8 caracteres.</p>
            {errores.password && (
              <p className="error-campo" role="alert">
                {errores.password}
              </p>
            )}
          </div>

          {errores.general && (
            <div className="alerta-error" role="alert">
              {errores.general}
            </div>
          )}

          <button type="submit" className="boton-primario" disabled={enviando}>
            Crear cuenta
          </button>

          <p className="nota-formulario">La cuenta queda activa al instante.</p>
        </form>

        <p className="pie-tarjeta">
          ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
        </p>
      </div>
    </section>
  )
}

function validarFormularioRegistro(email, password) {
  const errores = {}
  const correoLimpio = email.trim()
  if (!correoLimpio || !correoLimpio.includes('@')) {
    errores.email = MENSAJE_CORREO_INVALIDO
  }
  if (!password || password.length < 8) {
    errores.password = MENSAJE_CONTRASENA_CORTA
  }
  return errores
}

function extraerErroresRegistro(data) {
  if (!data) return { general: 'No se pudo crear la cuenta.' }
  const errores = {}
  if (Array.isArray(data.email) && data.email.length > 0) {
    errores.email = data.email[0]
  }
  if (Array.isArray(data.password) && data.password.length > 0) {
    errores.password = data.password[0]
  }
  if (data.detail) {
    errores.general = data.detail
  }
  if (Object.keys(errores).length === 0) {
    errores.general = 'Verifica los datos capturados.'
  }
  return errores
}

async function resolverDestinoInicial() {
  try {
    const { ok, data } = await apiFetch('projects/')
    if (ok && Array.isArray(data) && data.length === 0) {
      return '/proyectos/nuevo'
    }
  } catch {
    // Si falla la consulta de proyectos, lleva al listado general.
  }
  return '/proyectos'
}
