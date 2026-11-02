import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { SeccionActividades } from './Actividades.jsx'
import { apiFetch } from './api.js'
import { SeccionMetricas } from './Metricas.jsx'
import {
  MisProyectos,
  NuevoProyecto,
  UnirseProyecto,
  VistaProyecto,
} from './Proyectos.jsx'
import { BarraSuperior, InicioSesion, Registro } from './Sesion.jsx'

function NoEncontrado() {
  return (
    <section>
      <h1>Página no encontrada</h1>
      <Link to="/">Volver al inicio</Link>
    </section>
  )
}

function RutaProtegida({ usuario, cargando, children }) {
  if (cargando) {
    return <p role="status">Verificando sesión...</p>
  }
  if (!usuario) {
    return <Navigate to="/login" replace />
  }
  return children
}

function RutaVisitante({ usuario, cargando, children }) {
  if (!cargando && usuario) {
    return <Navigate to="/proyectos" replace />
  }
  return children
}

export default function App() {
  const navigate = useNavigate()
  const [usuario, setUsuario] = useState(null)
  const [cargandoSesion, setCargandoSesion] = useState(true)

  useEffect(() => {
    let activo = true
    apiFetch('auth/me/')
      .then(({ ok, data }) => {
        if (!activo) return
        setUsuario(ok ? data : null)
        setCargandoSesion(false)
      })
      .catch(() => {
        if (!activo) return
        setUsuario(null)
        setCargandoSesion(false)
      })
    return () => {
      activo = false
    }
  }, [])

  async function cerrarSesion() {
    try {
      await apiFetch('auth/logout/', { method: 'POST' })
    } finally {
      setUsuario(null)
      navigate('/login', { replace: true })
    }
  }

  return (
    <div className="pagina">
      <BarraSuperior usuario={usuario} alCerrarSesion={cerrarSesion} />
      <main className="contenedor">
        <Routes>
          <Route
            path="/login"
            element={
              <RutaVisitante usuario={usuario} cargando={cargandoSesion}>
                <InicioSesion alAutenticar={setUsuario} />
              </RutaVisitante>
            }
          />
          <Route
            path="/registro"
            element={
              <RutaVisitante usuario={usuario} cargando={cargandoSesion}>
                <Registro alAutenticar={setUsuario} />
              </RutaVisitante>
            }
          />
          <Route
            path="/"
            element={
              <RutaProtegida usuario={usuario} cargando={cargandoSesion}>
                <Navigate to="/proyectos" replace />
              </RutaProtegida>
            }
          />
          <Route
            path="/proyectos"
            element={
              <RutaProtegida usuario={usuario} cargando={cargandoSesion}>
                <MisProyectos />
              </RutaProtegida>
            }
          />
          <Route
            path="/proyectos/nuevo"
            element={
              <RutaProtegida usuario={usuario} cargando={cargandoSesion}>
                <NuevoProyecto />
              </RutaProtegida>
            }
          />
          <Route
            path="/proyectos/unirse"
            element={
              <RutaProtegida usuario={usuario} cargando={cargandoSesion}>
                <UnirseProyecto />
              </RutaProtegida>
            }
          />
          <Route
            path="/proyectos/:id/*"
            element={
              <RutaProtegida usuario={usuario} cargando={cargandoSesion}>
                <VistaProyecto
                  usuario={usuario}
                  SeccionMetricas={SeccionMetricas}
                  SeccionActividades={SeccionActividades}
                />
              </RutaProtegida>
            }
          />
          <Route path="*" element={<NoEncontrado />} />
        </Routes>
      </main>
    </div>
  )
}
