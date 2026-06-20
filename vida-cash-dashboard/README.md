# Dashboard Vida Cash

Streamlit app deployada en Streamlit Community Cloud. Lee `Leads.xlsx` y
`Ventas.xlsx` desde una carpeta de Google Drive y muestra el análisis de
funnel / PxQ / cascada. Para actualizar los datos, Carlos reemplaza los
archivos en Drive — sin tocar código ni reiniciar nada.

---

## Setup inicial (una sola vez)

### 1. Crear proyecto en Google Cloud y habilitar la Drive API

1. Ve a [Google Cloud Console](https://console.cloud.google.com/) → **New Project**.
2. Dentro del proyecto, ve a **APIs & Services → Library**.
3. Busca **Google Drive API** y haz clic en **Enable**.

### 2. Crear la Service Account y descargar credenciales

1. Ve a **APIs & Services → Credentials → Create Credentials → Service Account**.
2. Dale un nombre (ej. `vida-cash-dashboard`) y crea la cuenta.
3. En la lista de Service Accounts, haz clic en la que acabas de crear.
4. Ve a la pestaña **Keys → Add Key → Create new key → JSON**.
5. Descarga el archivo `.json` — lo necesitarás en el paso 4.

### 3. Compartir la carpeta de Drive con la Service Account

1. En Google Drive, navega a la carpeta donde están `Leads.xlsx` y `Ventas.xlsx`.
2. Haz clic derecho en la carpeta → **Share**.
3. Pega el email de la Service Account (lo ves en el JSON, campo `client_email`,
   algo como `vida-cash-dashboard@proyecto.iam.gserviceaccount.com`).
4. Dale permiso de **Viewer** y confirma.
5. Copia el **ID de la carpeta** desde la URL de Drive:
   `https://drive.google.com/drive/folders/<FOLDER_ID>` ← este es el `folder_id`.

### 4. Configurar los secrets en Streamlit Cloud

1. Ve a tu app en [share.streamlit.io](https://share.streamlit.io) → **Settings → Secrets**.
2. Pega el contenido siguiente, reemplazando los valores con los reales:

```toml
[app]
password = "tu-contraseña-segura"

[drive]
folder_id = "1AbCdEfGhIjKlMnOpQrStUvWxYz"

[gcp_service_account]
type = "service_account"
project_id = "mi-proyecto-123"
private_key_id = "abc123..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "dashboard@mi-proyecto-123.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/dashboard%40mi-proyecto-123.iam.gserviceaccount.com"
```

> **Importante:** los valores del bloque `[gcp_service_account]` se copian
> directamente del JSON descargado en el paso 2 — cada campo del JSON es una
> clave del bloque. El `private_key` debe tener los saltos de línea como `\n`
> (Streamlit los maneja automáticamente si lo pegas en la UI).

> **Nunca** subas el archivo `.json` ni un `secrets.toml` con credenciales
> reales al repositorio de GitHub.

### 5. Conectar el repo a Streamlit Community Cloud y deployar

1. Ve a [share.streamlit.io](https://share.streamlit.io) → **New app**.
2. Selecciona el repo de GitHub (`taghere123/helloworld`) y la rama `main`.
3. En **Main file path** pon: `vida-cash-dashboard/app.py`
4. Haz clic en **Deploy** — el deploy es automático en cada push a `main`.

---

## Uso diario

- **Actualizar datos:** reemplaza `Leads.xlsx` o `Ventas.xlsx` en la carpeta
  de Drive (mismo nombre de archivo). El dashboard se refresca solo en ≤ 10 min.
  Para forzar recarga inmediata, usa el botón **🔄 Recargar ahora** en el sidebar.
- **Compartir acceso:** comparte la URL de Streamlit con las 7 personas del
  equipo. La contraseña configurada en secrets protege el acceso.

---

## Estructura del proyecto

```
vida-cash-dashboard/
  app.py                         # Punto de entrada de Streamlit
  requirements.txt
  README.md
  .streamlit/
    secrets.toml.example         # Plantilla de secrets (sin datos reales)
  modules/
    drive_loader.py              # Descarga archivos desde Google Drive
    data_loader.py               # Parsea y valida los DataFrames
    funnel.py                    # Tablas de funnel mensual
    combinaciones.py             # Análisis PRE/POST por combinación
    insights.py                  # Motor de insights basado en reglas
```
