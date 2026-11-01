# Evidencia de Preparación de Despliegue (SQAP 5.1.4 / SDS Sección 5)

**Fecha:** 1 de noviembre de 2026  
**Responsable:** Oliver Germain Saldivar Elizalde  

## 1. Especificaciones del Host (Azure for Students)
* **Proveedor:** Microsoft Azure
* **Sistema Operativo:** Ubuntu Server 24.04 LTS (x64 Gen2)
* **Tamaño de VM:** Standard_B2als_v2 (2 vCPU, 4 GiB RAM)
* **Autenticación:** Exclusivamente mediante par de claves SSH
* **Nombre DNS asignado:** `gestorsqa.westus2.cloudapp.azure.com`

<img width="1100" height="728" alt="Screenshot 2026-11-01 152511" src="https://github.com/user-attachments/assets/c72d66c5-35d1-413a-bfec-6c5968ee8621" />

## 2. Seguridad de Red y Presupuesto
* **Grupo de Seguridad de Red (NSG):**
  * Puerto `80/TCP` (HTTP) y `443/TCP` (HTTPS): Abiertos (`Cualquiera`).
  * Puerto `22/TCP` (SSH): Restringido a mi IP pública (`187.241.241.116`).
* **Control de costos:** Alerta de presupuesto configurada en 50 USD mensuales (alertas al 50% y 80%).

<img width="1542" height="640" alt="Screenshot 2026-11-01 154005" src="https://github.com/user-attachments/assets/cf5fc82c-f89e-4a8d-8e66-dff9247cc232" />

<img width="1347" height="662" alt="Screenshot 2026-11-01 154326" src="https://github.com/user-attachments/assets/ced8dd29-d3eb-42d2-a689-bc4bd68c9cdd" />

<img width="1392" height="803" alt="image" src="https://github.com/user-attachments/assets/cd674fe1-00bb-4ed4-bca7-dbebeec2373b" />

## 3. Aprovisionamiento del Servidor (Docker y Swap)
Comandos ejecutados en la VM por SSH para instalar Docker y configurar 2 GB de memoria swap:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

<img width="1097" height="317" alt="Screenshot 2026-11-01 170532" src="https://github.com/user-attachments/assets/44ae4d57-893d-47fa-9bbf-39554f1fd7c7" />

## 4. Prueba de Humo
Validación de construcción de la imagen en dos etapas desde la rama `infra-esqueleto`:

```bash
git clone -b infra-esqueleto https://github.com/RubenAmauri/GestorSQA && cd GestorSQA
docker build -t gestor-sqa .
```

<img width="873" height="135" alt="Screenshot 2026-11-01 171051" src="https://github.com/user-attachments/assets/8ef2441e-b35e-4643-84a5-f1f0fc079354" />
