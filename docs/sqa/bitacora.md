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
| 2026-11-01 | Despliegue | Aprovisionamiento de máquina virtual Ubuntu 24.04 LTS en Azure (2 vCPU, 4 GiB RAM, puertos 80/443/22, DNS `gestorsqa.westus2.cloudapp.azure.com`). Configuración de alerta de presupuesto de 50 USD, instalación de Docker Engine, 2 GB de swap y prueba de humo exitosa (`docker build -t gestor-sqa .`) en la rama `infra-esqueleto`. | docs/despliegue.md (SQAP 5.1.4 / SDS 5.2) | Oliver Germain Saldivar Elizalde | |
| 2026-11-02 | No conformidad | Revisión del frontend (PR #23) en escritorio y móvil: en 360 px de ancho la tabla "Actividades del sprint" del reporte provoca scroll horizontal. Severidad baja; se registra para corregir antes de la entrega final. | Issue #25, RNF-01 | Rubén Amauri | |
| 2026-11-02 | Desviación | Los PR #4, #8, #10 y #14 se fusionaron sin borrar su rama, por lo que quedaron en ramas intermedias y no en `main`. Corrección: se cambió la base del #16 a `main` (contiene toda la cadena y la fusión de `rf08-actividades` con el conflicto de rutas resuelto), se volvió a aprobar y se fusionó; el #12 se cerró sin fusionar porque su contenido entró por el #16. Desde entonces cada fusión borra su rama. | PR #4, #8, #10, #12, #14, #16 | Rubén Amauri | |
| 2026-11-02 | Revisión | Integración en `main` de los PR #16, #18 y #19 a #23, cada uno aprobado por un integrante distinto de su autor. Revisores: isaac22232 (#4, #12), antoniodlcd (#8, #19 a #23), cberumenr (#10), OliverSaldivar (#14, #16, #18) y RubenAmauri (#19, #23). CI de `main` en verde: backend con 191 pruebas y 98.82 % de cobertura (100 % en motor de salud, umbrales y acceso); frontend con 24 pruebas; imagen Docker construida. | PR #16, #18 a #23; GitHub Actions | Rubén Amauri | |
| 2026-11-02 | Despliegue | Redespliegue de la rama `main` en Azure con `./deploy.sh main`; la aplicación queda disponible en `https://gestorsqa.westus2.cloudapp.azure.com`. | deploy.sh, docs/despliegue.md | [completar] | |
| 2026-11-03 | Prueba | Prueba de humo manual en producción con los datos de ejemplo de los wireframes (3 sprints de métricas y 7 actividades). Resultado igual al esperado por `test_reporte_api.py`: estado general Advertencia, sprint de referencia 3, densidad 6.11 (Advertencia), cobertura 78 (Óptimo), tiempo de corrección 3.5 (Óptimo), actividades 2 (Óptimo) e historial Crítico, Advertencia, Advertencia. | PR-RF10, PR-RF11, HU-07 | Rubén Amauri | |
| 2026-11-03 | Punto de control | Entrega Beta: avance de funcionalidad (RF-01, RF-02, RF-03, RF-06, RF-07, RF-08, RF-10 y RF-11 con su frontend, desplegados) y resultados de SQA (CI obligatoria, revisiones por pares, cobertura y no conformidades #2 y #25). | Issues #2 y #25, etiqueta `beta` | Rubén Amauri | |
