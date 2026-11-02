import { useEffect, useState } from 'react'
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom'
import { apiFetch } from './api.js'

const ETIQUETA_CLASE = {
  ADMIN_CREADOR: 'Admin Creador',
  ADMIN_NORMAL: 'Admin Normal',
  COLABORADOR: 'Colaborador',
  AUDITOR: 'Auditor',
}

function etiquetaClase(clase, conDetalleAuditor = false) {
  if (clase === 'AUDITOR' && conDetalleAuditor) {
    return 'Auditor (solo lectura)'
  }
  return ETIQUETA_CLASE[clase] || clase
}

function esClaseAdmin(clase) {
  return clase === 'ADMIN_CREADOR' || clase === 'ADMIN_NORMAL'
}

function formatearFecha(iso) {
  if (!iso || typeof iso !== 'string') return ''
  const partes = iso.split('-')
  if (partes.length !== 3) return iso
  return `${partes[2]}/${partes[1]}/${partes[0]}`
}

/* --- Lámina 03: Mis proyectos (/proyectos) --- */

export function MisProyectos() {
  const [proyectos, setProyectos] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let activo = true
    apiFetch('projects/')
      .then(({ ok, data }) => {
        if (!activo) return
        if (ok && Array.isArray(data)) {
          setProyectos(data)
        } else {
          setError('No se pudieron cargar los proyectos.')
        }
        setCargando(false)
      })
      .catch(() => {
        if (!activo) return
        setError('No se pudo conectar con el servidor.')
        setCargando(false)
      })
    return () => {
      activo = false
    }
  }, [])

  return (
    <section>
      <div className="encabezado-seccion">
        <h1>Mis proyectos</h1>
        <div className="acciones-encabezado">
          <Link to="/proyectos/unirse" className="boton-enlace-secundario">
            Unirme con código
          </Link>
          <Link to="/proyectos/nuevo" className="boton-enlace-primario">
            Registrar proyecto
          </Link>
        </div>
      </div>

      {cargando && <p role="status">Cargando proyectos...</p>}
      {error && (
        <div className="alerta-error" role="alert">
          {error}
        </div>
      )}

      {!cargando && !error && proyectos.length === 0 && (
        <p className="mensaje-vacio">
          Aún no perteneces a ningún proyecto. Registra uno nuevo o únete con un código.
        </p>
      )}

      {!cargando && !error && proyectos.length > 0 && (
        <>
          <table className="tabla-datos solo-tabla-escritorio">
            <thead>
              <tr>
                <th>Proyecto</th>
                <th>Periodo</th>
                <th>Mi clase</th>
                <th>
                  <span className="oculto-visualmente">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {proyectos.map((p) => (
                <tr key={p.id}>
                  <td className="celda-fuerte">{p.nombre}</td>
                  <td>{p.periodo_nombre}</td>
                  <td>
                    <span className="capsula-clase">{etiquetaClase(p.mi_clase)}</span>
                  </td>
                  <td className="celda-accion">
                    <Link to={`/proyectos/${p.id}`}>Abrir</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="lista-tarjetas-movil">
            {proyectos.map((p) => (
              <article key={p.id} className="tarjeta-item">
                <div className="tarjeta-item-cabecera">
                  <strong>{p.nombre}</strong>
                  <Link to={`/proyectos/${p.id}`}>Abrir</Link>
                </div>
                <p className="tarjeta-item-sub">Periodo {p.periodo_nombre}</p>
                <span className="capsula-clase">{etiquetaClase(p.mi_clase)}</span>
              </article>
            ))}
          </div>
        </>
      )}

      <p className="nota-pie">Solo se listan los proyectos donde eres miembro.</p>
    </section>
  )
}

/* --- Láminas 04 y 04b: Registrar proyecto (/proyectos/nuevo) --- */

export function NuevoProyecto() {
  const navigate = useNavigate()
  const [nombre, setNombre] = useState('')
  const [periodoNombre, setPeriodoNombre] = useState('')
  const [fechaInicio, setFechaInicio] = useState('')
  const [fechaFin, setFechaFin] = useState('')
  const [errores, setErrores] = useState({})
  const [enviando, setEnviando] = useState(false)

  async function manejarEnvio(evento) {
    evento.preventDefault()
    const validacion = validarProyecto({
      nombre,
      periodoNombre,
      fechaInicio,
      fechaFin,
    })
    if (Object.keys(validacion).length > 0) {
      setErrores(validacion)
      return
    }

    setErrores({})
    setEnviando(true)
    try {
      const { ok, status, data } = await apiFetch('projects/', {
        method: 'POST',
        body: {
          nombre,
          periodo_nombre: periodoNombre,
          fecha_inicio: fechaInicio,
          fecha_fin: fechaFin,
        },
      })

      if (ok && data?.id) {
        // Flujo de RNF-04 (SDS 3.5): al crear el proyecto pasa a /proyectos/:id/metricas.
        navigate(`/proyectos/${data.id}/metricas`, { replace: true })
        return
      }

      if (status === 409) {
        setErrores({
          general:
            'Ya registraste un proyecto con este nombre en este periodo. Cambia el nombre o el periodo.',
          nombre: `Nombre repetido en el periodo ${periodoNombre.trim()}.`,
        })
        return
      }

      setErrores(extraerErroresProyecto(data))
    } catch {
      setErrores({ general: 'No se pudo conectar con el servidor.' })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="contenedor-formulario">
      <p className="migas-pan">
        <Link to="/proyectos">Mis proyectos</Link> / Registrar proyecto
      </p>
      <h1>Registrar proyecto</h1>

      {errores.general && (
        <div className="alerta-error" role="alert">
          {errores.general}
        </div>
      )}

      <form onSubmit={manejarEnvio} noValidate>
        <div className="campo-formulario">
          <label htmlFor="proyecto-nombre">Nombre del proyecto *</label>
          <input
            id="proyecto-nombre"
            type="text"
            maxLength={100}
            placeholder="[Nombre del proyecto]"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            aria-invalid={Boolean(errores.nombre)}
            required
          />
          {errores.nombre && (
            <p className="error-campo" role="alert">
              {errores.nombre}
            </p>
          )}
        </div>

        <div className="campo-formulario">
          <label htmlFor="proyecto-periodo">Nombre del periodo *</label>
          <input
            id="proyecto-periodo"
            type="text"
            maxLength={50}
            placeholder="p. ej. 2026-2"
            value={periodoNombre}
            onChange={(e) => setPeriodoNombre(e.target.value)}
            aria-invalid={Boolean(errores.periodo_nombre)}
            required
          />
          {errores.periodo_nombre && (
            <p className="error-campo" role="alert">
              {errores.periodo_nombre}
            </p>
          )}
        </div>

        <div className="fila-dos-columnas">
          <div className="campo-formulario">
            <label htmlFor="proyecto-fecha-inicio">Fecha de inicio *</label>
            <input
              id="proyecto-fecha-inicio"
              type="date"
              value={fechaInicio}
              onChange={(e) => setFechaInicio(e.target.value)}
              aria-invalid={Boolean(errores.fecha_inicio)}
              required
            />
            {errores.fecha_inicio && (
              <p className="error-campo" role="alert">
                {errores.fecha_inicio}
              </p>
            )}
          </div>

          <div className="campo-formulario">
            <label htmlFor="proyecto-fecha-fin">Fecha de fin *</label>
            <input
              id="proyecto-fecha-fin"
              type="date"
              value={fechaFin}
              onChange={(e) => setFechaFin(e.target.value)}
              aria-invalid={Boolean(errores.fecha_fin)}
              required
            />
            <p className="texto-ayuda">No puede ser anterior a la fecha de inicio.</p>
            {errores.fecha_fin && (
              <p className="error-campo" role="alert">
                {errores.fecha_fin}
              </p>
            )}
          </div>
        </div>

        <p className="texto-obligatorio">* Obligatorio</p>

        <div className="acciones-formulario">
          <button type="submit" className="boton-primario boton-ajustado" disabled={enviando}>
            Registrar proyecto
          </button>
          <Link to="/proyectos" className="enlace-cancelar">
            Cancelar
          </Link>
        </div>
      </form>
    </section>
  )
}

function validarProyecto({ nombre, periodoNombre, fechaInicio, fechaFin }) {
  const errores = {}
  if (!nombre.trim()) {
    errores.nombre = 'El nombre del proyecto es obligatorio.'
  }
  if (!periodoNombre.trim()) {
    errores.periodo_nombre = 'El nombre del periodo es obligatorio.'
  }
  if (!fechaInicio) {
    errores.fecha_inicio = 'La fecha de inicio es obligatoria.'
  }
  if (!fechaFin) {
    errores.fecha_fin = 'La fecha de fin es obligatoria.'
  } else if (fechaInicio && fechaFin < fechaInicio) {
    errores.fecha_fin = 'La fecha de fin no puede ser anterior a la fecha de inicio.'
  }
  return errores
}

function extraerErroresProyecto(data) {
  if (!data) return { general: 'No se pudo registrar el proyecto.' }
  const errores = {}
  for (const campo of ['nombre', 'periodo_nombre', 'fecha_inicio', 'fecha_fin']) {
    if (Array.isArray(data[campo]) && data[campo].length > 0) {
      errores[campo] = data[campo][0]
    }
  }
  if (data.detail) {
    errores.general = data.detail
  }
  if (Object.keys(errores).length === 0) {
    errores.general = 'Verifica los datos del proyecto.'
  }
  return errores
}

/* --- Lámina 05: Unirse a un proyecto (/proyectos/unirse) --- */

export function UnirseProyecto() {
  const navigate = useNavigate()
  const [codigo, setCodigo] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function manejarEnvio(evento) {
    evento.preventDefault()
    setError('')

    if (!codigo.trim()) {
      setError('El código no es válido.')
      return
    }

    setEnviando(true)
    try {
      const { ok, status, data } = await apiFetch('projects/join/', {
        method: 'POST',
        body: { codigo },
      })

      if (ok && data?.id) {
        // SDS 3.5: al unirse con código, va al reporte del proyecto.
        navigate(`/proyectos/${data.id}`, { replace: true })
        return
      }

      if (status === 429) {
        setError('Demasiados intentos. Vuelve a intentarlo más tarde.')
      } else if (status === 409) {
        setError(data?.detail || 'Ya eres miembro de este proyecto.')
      } else {
        setError(data?.detail || 'El código no es válido.')
      }
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="contenedor-formulario">
      <p className="migas-pan">
        <Link to="/proyectos">Mis proyectos</Link> / Unirse con código
      </p>
      <h1>Unirse a un proyecto</h1>

      <form onSubmit={manejarEnvio} noValidate>
        <div className="campo-formulario">
          <label htmlFor="codigo-union">Código del proyecto</label>
          <input
            id="codigo-union"
            type="text"
            maxLength={32}
            placeholder="10 caracteres, p. ej. XXXXXXXXXX"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            required
          />
        </div>

        <p className="nota-formulario">
          Te unirás como Colaborador. Un Admin del proyecto puede cambiar tu clase.
        </p>

        {error && (
          <div className="alerta-error" role="alert">
            {error}
          </div>
        )}

        <div className="acciones-formulario">
          <button type="submit" className="boton-primario boton-ajustado" disabled={enviando}>
            Unirse
          </button>
          <Link to="/proyectos" className="enlace-cancelar">
            Cancelar
          </Link>
        </div>
      </form>
    </section>
  )
}

/* --- Marco de un proyecto (/proyectos/:id/*) y Configuración (Lámina 10) --- */

export function VistaProyecto({
  SeccionReporte,
  SeccionMetricas,
  SeccionActividades,
  SeccionMiembros,
}) {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [proyecto, setProyecto] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [noEncontrado, setNoEncontrado] = useState(false)

  useEffect(() => {
    let activo = true
    setCargando(true)
    setNoEncontrado(false)
    apiFetch(`projects/${id}/`)
      .then(({ ok, data }) => {
        if (!activo) return
        if (ok && data) {
          setProyecto(data)
        } else {
          setNoEncontrado(true)
        }
        setCargando(false)
      })
      .catch(() => {
        if (!activo) return
        setNoEncontrado(true)
        setCargando(false)
      })
    return () => {
      activo = false
    }
  }, [id])

  if (cargando) {
    return <p role="status">Cargando proyecto...</p>
  }

  if (noEncontrado || !proyecto) {
    // SDS 3.5 y ADR-06: quien no es miembro o busca un id inexistente ve el mismo mensaje.
    return (
      <section>
        <h1>Proyecto no encontrado</h1>
        <Link to="/proyectos">Volver a Mis proyectos</Link>
      </section>
    )
  }

  const esAdmin = esClaseAdmin(proyecto.mi_clase)
  const base = `/proyectos/${proyecto.id}`
  const secciones = [
    { ruta: base, etiqueta: 'Reporte' },
    { ruta: `${base}/metricas`, etiqueta: 'Métricas' },
    { ruta: `${base}/actividades`, etiqueta: 'Actividades' },
    { ruta: `${base}/miembros`, etiqueta: 'Miembros' },
    ...(esAdmin ? [{ ruta: `${base}/configuracion`, etiqueta: 'Configuración' }] : []),
  ]

  const rutaActual =
    secciones.find((s) => s.ruta === location.pathname)?.ruta || base

  return (
    <section>
      <header className="encabezado-proyecto">
        <p className="migas-pan">
          <Link to="/proyectos">Mis proyectos</Link> / {proyecto.nombre}
        </p>
        <div className="titulo-proyecto-fila">
          <h1>{proyecto.nombre}</h1>
          <span className="capsula-clase">
            Tu clase: {etiquetaClase(proyecto.mi_clase, true)}
          </span>
        </div>
        <p className="subtitulo-proyecto">
          Periodo {proyecto.periodo_nombre} · {formatearFecha(proyecto.fecha_inicio)} –{' '}
          {formatearFecha(proyecto.fecha_fin)}
        </p>

        <nav className="pestanas-proyecto" aria-label="Secciones del proyecto">
          {secciones.map((s) => (
            <Link
              key={s.ruta}
              to={s.ruta}
              className={
                rutaActual === s.ruta ? 'pestana-item pestana-activa' : 'pestana-item'
              }
            >
              {s.etiqueta}
            </Link>
          ))}
        </nav>

        <div className="selector-seccion-movil">
          <label htmlFor="selector-seccion">Sección</label>
          <select
            id="selector-seccion"
            value={rutaActual}
            onChange={(e) => navigate(e.target.value)}
          >
            {secciones.map((s) => (
              <option key={s.ruta} value={s.ruta}>
                {s.etiqueta}
              </option>
            ))}
          </select>
        </div>
      </header>

      <Routes>
        <Route
          index
          element={
            SeccionReporte ? (
              <SeccionReporte proyecto={proyecto} />
            ) : (
              <SeccionPendiente titulo="Reporte de salud" />
            )
          }
        />
        <Route
          path="metricas"
          element={
            SeccionMetricas ? (
              <SeccionMetricas proyecto={proyecto} />
            ) : (
              <SeccionPendiente titulo="Métricas por sprint" />
            )
          }
        />
        <Route
          path="actividades"
          element={
            SeccionActividades ? (
              <SeccionActividades proyecto={proyecto} />
            ) : (
              <SeccionPendiente titulo="Actividades SQA" />
            )
          }
        />
        <Route
          path="miembros"
          element={
            SeccionMiembros ? (
              <SeccionMiembros proyecto={proyecto} />
            ) : (
              <SeccionPendiente titulo="Miembros del proyecto" />
            )
          }
        />
        <Route
          path="configuracion"
          element={
            esAdmin ? (
              <ConfiguracionProyecto
                proyecto={proyecto}
                alActualizarProyecto={setProyecto}
              />
            ) : (
              <Navigate to={base} replace />
            )
          }
        />
      </Routes>
    </section>
  )
}

function SeccionPendiente({ titulo }) {
  return (
    <section>
      <h2>{titulo}</h2>
    </section>
  )
}

function ConfiguracionProyecto({ proyecto, alActualizarProyecto }) {
  const [confirmando, setConfirmando] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const [regenerando, setRegenerando] = useState(false)
  const [error, setError] = useState('')

  async function copiarCodigo() {
    if (navigator.clipboard?.writeText && proyecto.codigo_union) {
      await navigator.clipboard.writeText(proyecto.codigo_union)
      setCopiado(true)
    }
  }

  async function confirmarRegeneracion() {
    setRegenerando(true)
    setError('')
    try {
      const { ok, data } = await apiFetch(
        `projects/${proyecto.id}/codigo/regenerar/`,
        { method: 'POST' },
      )
      if (ok && data?.codigo_union) {
        alActualizarProyecto({ ...proyecto, codigo_union: data.codigo_union })
        setConfirmando(false)
        setCopiado(false)
      } else {
        setError('No se pudo regenerar el código.')
      }
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setRegenerando(false)
    }
  }

  return (
    <div className="rejilla-configuracion">
      <section className="tarjeta-panel">
        <h2>Código de unión</h2>
        <p className="texto-ayuda">
          Compártelo con quien deba unirse; entrará como Colaborador.
        </p>

        <div className="fila-codigo-union">
          <output className="recuadro-codigo" aria-label="Código de unión actual">
            {proyecto.codigo_union}
          </output>
          <button type="button" className="boton-secundario" onClick={copiarCodigo}>
            {copiado ? 'Copiado' : 'Copiar'}
          </button>
        </div>

        {!confirmando ? (
          <button
            type="button"
            className="boton-secundario"
            onClick={() => setConfirmando(true)}
          >
            Regenerar código
          </button>
        ) : (
          <div className="cuadro-confirmacion" role="region" aria-label="Confirmar regeneración">
            <p>
              <strong>¿Regenerar el código de unión?</strong> El código anterior dejará de
              funcionar inmediatamente.
            </p>
            <div className="acciones-formulario">
              <button
                type="button"
                className="boton-primario boton-ajustado"
                disabled={regenerando}
                onClick={confirmarRegeneracion}
              >
                Confirmar regeneración
              </button>
              <button
                type="button"
                className="boton-secundario"
                onClick={() => setConfirmando(false)}
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        <p className="texto-ayuda">
          Al regenerarlo, el código anterior deja de funcionar. Se pide confirmación.
        </p>

        {error && (
          <div className="alerta-error" role="alert">
            {error}
          </div>
        )}
      </section>
    </div>
  )
}
