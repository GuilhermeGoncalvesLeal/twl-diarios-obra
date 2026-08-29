"""
Acesso ao Google Drive — imagens de capa das obras, e armazenamento dos PDFs
de RDO gerados.

IMPORTANTE: usa autenticação OAuth do UTILIZADOR (não a conta de serviço).
Contas de serviço têm 0 bytes de quota própria no Drive, por isso qualquer
upload de ficheiro binário (fotos, PDFs) falha com "storageQuotaExceeded" —
isto é uma limitação do Google, não um bug. Como a tua conta é Gmail pessoal
(sem Shared Drives), a forma correta é a app escrever em teu nome. Ver
get_oauth_refresh_token.py para gerar as credenciais uma única vez.

Espera em st.secrets:
    [gcp_oauth_user]
    client_id = "..."
    client_secret = "..."
    refresh_token = "..."

    [twl]
    drive_root_folder_id = "..." -> ID da pasta "TWL_Obras" no teu Drive

Como agora é a tua própria conta a escrever, já NÃO precisas de partilhar a
pasta TWL_Obras com nenhuma conta de serviço — é simplesmente tua.

Organização criada automaticamente pela app dentro da pasta raiz:

    TWL_Obras/
      <codigo_obra>/
        fotos_rdo/<data>/       <- fotos brutas enviadas nesse RDO
        relatorios_pdf/         <- PDFs gerados (nome = <referencia>.pdf)
"""
import io

import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


@st.cache_resource
def _service():
    creds = Credentials(
        None,
        refresh_token=st.secrets["gcp_oauth_user"]["refresh_token"],
        client_id=st.secrets["gcp_oauth_user"]["client_id"],
        client_secret=st.secrets["gcp_oauth_user"]["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds)


@st.cache_data(ttl=300)
def download_file_bytes(file_id: str) -> bytes:
    """Descarrega um ficheiro (ex: imagem de capa) diretamente pela API."""
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
