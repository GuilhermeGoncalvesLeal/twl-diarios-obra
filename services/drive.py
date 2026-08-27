"""
Acesso ao Google Drive — imagens de capa das obras, e armazenamento dos PDFs
de RDO gerados.

Espera em st.secrets:
    [gcp_service_account]   -> mesmo JSON usado em sheets.py
    [twl]
    drive_root_folder_id = "..." -> ID da pasta raiz "TWL_Obras" no Drive

IMPORTANTE: a pasta raiz (e a spreadsheet, em sheets.py) têm de estar
partilhadas com o "client_email" da service account (permissão de Editor),
senão a API devolve 404/403.

Organização criada automaticamente pela app dentro da pasta raiz:

    TWL_Obras/
      <codigo_obra>/
        fotos_rdo/<data>/       <- fotos brutas enviadas nesse RDO
        relatorios_pdf/         <- PDFs gerados (nome = <referencia>.pdf)
"""
import io

import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


@st.cache_resource
def _service():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


@st.cache_data(ttl=300)
def download_file_bytes(file_id: str) -> bytes:
    """Descarrega um ficheiro (ex: imagem de capa) diretamente pela API —
    não depende do ficheiro estar público."""
    request = _service().files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def get_or_create_subfolder(parent_id: str, name: str) -> str:
    svc = _service()
    safe_name = name.replace("'", "\\'")
    q = (
        f"'{parent_id}' in parents and name='{safe_name}' "
        "and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    res = svc.files().list(q=q, fields="files(id,name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    folder = svc.files().create(body=meta, fields="id").execute()
    return folder["id"]


def _obra_folder(codigo_obra: str) -> str:
    root = st.secrets["twl"]["drive_root_folder_id"]
    return get_or_create_subfolder(root, codigo_obra)


def upload_bytes(data: bytes, filename: str, parent_id: str, mime_type: str) -> str:
    svc = _service()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
    meta = {"name": filename, "parents": [parent_id]}
    f = svc.files().create(body=meta, media_body=media, fields="id").execute()
    return f["id"]


def list_referencias(codigo_obra: str) -> list:
    """Nomes (sem extensão) de todos os RDOs já gerados para esta obra —
    usado para evitar colisão de referência no mesmo dia."""
    obra_folder = _obra_folder(codigo_obra)
    reports_folder = get_or_create_subfolder(obra_folder, "relatorios_pdf")
    svc = _service()
    q = f"'{reports_folder}' in parents and trashed=false"
    res = svc.files().list(q=q, fields="files(name)").execute()
    return [f["name"].rsplit(".", 1)[0] for f in res.get("files", [])]


def save_rdo_pdf(codigo_obra: str, referencia: str, pdf_bytes: bytes) -> str:
    obra_folder = _obra_folder(codigo_obra)
    reports_folder = get_or_create_subfolder(obra_folder, "relatorios_pdf")
    return upload_bytes(pdf_bytes, f"{referencia}.pdf", reports_folder, "application/pdf")


def save_rdo_photos(codigo_obra: str, data_iso: str, photos: list) -> list:
    """Guarda as fotos brutas usadas num RDO em fotos_rdo/<data>/. Devolve os file_ids."""
    obra_folder = _obra_folder(codigo_obra)
    fotos_folder = get_or_create_subfolder(obra_folder, "fotos_rdo")
    data_folder = get_or_create_subfolder(fotos_folder, data_iso)
    ids = []
    for i, photo in enumerate(photos):
        name = photo.get("name") or f"foto_{i+1}.jpg"
        ids.append(upload_bytes(photo["bytes"], name, data_folder, "image/jpeg"))
    return ids
