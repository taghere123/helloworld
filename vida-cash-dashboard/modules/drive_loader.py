"""
Google Drive loader.

Downloads Leads.xlsx and Ventas.xlsx from a shared Drive folder using a
Service Account.  Credentials and folder_id come from st.secrets — nothing
is hardcoded or stored in the repo.

Expected secrets.toml structure:
    [drive]
    folder_id = "1AbCdEf..."

    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----\\n"
    client_email = "dashboard@project.iam.gserviceaccount.com"
    client_id = "..."
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "..."
"""
from __future__ import annotations

import io

import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _build_service():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=_SCOPES,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_file(service, folder_id: str, filename: str) -> dict | None:
    """Return first matching file metadata or None."""
    q = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    result = (
        service.files()
        .list(
            q=q,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=1,
        )
        .execute()
    )
    files = result.get("files", [])
    return files[0] if files else None


def _download_bytes(service, file_id: str) -> bytes:
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


@st.cache_data(ttl=600, show_spinner="Leyendo archivos desde Google Drive…")
def load_from_drive() -> tuple[bytes, bytes, str, str]:
    """
    Download both Excel files from Drive and return raw bytes + ISO-8601
    modifiedTime strings.  Cached for 10 minutes.  Call
    st.cache_data.clear() to force an immediate refresh.
    """
    folder_id: str = st.secrets["drive"]["folder_id"]

    try:
        service = _build_service()
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo autenticar con Google Drive. "
            f"Verifica las credenciales en st.secrets. Detalle: {exc}"
        ) from exc

    leads_meta = _find_file(service, folder_id, "Leads.xlsx")
    if leads_meta is None:
        raise FileNotFoundError(
            "Leads.xlsx no encontrado en la carpeta de Drive. "
            "Verifica que el archivo exista y que el folder_id sea correcto."
        )

    ventas_meta = _find_file(service, folder_id, "Ventas.xlsx")
    if ventas_meta is None:
        raise FileNotFoundError(
            "Ventas.xlsx no encontrado en la carpeta de Drive. "
            "Verifica que el archivo exista y que el folder_id sea correcto."
        )

    leads_bytes = _download_bytes(service, leads_meta["id"])
    ventas_bytes = _download_bytes(service, ventas_meta["id"])

    return (
        leads_bytes,
        ventas_bytes,
        leads_meta["modifiedTime"],
        ventas_meta["modifiedTime"],
    )
