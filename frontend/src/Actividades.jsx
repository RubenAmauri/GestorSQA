import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiFetch } from './api.js'

const TIPOS_ACTIVIDAD = [
  { valor: 'CAMINATA', etiqueta: 'Caminata' },
  { valor: 'REVISION_CODIGO', etiqueta: 'Revisión de código' },
  { valor: 'AUDITORIA_CONFIGURACION', etiqueta: 'Auditoría de configuración' },
  { valor: 'PRUEBAS', etiqueta: 'Pruebas' },
  { valor: 'OTRA', etiqueta: 'Otra' },
]

const ETIQUETA_ESTADO = {
  PLANEADA: 'Planeada',
  REALIZADA: 'Realizada',
}

const ETIQUETA_RESULTADO = {
  SATISFACTORIO: 'Satisfactorio',
  CON_HALLAZGOS: 'Con hallazgos',
  NO_SATISFACTORIO: 'No satisfactorio',
}

function puedeRegistrarActividad(clase) {
  return (
    clase === 'ADMIN_CREADOR' ||
    clase === 'ADMIN_NORMAL' ||
    clase === 'COLABORADOR'
  )
}

function formatearFecha(iso) {
  if (!iso || typeof iso !== 'string') return '—'
  const partes = iso.split('-')
  if (partes.length !== 3) return iso
  return `${partes[2]}/${partes[1]}/${partes[0]}`
}

function formatearTipoTabla(actividad) {
  if (actividad.tipo === 'OTRA') {
    const nombre = actividad.nombre_otra || actividad.nombre || ''
    return nombre ? `Otra: ${nombre}` : 'Otra'
  }
  return actividad.nombre || actividad.tipo
}

export function SeccionActividades({ proyecto, usuario }) {
  const [searchParams] = useSearchParams()
  const [actividades, setActividades] = useState([])
  const [sprintsConocidos, setSprintsConocidos] = useState([])
  const [responsables, setResponsables] = useState(() =>
    usuario ? [{ id: usuario.id, email: usuario.email }] : [],
  )
  const [filtroSprint, setFiltroSprint] = useState('')
  const [filtroEstado, setFiltroEstado] = useState('')
  const [cargando, setCargando] = useState(true)
  const [errorCarga, setErrorCarga] = useState('')

  const [actividadDetalle, setActividadDetalle] = useState(null)
  const [mostrarFormulario, setMostrarFormulario] = useState(
    () => searchParams.get('nueva') === '1',
  )

  const registroPermitido = puedeRegistrarActividad(proyecto.mi_clase)

  useEffect(() => {
    let activo = true
    setCargando(true)
    setErrorCarga('')

    const params = new URLSearchParams()
    if (filtroSprint) params.set('sprint', filtroSprint)
    if (filtroEstado) params.set('estado', filtroEstado)
    const sufijo = params.toString() ? `?${params.toString()}` : ''

    apiFetch(`projects/${proyecto.id}/activities/${sufijo}`)
      .then(({ ok, data }) => {
        if (!activo) return
        if (ok && Array.isArray(data)) {
          setActividades(data)
          actualizarCatalogosLocales(data, usuario, setSprintsConocidos, setResponsables)
        } else {
          setErrorCarga('No se pudieron cargar las actividades.')
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
  }, [proyecto.id, filtroSprint, filtroEstado, usuario])

  function alGuardarActividad(nueva) {
    const actualizadas = [...actividades, nueva]
    setActividades(actualizadas)
    actualizarCatalogosLocales(
      actualizadas,
      usuario,
      setSprintsConocidos,
      setResponsables,
    )
    setMostrarFormulario(false)
  }

  return (
    <section>
      <div className="barra-filtros-actividades">
        <div className="grupo-filtros">
          <div className="campo-filtro">
            <label htmlFor="filtro-sprint">Sprint</label>
            <select
              id="filtro-sprint"
              value={filtroSprint}
              onChange={(e) => setFiltroSprint(e.target.value)}
            >
              <option value="">Todos</option>
              {sprintsConocidos.map((s) => (
                <option key={s} value={String(s)}>
                  Sprint {s}
                </option>
              ))}
            </select>
          </div>

          <div className="campo-filtro">
            <label htmlFor="filtro-estado">Estado</label>
            <select
              id="filtro-estado"
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
            >
              <option value="">Todas</option>
              <option value="PLANEADA">Planeada</option>
              <option value="REALIZADA">Realizada</option>
            </select>
          </div>
        </div>

        {registroPermitido && !mostrarFormulario && (
          <button
            type="button"
            className="boton-primario boton-ajustado"
            onClick={() => setMostrarFormulario(true)}
          >
            Registrar actividad
          </button>
        )}
      </div>

      {registroPermitido && mostrarFormulario && (
        <FormularioActividad
          proyectoId={proyecto.id}
          responsables={responsables}
          usuarioActual={usuario}
          alGuardar={alGuardarActividad}
          alCancelar={() => setMostrarFormulario(false)}
        />
      )}

      {cargando && <p role="status">Cargando actividades...</p>}
      {errorCarga && (
        <div className="alerta-error" role="alert">
          {errorCarga}
        </div>
      )}

      {!cargando && !errorCarga && actividades.length === 0 && (
        <p className="mensaje-vacio">
          No hay actividades registradas con los criterios seleccionados.
        </p>
      )}

      {!cargando && !errorCarga && actividades.length > 0 && (
        <>
          <table className="tabla-datos solo-tabla-escritorio">
            <thead>
              <tr>
                <th>Sprint</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Responsable</th>
                <th>Resultado</th>
                <th>Fecha</th>
                <th>
                  <span className="oculto-visualmente">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {actividades.map((a) => (
                <tr key={a.id}>
                  <td className="celda-fuerte">{a.sprint}</td>
                  <td>{formatearTipoTabla(a)}</td>
                  <td>{ETIQUETA_ESTADO[a.estado] || a.estado}</td>
                  <td>{a.responsable?.email || '—'}</td>
                  <td>
                    {a.resultado ? ETIQUETA_RESULTADO[a.resultado] || a.resultado : '—'}
                  </td>
                  <td>{formatearFecha(a.fecha)}</td>
                  <td className="celda-accion">
                    <button
                      type="button"
                      className="boton-secundario"
                      onClick={() => setActividadDetalle(a)}
                    >
                      Ver
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="lista-tarjetas-movil">
            {actividades.map((a) => (
              <article key={a.id} className="tarjeta-item">
                <div className="tarjeta-item-cabecera">
                  <strong>{formatearTipoTabla(a)}</strong>
                  <span className="capsula-clase">
                    {ETIQUETA_ESTADO[a.estado] || a.estado}
                  </span>
                </div>
                <p className="tarjeta-item-sub">
                  Sprint {a.sprint} · {a.responsable?.email || '—'}
                  {a.resultado
                    ? ` · ${ETIQUETA_RESULTADO[a.resultado] || a.resultado}`
                    : ''}
                </p>
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => setActividadDetalle(a)}
                >
                  Ver
                </button>
              </article>
            ))}
          </div>
        </>
      )}

      {actividadDetalle && (
        <section
          className="tarjeta-panel panel-detalle-actividad"
          aria-label="Detalle de la actividad"
        >
          <h3>
            Detalle: {actividadDetalle.nombre || formatearTipoTabla(actividadDetalle)} · sprint{' '}
            {actividadDetalle.sprint}
          </h3>
          <p>
            <strong>Descripción:</strong> {actividadDetalle.descripcion || 'Sin descripción'}
          </p>
          <p>
            <strong>Hallazgos:</strong> {actividadDetalle.hallazgos || 'Sin hallazgos'}
          </p>
          <p>
            <strong>Evidencia:</strong>{' '}
            {actividadDetalle.evidencia_url ? (
              <a
                href={actividadDetalle.evidencia_url}
                target="_blank"
                rel="noreferrer"
              >
                {actividadDetalle.evidencia_url}
              </a>
            ) : (
              'Sin enlace de evidencia'
            )}
          </p>
        </section>
      )}
    </section>
  )
}

function FormularioActividad({
  proyectoId,
  responsables,
  usuarioActual,
  alGuardar,
  alCancelar,
}) {
  const [sprint, setSprint] = useState('1')
  const [fecha, setFecha] = useState('')
  const [tipo, setTipo] = useState('PRUEBAS')
  const [nombreOtra, setNombreOtra] = useState('')
  const [estado, setEstado] = useState('PLANEADA')
  const [resultado, setResultado] = useState('')
  const [responsable, setResponsable] = useState(() =>
    usuarioActual?.id ? String(usuarioActual.id) : String(responsables[0]?.id || ''),
  )
  const [descripcion, setDescripcion] = useState('')
  const [hallazgos, setHallazgos] = useState('')
  const [evidenciaUrl, setEvidenciaUrl] = useState('')
  const [errores, setErrores] = useState({})
  const [enviando, setEnviando] = useState(false)

  function cambiarEstado(nuevoEstado) {
    setEstado(nuevoEstado)
    if (nuevoEstado === 'PLANEADA') {
      setResultado('')
    }
  }

  async function manejarEnvio(evento) {
    evento.preventDefault()
    const validacion = validarActividad({
      sprint,
      tipo,
      nombreOtra,
      estado,
      resultado,
      responsable,
    })
    if (Object.keys(validacion).length > 0) {
      setErrores(validacion)
      return
    }

    setErrores({})
    setEnviando(true)
    try {
      const cuerpo = {
        sprint: Number(sprint),
        tipo,
        nombre_otra: tipo === 'OTRA' ? nombreOtra : '',
        estado,
        resultado: estado === 'REALIZADA' ? resultado : null,
        fecha: fecha || null,
        responsable: Number(responsable),
        descripcion,
        hallazgos: estado === 'REALIZADA' ? hallazgos : '',
        evidencia_url: estado === 'REALIZADA' ? evidenciaUrl : '',
      }

      const { ok, data } = await apiFetch(`projects/${proyectoId}/activities/`, {
        method: 'POST',
        body: cuerpo,
      })

      if (ok && data) {
        alGuardar(data)
        return
      }

      setErrores(extraerErroresActividad(data))
    } catch {
      setErrores({ general: 'No se pudo conectar con el servidor.' })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="tarjeta-panel formulario-actividad">
      <h2>Registrar actividad SQA</h2>

      {errores.general && (
        <div className="alerta-error" role="alert">
          {errores.general}
        </div>
      )}

      <form onSubmit={manejarEnvio} noValidate>
        <div className="fila-dos-columnas">
          <div className="campo-formulario">
            <label htmlFor="actividad-sprint">Sprint *</label>
            <input
              id="actividad-sprint"
              type="number"
              min="1"
              step="1"
              value={sprint}
              onChange={(e) => setSprint(e.target.value)}
              aria-invalid={Boolean(errores.sprint)}
              required
            />
            {errores.sprint && (
              <p className="error-campo" role="alert">
                {errores.sprint}
              </p>
            )}
          </div>

          <div className="campo-formulario">
            <label htmlFor="actividad-fecha">Fecha</label>
            <input
              id="actividad-fecha"
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              aria-invalid={Boolean(errores.fecha)}
            />
            {errores.fecha && (
              <p className="error-campo" role="alert">
                {errores.fecha}
              </p>
            )}
          </div>
        </div>

        <div className="campo-formulario">
          <label htmlFor="actividad-tipo">Tipo *</label>
          <select
            id="actividad-tipo"
            value={tipo}
            onChange={(e) => setTipo(e.target.value)}
          >
            {TIPOS_ACTIVIDAD.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.etiqueta}
              </option>
            ))}
          </select>
        </div>

        {tipo === 'OTRA' && (
          <div className="campo-formulario">
            <label htmlFor="actividad-nombre-otra">Nombre de la actividad *</label>
            <input
              id="actividad-nombre-otra"
              type="text"
              maxLength={100}
              placeholder="[Nombre de la práctica]"
              value={nombreOtra}
              onChange={(e) => setNombreOtra(e.target.value)}
              aria-invalid={Boolean(errores.nombre_otra)}
              required
            />
            {errores.nombre_otra && (
              <p className="error-campo" role="alert">
                {errores.nombre_otra}
              </p>
            )}
          </div>
        )}

        <fieldset className="grupo-radios">
          <legend>Estado *</legend>
          <div className="opciones-radio">
            <label>
              <input
                type="radio"
                name="estado-actividad"
                value="PLANEADA"
                checked={estado === 'PLANEADA'}
                onChange={() => cambiarEstado('PLANEADA')}
              />{' '}
              Planeada
            </label>
            <label>
              <input
                type="radio"
                name="estado-actividad"
                value="REALIZADA"
                checked={estado === 'REALIZADA'}
                onChange={() => cambiarEstado('REALIZADA')}
              />{' '}
              Realizada
            </label>
          </div>
          {estado === 'PLANEADA' && (
            <p className="texto-ayuda">
              El resultado se pide al marcarla como Realizada.
            </p>
          )}
        </fieldset>

        {estado === 'REALIZADA' && (
          <fieldset className="grupo-radios">
            <legend>Resultado *</legend>
            <div className="opciones-radio">
              <label>
                <input
                  type="radio"
                  name="resultado-actividad"
                  value="SATISFACTORIO"
                  checked={resultado === 'SATISFACTORIO'}
                  onChange={(e) => setResultado(e.target.value)}
                />{' '}
                Satisfactorio
              </label>
              <label>
                <input
                  type="radio"
                  name="resultado-actividad"
                  value="CON_HALLAZGOS"
                  checked={resultado === 'CON_HALLAZGOS'}
                  onChange={(e) => setResultado(e.target.value)}
                />{' '}
                Con hallazgos
              </label>
              <label>
                <input
                  type="radio"
                  name="resultado-actividad"
                  value="NO_SATISFACTORIO"
                  checked={resultado === 'NO_SATISFACTORIO'}
                  onChange={(e) => setResultado(e.target.value)}
                />{' '}
                No satisfactorio
              </label>
            </div>
            {errores.resultado && (
              <p className="error-campo" role="alert">
                {errores.resultado}
              </p>
            )}
          </fieldset>
        )}

        <div className="campo-formulario">
          <label htmlFor="actividad-responsable">Responsable *</label>
          <select
            id="actividad-responsable"
            value={responsable}
            onChange={(e) => setResponsable(e.target.value)}
          >
            {responsables.map((r) => (
              <option key={r.id} value={String(r.id)}>
                {r.email}
              </option>
            ))}
          </select>
          {errores.responsable && (
            <p className="error-campo" role="alert">
              {errores.responsable}
            </p>
          )}
        </div>

        <div className="campo-formulario">
          <label htmlFor="actividad-descripcion">Descripción</label>
          <textarea
            id="actividad-descripcion"
            rows={3}
            placeholder={
              estado === 'PLANEADA'
                ? '[Qué se va a revisar o probar]'
                : '[Qué se revisó o probó]'
            }
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
          />
        </div>

        {estado === 'REALIZADA' && (
          <>
            <div className="campo-formulario">
              <label htmlFor="actividad-hallazgos">Hallazgos</label>
              <textarea
                id="actividad-hallazgos"
                rows={2}
                placeholder="[Problemas encontrados]"
                value={hallazgos}
                onChange={(e) => setHallazgos(e.target.value)}
              />
            </div>

            <div className="campo-formulario">
              <label htmlFor="actividad-evidencia">Enlace de evidencia</label>
              <input
                id="actividad-evidencia"
                type="url"
                maxLength={500}
                placeholder="https://..."
                value={evidenciaUrl}
                onChange={(e) => setEvidenciaUrl(e.target.value)}
                aria-invalid={Boolean(errores.evidencia_url)}
              />
              {errores.evidencia_url && (
                <p className="error-campo" role="alert">
                  {errores.evidencia_url}
                </p>
              )}
            </div>
          </>
        )}

        <div className="acciones-formulario">
          <button
            type="submit"
            className="boton-primario boton-ajustado"
            disabled={enviando}
          >
            Guardar
          </button>
          <button
            type="button"
            className="boton-secundario"
            onClick={alCancelar}
          >
            Cancelar
          </button>
        </div>
      </form>
    </section>
  )
}

function validarActividad({
  sprint,
  tipo,
  nombreOtra,
  estado,
  resultado,
  responsable,
}) {
  const errores = {}
  const numSprint = Number(sprint)
  if (!sprint.toString().trim() || !Number.isInteger(numSprint) || numSprint < 1) {
    errores.sprint = 'El sprint debe ser un entero mayor o igual a 1.'
  }
  if (tipo === 'OTRA' && !nombreOtra.trim()) {
    errores.nombre_otra = 'Escribe el nombre de la actividad cuando el tipo es Otra.'
  }
  if (estado === 'REALIZADA' && !resultado) {
    errores.resultado = 'Una actividad Realizada necesita un resultado.'
  }
  if (!responsable) {
    errores.responsable = 'Selecciona un miembro responsable.'
  }
  return errores
}

function extraerErroresActividad(data) {
  if (!data) return { general: 'No se pudo registrar la actividad.' }
  const errores = {}
  const campos = [
    'sprint',
    'tipo',
    'nombre_otra',
    'estado',
    'resultado',
    'fecha',
    'responsable',
    'evidencia_url',
  ]
  for (const campo of campos) {
    if (Array.isArray(data[campo]) && data[campo].length > 0) {
      errores[campo] = data[campo][0]
    }
  }
  if (data.detail) {
    errores.general = data.detail
  }
  if (Object.keys(errores).length === 0) {
    errores.general = 'Verifica los datos de la actividad.'
  }
  return errores
}

function actualizarCatalogosLocales(
  listaActividades,
  usuario,
  setSprintsConocidos,
  setResponsables,
) {
  setSprintsConocidos((previos) => {
    const conjunto = new Set(previos)
    for (const a of listaActividades) {
      if (a.sprint) conjunto.add(Number(a.sprint))
    }
    return [...conjunto].sort((x, y) => x - y)
  })

  setResponsables((previos) => {
    const mapa = new Map()
    if (usuario?.id) {
      mapa.set(usuario.id, { id: usuario.id, email: usuario.email })
    }
    for (const r of previos) {
      if (r?.id) mapa.set(r.id, r)
    }
    for (const a of listaActividades) {
      if (a.responsable?.id) {
        mapa.set(a.responsable.id, a.responsable)
      }
    }
    return [...mapa.values()]
  })
}
