import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { apiFetch } from './api.js'
import { BarraSuperior, InicioSesion, Registro } from './Sesion.jsx'

function EstadoServicio() {
  const [estado, setEstado] = useState('consultando')

  useEffect(() => {
    let activo = true
    apiFetch('health/')
      .then(({ ok }) => activo && setEstado(ok ? 'disponible' : 'con problemas'))
      .catch(() => activo && setEstado('sin conexión'))
    return () => {
      activo = false
    }
  }, [])

  return <p role="status">Servicio: {estado}</p>
}

function MisProyectos() {
  return (
    <section>
      <h1>Mis proyectos</h1>
      <p>Solo se listan los proyectos donde eres miembro.</p>
      <EstadoServicio />
    </section>
  )
}

function NuevoProyecto() {
  return (
    <section>
      <h1>Registrar proyecto</h1>
    </section>
  )
}

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
          <Route path="*" element={<NoEncontrado />} />
        </Routes>
      </main>
    </div>
  )
}
