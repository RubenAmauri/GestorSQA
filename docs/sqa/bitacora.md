# Bitácora de SQA – Gestor SQA

Registro de las actividades de aseguramiento de calidad del proyecto (SQAP, sección 7).

**Reglas (SQAP 6.5 y 7.1.2):**
- Cada entrada lleva la fecha real en que ocurrió la actividad.
- Las entradas solo se agregan al final; nunca se borran ni se editan. Una corrección se hace con una entrada nueva que remite a la original.
- Las actividades que ya quedan registradas en GitHub (PR, revisiones de código, resultados de la CI, issues) se resumen aquí en cada punto de control.

**Tipos de entrada:** Decisión · Revisión · Auditoría · Prueba · No conformidad · Desviación · Despliegue · Respaldo · Indicación de la clienta · Punto de control

| Fecha | Tipo | Descripción | Referencias | Responsable | Horas |
|---|---|---|---|---|---|
| 2026-10-30 | Revisión | Revisión del SDS v0.2 contra el enunciado, el documento de visión y el SRS v1.0. Se registraron 20 hallazgos (contradicciones, falta de trazabilidad, sobreingeniería y requisitos no verificables). | SDS v0.2, SRS v1.0 | Rubén Amauri | |
| 2026-10-31 | Decisión | Regla de discrepancias: ante una contradicción entre documentos se decide contra el enunciado de trabajo. | SQAP 4.4.5 | Rubén Amauri | |
| 2026-10-31 | Decisión | Regla del estado de salud: densidad acumulada, umbrales de cobertura basados en la guía de Google, indicador de actividades con resultados, historial por sprint y estado "Sin evaluación". | SRS v1.1, anexos A y C | Rubén Amauri | |
| 2026-10-31 | Decisión | Despliegue en Azure for Students (plan B: Google Cloud; plan C: ejecución local). | SDS v0.3, ADR-08 | Rubén Amauri | |
| 2026-10-31 | Revisión | Corrección del SDS a la versión 0.3 y del SRS a la versión 1.1 a partir de los hallazgos del 2026-10-30. | SDS v0.3, SRS v1.1 | Rubén Amauri | |
| 2026-10-31 | Revisión | Modelo C4 (niveles 1 a 3) rehecho desde el SDS v0.3; se elimina el servicio de correo descartado. | Modelo C4 | Rubén Amauri | |
| 2026-11-01 | Decisión | Diseño responsivo sin jerarquía entre escritorio y móvil, conforme a RNF-01. | SDS v0.4 | Rubén Amauri | |
| 2026-11-01 | Revisión | Wireframes v1 de baja fidelidad: 10 pantallas en escritorio y móvil, más 4 estados, cada elemento trazado a HU, RF y CA. | Wireframes v1, SDS 3.5 | Rubén Amauri | |
| 2026-11-01 | Decisión | Plan de aseguramiento de la calidad con IEEE 730-2014, ISO/IEC 25010:2011 y referencia a ISO/IEC 29110. El contenido de SQA del SDS pasa al SQAP. | SQAP v1.0, SDS v0.4 | Rubén Amauri | |
| 2026-11-01 | Decisión | Estructura del repositorio, entorno de desarrollo con Docker Compose, integración continua y plantillas de PR e issues. | PR del esqueleto | Rubén Amauri | |
