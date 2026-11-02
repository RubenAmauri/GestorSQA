import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from './api.js'

const ETIQUETA_NIVEL = {
  OPTIMO: 'ÓPTIMO',
  ADVERTENCIA: 'ADVERTENCIA',
  CRITICO: 'CRÍTICO',
  SIN_DATOS: 'SIN DATOS',
  NO_APLICA: 'NO APLICA',
  SIN_EVALUACION: 'SIN EVALUACIÓN',
}

const CLASE_NIVEL = {
  OPTIMO: 'insignia-nivel insignia-optimo',
  ADVERTENCIA: 'insignia-nivel insignia-advertencia',
  CRITICO: 'insignia-nivel insignia-critico',
  SIN_DATOS: 'insignia-nivel insignia-sin-datos',
  NO_APLICA: 'insignia-nivel insignia-no-aplica',
  SIN_EVALUACION: 'insignia-nivel insignia-sin-evaluacion',
}

const ETIQUETA_ESTADO_ACT = {
  PLANEADA: 'Planeada',
  REALIZADA: 'Realizada',
}

const ETIQUETA_RESULTADO_ACT = {
  SATISFACTORIO: 'Satisfactorio',
  CON_HALLAZGOS: 'Con hallazgos',
  NO_SATISFACTORIO: 'No satisfactorio',
}

function puedeRegistrarEnProyecto(clase) {
  return (
    clase === 'ADMIN_CREADOR' ||
    clase === 'ADMIN_NORMAL' ||
    clase === 'COLABORADOR'
  )
}

function InsigniaNivel({ nivel, grande = false }) {
  const claseBase = CLASE_NIVEL[nivel] || 'insignia-nivel'
  const clase = grande ? `${claseBase} insignia-grande` : claseBase
  return <span className={clase}>{ETIQUETA_NIVEL[nivel] || nivel}</span>
}

function formatearValorIndicador(indicador, sufijo = '') {
  if (!indicador) return 'Sin datos'
  if (indicador.nivel === 'NO_APLICA') return 'No aplica'
  if (indicador.valor === null || indicador.valor === undefined) {
    return 'Sin datos'
  }
  return `${indicador.valor}${sufijo}`
}

function formatearCeldaHistorial(indicador, sufijo = '') {
  if (!indicador) return '— (sin dato)'
  if (indicador.nivel === 'NO_APLICA') return 'No aplica'
  if (indicador.valor === null || indicador.valor === undefined) {
    return '— (sin dato)'
  }
  return `${indicador.valor}${sufijo}`
}

export function SeccionReporte({ proyecto }) {
  const [reporte, setReporte] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let activo = true
    setCargando(true)
    setError('')
    apiFetch(`projects/${proyecto.id}/report/`)
      .then(({ ok, data }) => {
        if (!activo) return
        if (ok && data) {
          setReporte(data)
        } else {
          setError('No se pudo cargar el reporte de salud.')
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
  }, [proyecto.id])

  if (cargando) {
    return <p role="status">Calculando reporte de salud...</p>
  }

  if (error || !reporte) {
    return (
      <div className="alerta-error" role="alert">
        {error || 'No se pudo cargar el reporte.'}
      </div>
    )
  }

  if (reporte.estado_general === 'SIN_EVALUACION') {
    const escritura = puedeRegistrarEnProyecto(proyecto.mi_clase)
    return (
      <section className="recuadro-sin-evaluacion" aria-label="Estado de salud">
        <div className="fila-insignia-sin-evaluacion">
          <InsigniaNivel nivel="SIN_EVALUACION" grande />
        </div>
        <p className="texto-sin-evaluacion">
          Este proyecto aún no tiene métricas ni actividades realizadas, así que no hay
          estado de salud que calcular.
        </p>
        {escritura && (
          <div className="acciones-sin-evaluacion">
            <Link
              to={`/proyectos/${proyecto.id}/metricas`}
              className="boton-enlace-primario boton-ajustado"
            >
              Registrar la primera métrica
            </Link>
            <Link
              to={`/proyectos/${proyecto.id}/actividades?nueva=1`}
              className="enlace-cancelar"
            >
              o registrar una actividad SQA
            </Link>
          </div>
        )}
      </section>
    )
  }

  const sprintRef = reporte.sprint_referencia
  const ind = reporte.indicadores || {}
  const historialOrdenado = [...(reporte.historial || [])].sort(
    (a, b) => b.sprint - a.sprint,
  )
  const actividadesSprintRef = (reporte.actividades || []).filter(
    (a) => a.sprint === sprintRef,
  )
  const noSatisfactoriasRef = actividadesSprintRef.filter(
    (a) => a.estado === 'REALIZADA' && a.resultado === 'NO_SATISFACTORIO',
  ).length

  function descargarCsv() {
    const contenido = generarCsvReporte(reporte)
    const blob = new Blob([contenido], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = `reporte-proyecto-${proyecto.id}.csv`
    enlace.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="contenedor-reporte">
      <div className="barra-estado-general">
        <div className="grupo-estado-general">
          <span className="etiqueta-estado-general">Estado general</span>
          <InsigniaNivel nivel={reporte.estado_general} grande />
          <span className="texto-sprint-referencia">
            Sprint de referencia: {sprintRef}
          </span>
        </div>

        <div className="acciones-reporte solo-escritorio">
          <button type="button" className="boton-secundario" onClick={descargarCsv}>
            Descargar CSV
          </button>
          <button
            type="button"
            className="boton-secundario"
            onClick={() => window.print()}
          >
            Vista imprimible
          </button>
        </div>
      </div>

      <h2>Indicadores del sprint {sprintRef}</h2>
      <div className="rejilla-indicadores">
        <article className="tarjeta-indicador">
          <p className="titulo-indicador">Densidad de defectos</p>
          <p className="valor-indicador">
            {ind.densidad?.valor !== null && ind.densidad?.valor !== undefined ? (
              <>
                <strong>{ind.densidad.valor}</strong>{' '}
                <span className="unidad-indicador">def/KLOC</span>
              </>
            ) : (
              <strong>Sin datos</strong>
            )}
          </p>
          <InsigniaNivel nivel={ind.densidad?.nivel || 'SIN_DATOS'} />
        </article>

        <article className="tarjeta-indicador">
          <p className="titulo-indicador">Cobertura de pruebas</p>
          <p className="valor-indicador">
            <strong>{formatearValorIndicador(ind.cobertura, ' %')}</strong>
          </p>
          <InsigniaNivel nivel={ind.cobertura?.nivel || 'SIN_DATOS'} />
        </article>

        <article className="tarjeta-indicador">
          <p className="titulo-indicador">Tiempo prom. de corrección</p>
          <p className="valor-indicador">
            <strong>{formatearValorIndicador(ind.tiempo_correccion, ' h')}</strong>
          </p>
          <InsigniaNivel nivel={ind.tiempo_correccion?.nivel || 'SIN_DATOS'} />
        </article>

        <article className="tarjeta-indicador">
          <p className="titulo-indicador">Actividades realizadas</p>
          <p className="valor-indicador">
            <strong>
              {ind.actividades?.valor !== null && ind.actividades?.valor !== undefined
                ? Math.trunc(ind.actividades.valor)
                : 0}
            </strong>{' '}
            <span className="unidad-indicador">
              {noSatisfactoriasRef} no satisfactorias
            </span>
          </p>
          <InsigniaNivel nivel={ind.actividades?.nivel || 'CRITICO'} />
        </article>
      </div>

      <h2>Historial por sprint</h2>
      <table className="tabla-datos solo-tabla-escritorio">
        <thead>
          <tr>
            <th>Sprint</th>
            <th>Densidad</th>
            <th>Cobertura</th>
            <th>Tiempo corr.</th>
            <th>Actividades plan. / real.</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {historialOrdenado.map((s) => (
            <tr key={s.sprint}>
              <td className="celda-fuerte">{s.sprint}</td>
              <td>{formatearCeldaHistorial(s.densidad)}</td>
              <td>{formatearCeldaHistorial(s.cobertura, ' %')}</td>
              <td>{formatearCeldaHistorial(s.tiempo_correccion, ' h')}</td>
              <td>
                {s.actividades_planeadas} / {s.actividades_realizadas}
              </td>
              <td>
                <InsigniaNivel nivel={s.nivel} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="lista-tarjetas-movil">
        {historialOrdenado.map((s) => (
          <article key={s.sprint} className="tarjeta-item fila-historial-movil">
            <div>
              <strong>Sprint {s.sprint}</strong>{' '}
              <span className="texto-ayuda">
                {s.actividades_planeadas}/{s.actividades_realizadas} act.
              </span>
            </div>
            <InsigniaNivel nivel={s.nivel} />
          </article>
        ))}
      </div>

      <div className="cabecera-actividades-reporte">
        <h2>Actividades del sprint {sprintRef}</h2>
        <Link to={`/proyectos/${proyecto.id}/actividades`} className="enlace-barra">
          Ver todas
        </Link>
      </div>

      {actividadesSprintRef.length === 0 ? (
        <p className="mensaje-vacio">
          No hay actividades registradas en el sprint {sprintRef}.
        </p>
      ) : (
        <table className="tabla-datos">
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Estado</th>
              <th>Responsable</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {actividadesSprintRef.map((a) => (
              <tr key={a.id}>
                <td>{a.nombre}</td>
                <td>{ETIQUETA_ESTADO_ACT[a.estado] || a.estado}</td>
                <td>{a.responsable}</td>
                <td>
                  {a.resultado
                    ? ETIQUETA_RESULTADO_ACT[a.resultado] || a.resultado
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="acciones-reporte-movil">
        <button type="button" className="boton-secundario" onClick={descargarCsv}>
          Descargar CSV
        </button>
        <button
          type="button"
          className="boton-secundario"
          onClick={() => window.print()}
        >
          Vista imprimible
        </button>
      </div>
    </section>
  )
}

function generarCsvReporte(reporte) {
  const lineas = [
    `Proyecto,${reporte.proyecto?.nombre || ''}`,
    `Periodo,${reporte.proyecto?.periodo_nombre || ''}`,
    `Estado general,${reporte.estado_general}`,
    `Sprint de referencia,${reporte.sprint_referencia ?? ''}`,
    '',
    'Sprint,Estado,Densidad,Cobertura,Tiempo correccion,Planeadas,Realizadas',
  ]
  for (const s of reporte.historial || []) {
    lineas.push(
      [
        s.sprint,
        s.nivel,
        s.densidad?.valor ?? '',
        s.cobertura?.valor ?? '',
        s.tiempo_correccion?.valor ?? '',
        s.actividades_planeadas,
        s.actividades_realizadas,
      ].join(','),
    )
  }
  return lineas.join('\n')
}
