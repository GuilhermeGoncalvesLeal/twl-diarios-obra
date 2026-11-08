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
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

LISBOA = ZoneInfo("Europe/Lisbon")

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


def _get_or_create_worksheet(title, headers, default_rows=None):
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=100, cols=len(headers))
        ws.update("A1", [headers])
        if default_rows:
            for row in default_rows:
                ws.append_row(row)
    return ws


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


@st.cache_data(ttl=60)
def get_utilizadores():
    """Lê os utilizadores autorizados a partir da folha 'Utilizadores'."""
    ws = _get_or_create_worksheet(
        "Utilizadores",
        ["email", "nome", "role", "ativo"],
        default_rows=[
            ["guilhermeleal.me@gmail.com", "Guilherme Leal", "admin", "sim"]
        ],
    )
    registos = ws.get_all_records()
    return [r for r in registos if str(r.get("ativo", "")).strip().lower() in ("true", "sim", "1", "verdadeiro")]


def get_user_profile(email: str):
    """Devolve o perfil do utilizador (admin/funcionario) se autorizado, ou None."""
    if not email:
        return None
    utilizadores = get_utilizadores()
    target = email.strip().lower()
    for u in utilizadores:
        if str(u.get("email", "")).strip().lower() == target:
            return {
                "email": u.get("email", "").strip(),
                "nome": u.get("nome", "").strip() or email.split("@")[0].capitalize(),
                "role": str(u.get("role", "funcionario")).strip().lower(),
                "ativo": True,
            }
    return None


def registrar_pedido_acesso(email: str, nome: str = "", motivo: str = "", contacto: str = ""):
    """Regista uma solicitação de acesso para avaliação do Administrador."""
    ws = _get_or_create_worksheet(
        "Pedidos_Acesso",
        ["data_pedido", "email", "nome", "motivo", "contacto", "estado"],
    )
    registos = ws.get_all_records()
    for r in registos:
        if (
            str(r.get("email", "")).strip().lower() == email.strip().lower()
            and str(r.get("estado", "")).strip().lower() == "pendente"
        ):
            return False, "Já existe um pedido pendente para este email."

    agora = datetime.now(LISBOA).strftime("%d/%m/%Y %H:%M")
    ws.append_row([agora, email.strip(), nome.strip(), motivo.strip(), contacto.strip(), "pendente"])
    get_pedidos_acesso.clear()
    return True, "Pedido registado com sucesso."


@st.cache_data(ttl=60)
def get_pedidos_acesso():
    """Lê os pedidos de acesso pendentes."""
    ws = _get_or_create_worksheet(
        "Pedidos_Acesso",
        ["data_pedido", "email", "nome", "motivo", "contacto", "estado"],
    )
    registos = ws.get_all_records()
    return [r for r in registos if str(r.get("estado", "")).strip().lower() == "pendente"]


def aprovar_pedido_acesso(email: str, nome: str, role: str = "funcionario"):
    """Aprova um pedido de acesso: adiciona a Utilizadores e atualiza o pedido."""
    sh = _spreadsheet()
    ws_pedidos = _get_or_create_worksheet(
        "Pedidos_Acesso",
        ["data_pedido", "email", "nome", "motivo", "contacto", "estado"],
    )
    ws_users = _get_or_create_worksheet(
        "Utilizadores",
        ["email", "nome", "role", "ativo"],
    )

    # 1. Adicionar ou reativar em Utilizadores
    users_records = ws_users.get_all_records()
    found_row = None
    for idx, u in enumerate(users_records, start=2):
        if str(u.get("email", "")).strip().lower() == email.strip().lower():
            found_row = idx
            break

    if found_row:
        ws_users.update_cell(found_row, 3, role)
        ws_users.update_cell(found_row, 4, "sim")
    else:
        ws_users.append_row([email.strip().lower(), nome.strip(), role, "sim"])

    # 2. Atualizar estado em Pedidos_Acesso para 'aprovado'
    pedidos_records = ws_pedidos.get_all_records()
    for idx, p in enumerate(pedidos_records, start=2):
        if (
            str(p.get("email", "")).strip().lower() == email.strip().lower()
            and str(p.get("estado", "")).strip().lower() == "pendente"
        ):
            ws_pedidos.update_cell(idx, 6, "aprovado")
            break

    clear_cache()
    return True


def rejeitar_pedido_acesso(email: str):
    """Marca o pedido de acesso como rejeitado."""
    ws_pedidos = _get_or_create_worksheet(
        "Pedidos_Acesso",
        ["data_pedido", "email", "nome", "motivo", "contacto", "estado"],
    )
    pedidos_records = ws_pedidos.get_all_records()
    for idx, p in enumerate(pedidos_records, start=2):
        if (
            str(p.get("email", "")).strip().lower() == email.strip().lower()
            and str(p.get("estado", "")).strip().lower() == "pendente"
        ):
            ws_pedidos.update_cell(idx, 6, "rejeitado")
            break

    clear_cache()
    return True


def clear_cache():
    """Chamar depois de qualquer alteração manual na sheet, para forçar refresh."""
    get_obras.clear()
    get_responsaveis.clear()
    get_utilizadores.clear()
    get_pedidos_acesso.clear()
