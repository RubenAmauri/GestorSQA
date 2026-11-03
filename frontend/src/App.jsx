import { useEffect, useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import { apiFetch } from './api.js'

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

function Inicio() {
  return (
    <section>
      <h1>Gestor SQA</h1>
      <p>Esqueleto de la aplicación. Las pantallas se agregan según la sección 3.5 del SDS.</p>
      <EstadoServicio />
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

export default function App() {
  return (
    <main className="contenedor">
      <Routes>
        <Route path="/" element={<Inicio />} />
        <Route path="*" element={<NoEncontrado />} />
      </Routes>
    </main>
  )
}
