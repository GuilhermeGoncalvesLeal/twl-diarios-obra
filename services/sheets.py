"""
Acesso ao Google Sheets — base de dados da app (obras, responsáveis, histórico de RDOs).

Espera em st.secrets:
    [gcp_service_account]   -> JSON da service account (Sheets API + Drive API ativas)
    [twl]
    spreadsheet_id = "..."  -> ID da spreadsheet "TWL_Obras" (está na URL da folha)

Estrutura esperada da spreadsheet (ver README.md para o passo a passo de criação):

  Separador "Obras"
    id_obra | nome_obra | codigo_obra | localizacao | percentagem | descricao_curta | capa_file_id | estado

  Separador "Responsaveis"
    nome_completo | iniciais | contacto | ativo

  Separador "RDOs"  (histórico — a app escreve aqui, não precisas de preencher à mão)
    id_obra | data | responsavel | referencia
"""
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def _client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)


def _spreadsheet():
    return _client().open_by_key(st.secrets["twl"]["spreadsheet_id"])


@st.cache_data(ttl=60)
def get_obras():
    """Devolve só as obras com estado == 'ativa'."""
    ws = _spreadsheet().worksheet("Obras")
    registos = ws.get_all_records()
    return [r for r in registos if str(r.get("estado", "")).strip().lower() == "ativa"]


@st.cache_data(ttl=60)
def get_responsaveis():
    ws = _spreadsheet().worksheet("Responsaveis")
    registos = ws.get_all_records()
    return [r for r in registos if str(r.get("ativo", "")).strip().lower() in ("true", "sim", "1", "verdadeiro")]


def log_rdo(id_obra, data_iso, responsavel, referencia):
    """Regista o RDO gerado no separador de histórico."""
    ws = _spreadsheet().worksheet("RDOs")
    ws.append_row([id_obra, data_iso, responsavel, referencia])


def clear_cache():
    """Chamar depois de qualquer alteração manual na sheet, para forçar refresh."""
    get_obras.clear()
    get_responsaveis.clear()
