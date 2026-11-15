# Prueba de carga PR-RNF02-01 (RNF-02)

**Meta (SRS v1.2, RNF-02):** percentil 95 < 3 s cuando 50 usuarios simultáneos consultan el reporte de salud (`GET /api/projects/{id}/report/`), con 100 proyectos × 10 sprints; cada sprint con 1 registro de métricas y 5 actividades.

Herramientas:

- `python manage.py sembrar_carga` (en `backend/`): crea y borra los datos de prueba.
- `locustfile.py` (esta carpeta): los 50 usuarios virtuales.
- Locust se instala con `pip install -r backend/requirements-dev.txt`; no va en la imagen de producción.

## 1. Antes de empezar en producción (obligatorio)

En la VM, desde la carpeta del repositorio:

```bash
./respaldo.sh                      # deja un respaldo en respaldos/; cópialo fuera de la VM
```

Si algo sale mal, se restaura con `./restaurar.sh <archivo>`.

## 2. Sembrar los datos

El comando exige `--confirmar` para que nadie lo corra por accidente. La contraseña de los 50 usuarios de prueba se pasa por la variable de entorno `CARGA_PASSWORD` (así no queda en el historial del shell); también acepta `--password`.

En producción, dentro del contenedor de la aplicación:

```bash
read -rs CARGA_PASSWORD && export CARGA_PASSWORD      # escribe la contraseña sin que se vea
docker compose exec -e CARGA_PASSWORD app python manage.py sembrar_carga --confirmar
```

En local, desde `backend/`:

```bash
export DB_ENGINE=sqlite DJANGO_DEBUG=1 CARGA_PASSWORD=una-clave-local
python manage.py migrate && python manage.py createcachetable
python manage.py sembrar_carga --confirmar
```

Por omisión crea el volumen exacto del RNF-02: 50 usuarios (`carga-01@prueba.gestorsqa` … `carga-50@prueba.gestorsqa`) y 100 proyectos ("Carga 001" … "Carga 100", periodo "Prueba de carga"). Cada usuario es Admin Creador de 2 proyectos. Al terminar imprime un resumen para pegarlo como evidencia:

```
Sembrado de la prueba de carga (PR-RNF02-01)
  Usuarios creados: 50
  Proyectos creados: 100
  Métricas creadas: 1000
  Actividades creadas: 5000
Quedan en la base: 50 usuarios de carga y 100 proyectos de carga.
```

- Es idempotente: si se corre otra vez, solo crea lo que falte.
- La contraseña se fija **solo al crear** cada usuario. Si cambias `CARGA_PASSWORD` después, limpia (paso 5) y vuelve a sembrar.
- Para probar con otro volumen: `--usuarios`, `--proyectos`, `--sprints` y `--actividades-por-sprint`.

## 3. Correr la prueba (modo headless)

Desde esta carpeta, en una máquina con Locust (no en la VM, para no competir por CPU con el servidor):

```bash
export CARGA_PASSWORD=...                  # la misma del paso 2
mkdir -p resultados
locust -f locustfile.py --headless \
  -H https://<dominio-del-servidor> \
  -u 50 --spawn-rate 0.077 \
  --reset-stats --run-time 16m \
  --csv resultados/rnf02 --html resultados/rnf02.html
```

| Parámetro | Valor | Por qué |
|---|---|---|
| `-u` | 50 | Usuarios simultáneos del RNF-02. |
| `--spawn-rate` | 0.077 | Tasa de llegada: un usuario cada 13 s (unos 4.6 por minuto). Ver la sección del límite de intentos. |
| `--reset-stats` | — | Borra las estadísticas cuando ya entraron los 50 usuarios: se mide solo la fase con carga completa. |
| `--run-time` | 16m | Unos 11 minutos de rampa (50 × 13 s) más **5 minutos de medición** con 50 usuarios. |
| `--csv` | `resultados/rnf02` | Exporta los resultados (ver el paso 4). |

### Espera entre consultas

Cada usuario virtual espera entre 1 y 3 s entre consultas (un uso realista: lee el reporte y vuelve a consultar). Es un parámetro:

```bash
CARGA_ESPERA_MIN=0 CARGA_ESPERA_MAX=0 locust ...     # peor caso: sin espera
```

### Cómo se evita que el límite de intentos contamine la medición

El servidor permite **5 inicios de sesión por minuto por IP** (RNF-05) y **no se desactiva** para la prueba. Desde una sola máquina, los 50 usuarios virtuales comparten IP, así que:

1. Cada usuario virtual inicia sesión **una sola vez**, al empezar (`GET /api/auth/csrf/` y luego `POST /api/auth/login/` con `X-CSRFToken`). El resto de la prueba usa esa sesión.
2. Los usuarios entran **escalonados** con `--spawn-rate 0.077`: unos 4.6 inicios de sesión por minuto, por debajo del límite.
3. `--reset-stats` descarta todo lo medido durante la rampa: el percentil 95 de la fila del reporte corresponde solo a las consultas con 50 usuarios simultáneos. El inicio de sesión del último usuario termina justo después del reinicio, así que en el CSV puede aparecer una fila `inicio de sesión` con 1 petición; no afecta la fila del reporte.
4. Si aun así llega un 429, el usuario virtual espera lo que indica `Retry-After` y reintenta. Queda en el log y en `rnf02_failures.csv` con el nombre `inicio de sesión`, para que se vea si pasó.

### Opción distribuida (no se usa por omisión)

Como el límite es por IP, se puede repartir la carga entre varias máquinas para acortar la rampa. Cada worker usa un rango distinto de cuentas con `CARGA_PRIMER_USUARIO` y `CARGA_USUARIOS`, y respeta igual 5 inicios de sesión por minuto desde su IP:

```bash
# Máquina principal (solo coordina)
locust -f locustfile.py --master --headless -H https://<dominio> -u 50 --spawn-rate 0.15 \
  --expect-workers 2 --reset-stats --run-time 11m --csv resultados/rnf02
# Máquina A (cuentas 01 a 25) y máquina B (cuentas 26 a 50)
CARGA_PRIMER_USUARIO=1  CARGA_USUARIOS=25 locust -f locustfile.py --worker --master-host <ip-principal>
CARGA_PRIMER_USUARIO=26 CARGA_USUARIOS=25 locust -f locustfile.py --worker --master-host <ip-principal>
```

## 4. Leer el resultado

En `resultados/rnf02_stats.csv`, la fila con `Name` = `/api/projects/[id]/report/`:

- Columna `95%`: percentil 95 en milisegundos. **Cumple si es menor que 3000.**
- Columnas `Request Count` y `Failure Count`: cuántas consultas se midieron y cuántas fallaron.

`rnf02_failures.csv` debe estar vacío o solo con reintentos de `inicio de sesión` anteriores al reinicio de estadísticas. Guarda los CSV y el HTML como evidencia junto con los resúmenes de los pasos 2 y 5.

## 5. Limpiar y verificar

```bash
docker compose exec app python manage.py sembrar_carga --limpiar --confirmar
```

Borra **solo** lo que creó el comando (los usuarios `carga-NN@prueba.gestorsqa`, sus proyectos y, en cascada, sus métricas, actividades y membresías). La última línea del resumen es la verificación: debe decir

```
Quedan en la base: 0 usuarios de carga y 0 proyectos de carga.
```

Si un usuario de carga quedó como responsable de datos reales, el comando no borra nada y lo explica.
