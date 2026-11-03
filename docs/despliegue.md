# Guía de despliegue – Gestor SQA

Documentación de la configuración del servidor y del procedimiento de despliegue y operación en producción (SDS sección 5, ADR-08 y SQAP 5.1.4).

## 1. Infraestructura del servidor (SDS 5.2)

| Parámetro | Valor configurado |
|---|---|
| Proveedor | Microsoft Azure (Azure for Students) |
| Alerta de presupuesto | Configurada en 50 USD |
| Región | West US 2 (`westus2`) |
| Nombre DNS | `gestorsqa.westus2.cloudapp.azure.com` |
| Sistema operativo | Ubuntu Server 24.04 LTS (Linux) |
| Tamaño | 2 vCPU, 4 GiB de RAM + 2 GB de memoria swap (`/swapfile`) |
| Reglas de red (NSG) | Puertos `80/tcp` (HTTP) y `443/tcp` (HTTPS) abiertos; `22/tcp` (SSH) solo con llave criptográfica (`azureuser`) |

## 2. Arquitectura de contenedores en producción (SDS 5.1)

El archivo `compose.yml` levanta tres servicios:

- **`proxy` (`caddy:2.8`)**: Escucha en los puertos `80` y `443`, obtiene y renueva automáticamente el certificado TLS para `DOMINIO`, redirige `HTTP` a `HTTPS` (`308 Permanent Redirect`) y reenvía el tráfico a `app:8000` (`Caddyfile`).
- **`app` (`gestor-sqa:latest`)**: Imagen construida en dos etapas (`Dockerfile`): compila el SPA de React con Vite y lo sirve junto con la API de Django mediante `gunicorn` y `WhiteNoise`. Al iniciar aplica migraciones (`migrate --noinput`), crea la tabla de caché (`createcachetable`) y expone el endpoint de salud `/api/health/`.
- **`db` (`mariadb:11.4`)**: Base de datos relacional con almacenamiento persistente en el volumen `db_data`, aislada en la red interna de Compose (sin puerto publicado al exterior).

## 3. Preparación inicial de la máquina virtual

Comandos ejecutados en la VM durante su aprovisionamiento (`2026-11-01`):

```bash
# 1. Instalar Docker Engine y el plugin de Docker Compose
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"

# 2. Configurar 2 GB de swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 3. Clonar el repositorio y validar construcción de imagen
git clone https://github.com/RubenAmauri/GestorSQA.git
cd GestorSQA
docker build -t gestor-sqa .
```

## 4. Variables de entorno (`.env`)

En el directorio `~/GestorSQA` del servidor se crea el archivo `.env` a partir de `.env.example` (el archivo `.env` nunca se sube al repositorio):

```bash
cp .env.example .env
nano .env
```

Se generan claves aleatorias seguras para `DJANGO_SECRET_KEY`, `DB_PASSWORD` y `MARIADB_ROOT_PASSWORD`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Valores requeridos para el dominio en Azure:

```dotenv
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=gestorsqa.westus2.cloudapp.azure.com,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://gestorsqa.westus2.cloudapp.azure.com
DOMINIO=gestorsqa.westus2.cloudapp.azure.com
```

## 5. Procedimiento de despliegue (SDS 5.3)

Para desplegar o actualizar el servidor se ejecuta `deploy.sh` indicando la rama (por defecto `main`):

```bash
cd ~/GestorSQA
./deploy.sh main
```

El script `deploy.sh` realiza en orden:
1. Verifica que exista `.env`.
2. Si el contenedor `db` ya está en ejecución, genera un respaldo previo con `./respaldo.sh`.
3. Actualiza el código desde `origin` (`git fetch`, `git checkout` y `git pull --ff-only`).
4. Construye y levanta los servicios en segundo plano (`docker compose up -d --build`).
5. Espera hasta que el `healthcheck` del contenedor `app` pase a estado `healthy`.

Cada despliegue se registra en `docs/sqa/bitacora.md` con el tipo `Despliegue`.

## 6. Verificación posterior al despliegue (`PR-RNF05-04`)

Después de cada despliegue se comprueba el estado del servicio y la configuración de HTTPS/cookies seguras (`RNF-05`):

```bash
# 1. Salud de la aplicación y conexión a MariaDB
curl -s https://gestorsqa.westus2.cloudapp.azure.com/api/health/
# Salida obtenida:
# {"status": "ok", "database": "ok"}

# 2. Redirección automática de HTTP a HTTPS (PR-RNF05-04)
curl -sI http://gestorsqa.westus2.cloudapp.azure.com/ | head -3
# Salida obtenida:
# HTTP/1.1 308 Permanent Redirect
# Connection: close
# Location: https://gestorsqa.westus2.cloudapp.azure.com/

# 3. Cookie CSRF con atributo Secure sobre HTTPS (PR-RNF05-04)
curl -sI https://gestorsqa.westus2.cloudapp.azure.com/api/auth/csrf/ | grep -i set-cookie
# Salida obtenida:
# set-cookie: csrftoken=...; Path=/; SameSite=Lax; Secure
```

## 7. Respaldos y restauración (`PR-OPS-01`)

### Crear un respaldo

```bash
cd ~/GestorSQA
./respaldo.sh
```

Genera un volcado comprimido en `respaldos/gestorsqa-AAAAMMDD-HHMMSS.sql.gz` y puede copiarse fuera de la VM mediante `scp`:

```bash
scp -i ~/.ssh/gestorsqa-key.pem azureuser@gestorsqa.westus2.cloudapp.azure.com:GestorSQA/respaldos/<archivo> .
```

### Restaurar un respaldo

```bash
cd ~/GestorSQA
./restaurar.sh respaldos/gestorsqa-AAAAMMDD-HHMMSS.sql.gz
```
