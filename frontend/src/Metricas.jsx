import { useEffect, useState } from 'react'
import { apiFetch } from './api.js'

function puedeCapturar(clase) {
  return (
    clase === 'ADMIN_CREADOR' ||
    clase === 'ADMIN_NORMAL' ||
    clase === 'COLABORADOR'
  )
}

function formatearCelda(valor, sufijo = '') {
  if (valor === null || valor === undefined || valor === '') {
    return '—'
  }
  return `${valor}${sufijo}`
}

function siguienteSprintSugerido(metricas) {
  if (!Array.isArray(metricas) || metricas.length === 0) return '1'
  const maximo = Math.max(...metricas.map((m) => Number(m.sprint) || 0))
  return String(maximo + 1)
}

export function SeccionMetricas({ proyecto }) {
  const [metricas, setMetricas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [errorCarga, setErrorCarga] = useState('')

  const [sprint, setSprint] = useState('1')
  const [defectosEncontrados, setDefectosEncontrados] = useState('')
  const [defectosCorregidos, setDefectosCorregidos] = useState('')
  const [horasCorreccion, setHorasCorreccion] = useState('')
  const [kloc, setKloc] = useState('')
  const [coberturaPct, setCoberturaPct] = useState('')
  const [errores, setErrores] = useState({})
  const [enviando, setEnviando] = useState(false)

  const capturaPermitida = puedeCapturar(proyecto.mi_clase)

  useEffect(() => {
    let activo = true
    setCargando(true)
    apiFetch(`projects/${proyecto.id}/metrics/`)
      .then(({ ok, data }) => {
        if (!activo) return
        if (ok && Array.isArray(data)) {
          setMetricas(data)
          setSprint(siguienteSprintSugerido(data))
        } else {
          setErrorCarga('No se pudieron cargar las métricas.')
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

  function limpiarFormulario(listaActual = metricas) {
    setSprint(siguienteSprintSugerido(listaActual))
    setDefectosEncontrados('')
    setDefectosCorregidos('')
    setHorasCorreccion('')
    setKloc('')
    setCoberturaPct('')
    setErrores({})
  }

  async function manejarEnvio(evento) {
    evento.preventDefault()
    const validacion = validarMetricas({
      sprint,
      defectosEncontrados,
      defectosCorregidos,
      horasCorreccion,
      kloc,
      coberturaPct,
    })
    if (Object.keys(validacion).length > 0) {
      setErrores(validacion)
      return
    }

    setErrores({})
    setEnviando(true)
    try {
      const cuerpo = construirCuerpoMetricas({
        sprint,
        defectosEncontrados,
        defectosCorregidos,
        horasCorreccion,
        kloc,
        coberturaPct,
      })

      const { ok, data } = await apiFetch(`projects/${proyecto.id}/metrics/`, {
        method: 'POST',
        body: cuerpo,
      })

      if (ok && data) {
        const actualizadas = [...metricas, data].sort(
          (a, b) => a.sprint - b.sprint,
        )
        setMetricas(actualizadas)
        limpiarFormulario(actualizadas)
        return
      }

      setErrores(extraerErroresMetricas(data))
    } catch {
      setErrores({ general: 'No se pudo conectar con el servidor.' })
    } finally {
      setEnviando(false)
    }
  }

  const metricasOrdenadas = [...metricas].sort((a, b) => b.sprint - a.sprint)

  return (
    <div className="rejilla-metricas">
      <section className="columna-metricas-lista">
        <h2>Métricas por sprint</h2>

        {cargando && <p role="status">Cargando métricas...</p>}
        {errorCarga && (
          <div className="alerta-error" role="alert">
            {errorCarga}
          </div>
        )}

        {!cargando && !errorCarga && metricasOrdenadas.length === 0 && (
          <p className="mensaje-vacio">
            Aún no hay métricas registradas para este proyecto.
          </p>
        )}

        {!cargando && !errorCarga && metricasOrdenadas.length > 0 && (
          <>
            <table className="tabla-datos solo-tabla-escritorio">
              <thead>
                <tr>
                  <th>Sprint</th>
                  <th>Def. encontrados</th>
                  <th>Def. corregidos</th>
                  <th>Horas corr.</th>
                  <th>KLOC</th>
                  <th>Cobertura</th>
                </tr>
              </thead>
              <tbody>
                {metricasOrdenadas.map((m) => (
                  <tr key={m.sprint}>
                    <td className="celda-fuerte">{m.sprint}</td>
                    <td>{formatearCelda(m.defectos_encontrados)}</td>
                    <td>{formatearCelda(m.defectos_corregidos)}</td>
                    <td>{formatearCelda(m.horas_correccion)}</td>
                    <td>{formatearCelda(m.kloc)}</td>
                    <td>{formatearCelda(m.cobertura_pct, ' %')}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="lista-tarjetas-movil">
              {metricasOrdenadas.map((m) => (
                <article key={m.sprint} className="tarjeta-item">
                  <div className="tarjeta-item-cabecera">
                    <strong>Sprint {m.sprint}</strong>
                  </div>
                  <p className="tarjeta-item-sub">
                    {formatearCelda(m.defectos_encontrados)} encontrados ·{' '}
                    {formatearCelda(m.defectos_corregidos)} corregidos ·{' '}
                    {formatearCelda(m.horas_correccion, ' h')} ·{' '}
                    {formatearCelda(m.kloc, ' KLOC')} ·{' '}
                    {formatearCelda(m.cobertura_pct, ' %')}
                  </p>
                </article>
              ))}
            </div>
          </>
        )}

        <p className="nota-pie">
          — = sin dato. Cuenta como &quot;Sin datos&quot; en el reporte; no es lo mismo que 0.
        </p>
      </section>

      {capturaPermitida && (
        <section className="tarjeta-panel columna-metricas-formulario">
          <h2>Capturar sprint</h2>

          {errores.general && (
            <div className="alerta-error" role="alert">
              {errores.general}
            </div>
          )}

          <form onSubmit={manejarEnvio} noValidate>
            <div className="campo-formulario">
              <label htmlFor="metrica-sprint">Sprint *</label>
              <input
                id="metrica-sprint"
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

            <div className="fila-dos-columnas">
              <div className="campo-formulario">
                <label htmlFor="metrica-encontrados">Def. encontrados</label>
                <input
                  id="metrica-encontrados"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="vacío"
                  value={defectosEncontrados}
                  onChange={(e) => setDefectosEncontrados(e.target.value)}
                  aria-invalid={Boolean(errores.defectos_encontrados)}
                />
                {errores.defectos_encontrados && (
                  <p className="error-campo" role="alert">
                    {errores.defectos_encontrados}
                  </p>
                )}
              </div>

              <div className="campo-formulario">
                <label htmlFor="metrica-corregidos">Def. corregidos</label>
                <input
                  id="metrica-corregidos"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="vacío"
                  value={defectosCorregidos}
                  onChange={(e) => setDefectosCorregidos(e.target.value)}
                  aria-invalid={Boolean(errores.defectos_corregidos)}
                />
                {errores.defectos_corregidos && (
                  <p className="error-campo" role="alert">
                    {errores.defectos_corregidos}
                  </p>
                )}
              </div>
            </div>

            <div className="fila-dos-columnas">
              <div className="campo-formulario">
                <label htmlFor="metrica-horas">Horas de corrección</label>
                <input
                  id="metrica-horas"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="vacío"
                  value={horasCorreccion}
                  onChange={(e) => setHorasCorreccion(e.target.value)}
                  aria-invalid={Boolean(errores.horas_correccion)}
                />
                {errores.horas_correccion && (
                  <p className="error-campo" role="alert">
                    {errores.horas_correccion}
                  </p>
                )}
              </div>

              <div className="campo-formulario">
                <label htmlFor="metrica-kloc">KLOC (total)</label>
                <input
                  id="metrica-kloc"
                  type="number"
                  min="0"
                  step="0.001"
                  placeholder="vacío"
                  value={kloc}
                  onChange={(e) => setKloc(e.target.value)}
                  aria-invalid={Boolean(errores.kloc)}
                />
                {errores.kloc && (
                  <p className="error-campo" role="alert">
                    {errores.kloc}
                  </p>
                )}
              </div>
            </div>

            <div className="campo-formulario">
              <label htmlFor="metrica-cobertura">Cobertura (%)</label>
              <input
                id="metrica-cobertura"
                type="number"
                min="0"
                max="100"
                step="0.01"
                placeholder="0 a 100"
                value={coberturaPct}
                onChange={(e) => setCoberturaPct(e.target.value)}
                aria-invalid={Boolean(errores.cobertura_pct)}
              />
              {errores.cobertura_pct && (
                <p className="error-campo" role="alert">
                  {errores.cobertura_pct}
                </p>
              )}
            </div>

            <p className="nota-formulario">Deja vacío lo que no sepas; 0 es un dato.</p>

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
                onClick={() => limpiarFormulario()}
              >
                Cancelar
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  )
}

function validarMetricas({
  sprint,
  defectosEncontrados,
  defectosCorregidos,
  horasCorreccion,
  kloc,
  coberturaPct,
}) {
  const errores = {}
  const numSprint = Number(sprint)
  if (!sprint.toString().trim() || !Number.isInteger(numSprint) || numSprint < 1) {
    errores.sprint = 'El sprint debe ser un entero mayor o igual a 1.'
  }

  const camposNoNegativos = [
    ['defectos_encontrados', defectosEncontrados],
    ['defectos_corregidos', defectosCorregidos],
    ['horas_correccion', horasCorreccion],
    ['kloc', kloc],
  ]

  for (const [clave, valor] of camposNoNegativos) {
    if (valor !== '' && Number(valor) < 0) {
      errores[clave] = 'El valor no puede ser negativo.'
    }
  }

  if (coberturaPct !== '') {
    const cob = Number(coberturaPct)
    if (Number.isNaN(cob) || cob < 0 || cob > 100) {
      errores.cobertura_pct = 'La cobertura debe estar entre 0 y 100.'
    }
  }

  return errores
}

function construirCuerpoMetricas({
  sprint,
  defectosEncontrados,
  defectosCorregidos,
  horasCorreccion,
  kloc,
  coberturaPct,
}) {
  return {
    sprint: Number(sprint),
    defectos_encontrados:
      defectosEncontrados === '' ? null : Number(defectosEncontrados),
    defectos_corregidos:
      defectosCorregidos === '' ? null : Number(defectosCorregidos),
    horas_correccion: horasCorreccion === '' ? null : Number(horasCorreccion),
    kloc: kloc === '' ? null : Number(kloc),
    cobertura_pct: coberturaPct === '' ? null : Number(coberturaPct),
  }
}

function extraerErroresMetricas(data) {
  if (!data) return { general: 'No se pudieron guardar las métricas.' }
  const errores = {}
  const campos = [
    'sprint',
    'defectos_encontrados',
    'defectos_corregidos',
    'horas_correccion',
    'kloc',
    'cobertura_pct',
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
    errores.general = 'Verifica los valores capturados.'
  }
  return errores
}
