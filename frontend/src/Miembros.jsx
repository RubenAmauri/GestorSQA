import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from './api.js'

const ETIQUETA_CLASE = {
  ADMIN_CREADOR: 'Admin Creador',
  ADMIN_NORMAL: 'Admin Normal',
  COLABORADOR: 'Colaborador',
  AUDITOR: 'Auditor',
}

const CLASES_ASIGNABLES = [
  { valor: 'ADMIN_NORMAL', etiqueta: 'Admin Normal' },
  { valor: 'COLABORADOR', etiqueta: 'Colaborador' },
  { valor: 'AUDITOR', etiqueta: 'Auditor' },
]

function esClaseAdmin(clase) {
  return clase === 'ADMIN_CREADOR' || clase === 'ADMIN_NORMAL'
}

function etiquetaClase(clase) {
  return ETIQUETA_CLASE[clase] || clase
}

function extraerMensajeError(data, porDefecto) {
  if (data?.detail) return data.detail
  if (Array.isArray(data?.clase) && data.clase.length > 0) return data.clase[0]
  return porDefecto
}

export function SeccionMiembros({ proyecto, usuario }) {
  const [miembros, setMiembros] = useState([])
  const [cargando, setCargando] = useState(true)
  const [errorCarga, setErrorCarga] = useState('')
  const [errorAccion, setErrorAccion] = useState('')
  const [procesandoId, setProcesandoId] = useState(null)
  const [miembroAExpulsar, setMiembroAExpulsar] = useState(null)
  const [expulsando, setExpulsando] = useState(false)

  const esAdmin = esClaseAdmin(proyecto.mi_clase)

  useEffect(() => {
    let activo = true
    setCargando(true)
    setErrorCarga('')
    apiFetch(`projects/${proyecto.id}/members/`)
      .then(({ ok, data }) => {
        if (!activo) return
        if (ok && Array.isArray(data)) {
          setMiembros(data)
        } else {
          setErrorCarga(extraerMensajeError(data, 'No se pudieron cargar los miembros.'))
        }
        setCargando(false)
      })
      .catch(() => {
        if (!activo) return
        setErrorCarga('No se pudo conectar con el servidor.')
        setCargando(false)
      })
    return () => {
      activo = false
    }
  }, [proyecto.id])

  function puedeGestionarMiembro(miembro) {
    if (!esAdmin) return false
    if (miembro.clase === 'ADMIN_CREADOR') return false
    if (usuario?.id && miembro.usuario_id === usuario.id) return false
    return true
  }

  async function cambiarClaseMiembro(miembro, nuevaClase) {
    setErrorAccion('')
    setProcesandoId(miembro.usuario_id)
    try {
      const { ok, data } = await apiFetch(
        `projects/${proyecto.id}/members/${miembro.usuario_id}/`,
        {
          method: 'PATCH',
          body: { clase: nuevaClase },
        },
      )
      if (ok && data) {
        setMiembros((actuales) =>
          actuales.map((m) => (m.usuario_id === miembro.usuario_id ? data : m)),
        )
        return
      }
      setErrorAccion(
        extraerMensajeError(data, 'No se pudo cambiar la clase del miembro.'),
      )
    } catch {
      setErrorAccion('No se pudo conectar con el servidor.')
    } finally {
      setProcesandoId(null)
    }
  }

  async function confirmarExpulsion() {
    if (!miembroAExpulsar) return
    setErrorAccion('')
    setExpulsando(true)
    try {
      const { ok, data } = await apiFetch(
        `projects/${proyecto.id}/members/${miembroAExpulsar.usuario_id}/`,
        { method: 'DELETE' },
      )
      if (ok) {
        setMiembros((actuales) =>
          actuales.filter((m) => m.usuario_id !== miembroAExpulsar.usuario_id),
        )
        setMiembroAExpulsar(null)
        return
      }
      setErrorAccion(extraerMensajeError(data, 'No se pudo expulsar al miembro.'))
    } catch {
      setErrorAccion('No se pudo conectar con el servidor.')
    } finally {
      setExpulsando(false)
    }
  }

  function renderizarCeldaClase(miembro, sufijoId = '') {
    if (!puedeGestionarMiembro(miembro)) {
      return <span className="capsula-clase">{etiquetaClase(miembro.clase)}</span>
    }
    return (
      <select
        id={`clase-miembro-${miembro.usuario_id}${sufijoId}`}
        aria-label={`Clase de ${miembro.correo}`}
        value={miembro.clase}
        disabled={procesandoId === miembro.usuario_id}
        onChange={(e) => cambiarClaseMiembro(miembro, e.target.value)}
      >
        {CLASES_ASIGNABLES.map((opcion) => (
          <option key={opcion.valor} value={opcion.valor}>
            {opcion.etiqueta}
          </option>
        ))}
      </select>
    )
  }

  function renderizarAccionMiembro(miembro) {
    if (miembro.clase === 'ADMIN_CREADOR') {
      return <span>Protegido</span>
    }
    if (usuario?.id && miembro.usuario_id === usuario.id) {
      return <span>No puedes modificarte</span>
    }
    return (
      <button
        type="button"
        className="boton-destructivo"
        aria-label={`Expulsar a ${miembro.correo}`}
        onClick={() => {
          setErrorAccion('')
          setMiembroAExpulsar(miembro)
        }}
      >
        Expulsar
      </button>
    )
  }

  return (
    <section>
      <div className="encabezado-seccion">
        <h2>Miembros del proyecto ({miembros.length})</h2>
        {esAdmin && (
          <p className="nota-pie">
            Para invitar, comparte el código de{' '}
            <Link to={`/proyectos/${proyecto.id}/configuracion`}>Configuración</Link>.
          </p>
        )}
      </div>

      {cargando && <p role="status">Cargando miembros...</p>}
      {errorCarga && (
        <div className="alerta-error" role="alert">
          {errorCarga}
        </div>
      )}
      {errorAccion && (
        <div className="alerta-error" role="alert">
          {errorAccion}
        </div>
      )}

      {miembroAExpulsar && (
        <div
          className="cuadro-confirmacion"
          role="region"
          aria-label="Confirmar expulsión"
        >
          <p>
            <strong>¿Expulsar a {miembroAExpulsar.correo}?</strong>
          </p>
          <p>Perderá el acceso al proyecto. Sus registros se conservan.</p>
          <div className="acciones-formulario">
            <button
              type="button"
              className="boton-destructivo boton-ajustado"
              disabled={expulsando}
              onClick={confirmarExpulsion}
            >
              Confirmar expulsión
            </button>
            <button
              type="button"
              className="boton-secundario"
              disabled={expulsando}
              onClick={() => setMiembroAExpulsar(null)}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {!cargando && !errorCarga && miembros.length > 0 && (
        <>
          <table className="tabla-datos solo-tabla-escritorio">
            <thead>
              <tr>
                <th>Miembro</th>
                <th>Clase</th>
                {esAdmin && <th>Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {miembros.map((m) => {
                const esPropio = Boolean(usuario?.id && m.usuario_id === usuario.id)
                return (
                  <tr key={m.usuario_id}>
                    <td className="celda-fuerte">
                      {m.correo}
                      {esPropio ? ' (tú)' : ''}
                    </td>
                    <td>{renderizarCeldaClase(m)}</td>
                    {esAdmin && <td>{renderizarAccionMiembro(m)}</td>}
                  </tr>
                )
              })}
            </tbody>
          </table>

          <div className="lista-tarjetas-movil">
            {miembros.map((m) => {
              const esPropio = Boolean(usuario?.id && m.usuario_id === usuario.id)
              const gestionable = puedeGestionarMiembro(m)
              return (
                <article key={m.usuario_id} className="tarjeta-item">
                  <div className="tarjeta-item-cabecera">
                    <strong>
                      {m.correo}
                      {esPropio ? ' (tú)' : ''}
                    </strong>
                    {!gestionable && (
                      <span className="capsula-clase">{etiquetaClase(m.clase)}</span>
                    )}
                  </div>
                  {gestionable ? (
                    <>
                      <div className="campo-formulario">
                        <label htmlFor={`clase-miembro-${m.usuario_id}-movil`}>
                          Clase
                        </label>
                        {renderizarCeldaClase(m, '-movil')}
                      </div>
                      {renderizarAccionMiembro(m)}
                    </>
                  ) : (
                    esAdmin && (
                      <p className="tarjeta-item-sub">{renderizarAccionMiembro(m)}</p>
                    )
                  )}
                </article>
              )
            })}
          </div>
        </>
      )}
    </section>
  )
}
