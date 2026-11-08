"""
TWL Obras — app Streamlit.

Fluxo:
    Login (Google OAuth) --> Verificação de Perfil (Google Sheets) -->
    Dashboard (obras ativas) --> Painel de obra --> Gerador de RDO

Navegação implementada via st.session_state (sem multipage nativo), para
poder passar a obra selecionada entre "páginas" sem depender de query params.
"""
from datetime import date, datetime
import os
from zoneinfo import ZoneInfo

import streamlit as st

LISBOA = ZoneInfo("Europe/Lisbon")

from services import drive, sheets
from services.pdf_generator import generate_rdo_pdf

st.set_page_config(page_title="TWL Obras", page_icon="⬛", layout="wide")

# ---------------------------------------------------------------------------
# Estilo — clean, minimalista, preto/branco/cinza (Identidade TWL)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&display=swap');
        
        html, body, [class*="css"], .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #ffffff;
            color: #000000;
        }
        
        h1, h2, h3 {
            font-family: 'Playfair Display', Georgia, serif;
            font-weight: 400;
            color: #000000;
        }
        
        /* Botões em formato Pílula (Pill Buttons) */
        div.stButton > button {
            border-radius: 9999px !important;
            height: 44px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 0.5rem 1.5rem !important;
            transition: all 0.2s ease !important;
            box-shadow: none !important;
        }
        
        /* Botão Primário — Preto sólido */
        div.stButton > button[kind="primary"] {
            background-color: #010101 !important;
            color: #ffffff !important;
            border: 1px solid #010101 !important;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #222222 !important;
            color: #ffffff !important;
            border-color: #222222 !important;
        }
        
        /* Botão Secundário — Cinzento suave */
        div.stButton > button[kind="secondary"] {
            background-color: #e6e6e6 !important;
            color: #000000 !important;
            border: 1px solid #e6e6e6 !important;
        }
        div.stButton > button[kind="secondary"]:hover {
            background-color: #d8d8d8 !important;
            color: #000000 !important;
            border-color: #d8d8d8 !important;
        }
        
        .obra-card {
            border: 1px solid #e2e2e2;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Estado de navegação
# ---------------------------------------------------------------------------
st.session_state.setdefault("view", "dashboard")
st.session_state.setdefault("selected_obra", None)
st.session_state.setdefault("rdo_photos", [])
st.session_state.setdefault("camera_shot_count", 0)


def go_to(view, obra=None):
    st.session_state.view = view
    if obra is not None:
        st.session_state.selected_obra = obra
    st.rerun()


def build_referencia(iniciais, codigo_obra, data_rdo):
    base = f"{iniciais}_{codigo_obra}_{data_rdo.strftime('%d_%m_%Y')}"
    existentes = drive.list_referencias(codigo_obra)
    ref, n = base, 2
    while ref in existentes:
        ref = f"{base}_v{n}"
        n += 1
    return ref


# ---------------------------------------------------------------------------
# Autenticação e Perfis
# ---------------------------------------------------------------------------
def check_authentication():
    """
    Verifica se o utilizador está autenticado via Google (st.login) e
    se possui um perfil ativo e autorizado na folha 'Utilizadores'.
    """
    has_auth_config = "auth" in st.secrets

    if has_auth_config:
        is_logged_in = getattr(st.user, "is_logged_in", False)
        if not is_logged_in:
            return None, "login_required"
        user_email = getattr(st.user, "email", None)
        user_name = getattr(st.user, "name", None) or (user_email.split("@")[0] if user_email else "")
    else:
        # Fallback de desenvolvimento local se [auth] ainda não estiver em secrets.toml
        user_email = "guilhermeleal.me@gmail.com"
        user_name = "Guilherme Leal"

    profile = sheets.get_user_profile(user_email)
    if not profile:
        return {"email": user_email, "name": user_name}, "access_requested"

    return profile, "authorized"


def view_login():
    # Centralização responsiva (Mobile-first, max-width 390px centrado em telas maiores)
    _, col_center, _ = st.columns([1, 1.6, 1])
    with col_center:
        # Topo: Logo TWL alinhado à esquerda
        logo_path = "assets/vector/logo_black.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=95)

        # Espaçamento vertical generoso (fidelidade ao canvas Inkscape)
        st.markdown("<div style='height: 180px;'></div>", unsafe_allow_html=True)

        # Título "Bem vindo,"
        st.markdown(
            """
            <h1 style='font-family: "Playfair Display", Georgia, serif; 
                       font-size: 34px; 
                       font-weight: 400; 
                       color: #000000; 
                       margin-bottom: 24px; 
                       line-height: 1.15;
                       letter-spacing: -0.5px;'>
                Bem vindo,
            </h1>
            """,
            unsafe_allow_html=True,
        )

        # Botão Primário: "Entre com a sua conta Google"
        if st.button("Entre com a sua conta Google", type="primary", use_container_width=True, key="btn_login_google"):
            st.login()

        # Botão Secundário: "Cadastre-se"
        if st.button("Cadastre-se", key="btn_cadastre_se", type="secondary", use_container_width=True):
            st.session_state["show_cadastro_info"] = not st.session_state.get("show_cadastro_info", False)

        if st.session_state.get("show_cadastro_info"):
            st.info("Para solicitar o seu cadastro, clique em **Entre com a sua conta Google**. O seu pedido será enviado automaticamente para aprovação do Administrador.")
            if st.button("Avançar para Login Google", type="primary", use_container_width=True, key="btn_cad_login"):
                st.login()

        # Rodapé com assinatura institucional
        st.markdown(
            """
            <p style='font-family: "Inter", sans-serif; 
                      font-size: 9px; 
                      color: #a1a1a1; 
                      text-align: center; 
                      margin-top: 55px; 
                      margin-bottom: 20px;
                      letter-spacing: 0.2px;'>
                TWL Portugal - Engenharia e Construção
            </p>
            """,
            unsafe_allow_html=True,
        )


def view_pedido_acesso(user_info):
    email = user_info.get("email", "")
    nome = user_info.get("name", "")

    _, col_center, _ = st.columns([1, 1.6, 1])
    with col_center:
        logo_path = "assets/vector/logo_black.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=95)

        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <h1 style='font-family: "Playfair Display", Georgia, serif; font-size: 28px; font-weight: 400; color: #000000; margin-bottom: 12px;'>
                Acesso Pendente
            </h1>
            """,
            unsafe_allow_html=True,
        )
        st.warning(f"Olá **{nome}**! A tua conta Google (**{email}**) ainda não se encontra autorizada no TWL Obras.")
        st.caption("Para teres acesso ao portal, envia a tua solicitação para que o administrador possa ativar o teu perfil.")

        with st.form("form_pedido"):
            motivo = st.text_input("Cargo / Função", placeholder="Ex: Engenheiro de Obra, Encarregado...")
            contacto = st.text_input("Contacto telefónico", placeholder="Ex: (+351) 912 345 678")
            enviado = st.form_submit_button("Enviar Pedido de Acesso", type="primary", use_container_width=True)
            if enviado:
                ok, msg = sheets.registrar_pedido_acesso(email, nome, motivo, contacto)
                if ok:
                    st.success("O teu pedido foi submetido! O administrador irá ativar o teu perfil.")
                else:
                    st.info(msg)

        st.markdown("<br>", unsafe_allow_html=True)
        if hasattr(st, "logout") and getattr(st.user, "is_logged_in", False):
            if st.button("Terminar sessão / Mudar de conta", type="secondary", use_container_width=True):
                st.logout()

        st.markdown(
            """
            <p style='font-family: "Inter", sans-serif; 
                      font-size: 9px; 
                      color: #a1a1a1; 
                      text-align: center; 
                      margin-top: 40px; 
                      margin-bottom: 20px;
                      letter-spacing: 0.2px;'>
                TWL Portugal - Engenharia e Construção
            </p>
            """,
            unsafe_allow_html=True,
        )


def render_user_header(profile):
    c_info, c_out = st.columns([8, 2])
    with c_info:
        badge = "👑 Admin" if profile.get("role") == "admin" else "👷 Colaborador"
        st.caption(f"Sessão iniciada como **{profile.get('nome')}** ({profile.get('email')}) — {badge}")
    with c_out:
        if hasattr(st, "logout") and getattr(st.user, "is_logged_in", False):
            if st.button("Terminar sessão", key="btn_logout", use_container_width=True):
                st.logout()


# ---------------------------------------------------------------------------
# Vista 1 — Dashboard
# ---------------------------------------------------------------------------
def view_dashboard(profile):
    render_user_header(profile)
    st.title("Obras")

    # Notificações e Aprovação de Acessos para Administradores
    if profile.get("role") == "admin":
        pedidos = sheets.get_pedidos_acesso()
        if pedidos:
            with st.expander(f"🔔 Pedidos de Acesso Pendentes ({len(pedidos)})", expanded=True):
                st.write("Colaboradores que solicitaram acesso recentemente:")
                for i, p in enumerate(pedidos):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
                    with c1:
                        st.markdown(f"**{p.get('nome', '')}**<br><small>{p.get('email', '')}</small>", unsafe_allow_html=True)
                        if p.get("motivo"):
                            st.caption(f"Função: {p.get('motivo')}")
                        if p.get("contacto"):
                            st.caption(f"Contacto: {p.get('contacto')}")
                    with c2:
                        role_sel = st.selectbox(
                            "Perfil",
                            ["funcionario", "admin"],
                            format_func=lambda x: "👷 Funcionário" if x == "funcionario" else "👑 Administrador",
                            key=f"role_sel_{i}",
                        )
                    with c3:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("✅ Aprovar", key=f"aprov_{i}", type="primary", use_container_width=True):
                            with st.spinner("A aprovar acesso..."):
                                sheets.aprovar_pedido_acesso(p["email"], p.get("nome", ""), role_sel)
                            st.success(f"{p['email']} aprovado como {role_sel}!")
                            st.rerun()
                    with c4:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("Recusar", key=f"rej_{i}", use_container_width=True):
                            with st.spinner("A recusar..."):
                                sheets.rejeitar_pedido_acesso(p["email"])
                            st.info(f"Pedido de {p['email']} recusado.")
                            st.rerun()
                    st.divider()

    obras = sheets.get_obras()
    if not obras:
        st.info("Sem obras ativas na sheet 'Obras' (ou a coluna 'estado' não tem nenhuma linha = 'ativa').")
        return

    cols = st.columns(3)
    for i, obra in enumerate(obras):
        with cols[i % 3]:
            with st.container(border=True):
                if obra.get("capa_file_id"):
                    st.image(drive.download_file_bytes(obra["capa_file_id"]), use_container_width=True)
                st.subheader(obra["nome_obra"])
                st.caption(obra["codigo_obra"])
                pct = int(obra.get("percentagem", 0) or 0)
                st.progress(pct / 100, text=f"{pct}% completo")
                if st.button("Abrir obra", key=f"open_{obra['id_obra']}", use_container_width=True):
                    go_to("painel", obra)


# ---------------------------------------------------------------------------
# Vista 2 — Painel de obra
# ---------------------------------------------------------------------------
def view_painel(profile):
    render_user_header(profile)
    obra = st.session_state.selected_obra
    if st.button("← Voltar às obras"):
        go_to("dashboard")

    if obra.get("capa_file_id"):
        st.image(drive.download_file_bytes(obra["capa_file_id"]), use_container_width=True)

    st.title(obra["nome_obra"])
    st.caption(obra.get("localizacao", ""))
    st.write(obra.get("descricao_curta", ""))

    if st.button("Gerar RDO", type="primary"):
        st.session_state.rdo_photos = []
        go_to("gerar_rdo")


# ---------------------------------------------------------------------------
# Vista 3 — Gerador de RDO
# ---------------------------------------------------------------------------
def view_gerar_rdo(profile):
    render_user_header(profile)
    obra = st.session_state.selected_obra
    if st.button("← Voltar ao painel de obra"):
        go_to("painel")

    st.title(f"Gerar RDO — {obra['nome_obra']}")

    responsaveis = sheets.get_responsaveis()
    if not responsaveis:
        st.error("Sem responsáveis ativos na sheet 'Responsaveis'.")
        return
    nomes = [r["nome_completo"] for r in responsaveis]

    # Para funcionários, tenta pré-selecionar o responsável pelo nome
    default_idx = 0
    if profile.get("role") == "funcionario":
        for idx, r in enumerate(responsaveis):
            if (
                profile.get("nome", "").strip().lower() in r["nome_completo"].strip().lower()
                or r["nome_completo"].strip().lower() in profile.get("nome", "").strip().lower()
            ):
                default_idx = idx
                break

    resp_nome = st.selectbox("Responsável", nomes, index=default_idx)
    resp = next(r for r in responsaveis if r["nome_completo"] == resp_nome)

    resumo = st.text_area("Resumo das atividades realizadas", height=120,
                           placeholder="Ex: Continuação dos trabalhos de pintura, acabamentos...")
    data_rdo = st.date_input("Data", value=date.today())

    st.subheader("Fotografias")
    tab_upload, tab_camera = st.tabs(["📁 Carregar do dispositivo", "📷 Tirar fotografia"])

    with tab_upload:
        uploaded = st.file_uploader(
            "Escolhe uma ou mais fotos", type=["jpg", "jpeg", "png"], accept_multiple_files=True
        )
        if uploaded:
            existentes = {p["name"] for p in st.session_state.rdo_photos}
            for f in uploaded:
                if f.name not in existentes:
                    st.session_state.rdo_photos.append({"name": f.name, "bytes": f.getvalue(), "legenda": ""})

    with tab_camera:
        shot = st.camera_input("Tirar foto", key=f"cam_{st.session_state.camera_shot_count}")
        if shot is not None:
            st.session_state.rdo_photos.append({
                "name": f"foto_{len(st.session_state.rdo_photos) + 1}.jpg",
                "bytes": shot.getvalue(),
                "legenda": "",
            })
            st.session_state.camera_shot_count += 1
            st.rerun()
        st.caption("Depois de tirares a foto, este espaço reaparece para tirares a seguinte.")

    if st.session_state.rdo_photos:
        st.divider()
        st.caption(f"{len(st.session_state.rdo_photos)} foto(s) — adiciona uma legenda a cada uma")
        to_delete = None
        for i, p in enumerate(st.session_state.rdo_photos):
            c1, c2, c3 = st.columns([1, 3, 0.6])
            with c1:
                st.image(p["bytes"], width=90)
            with c2:
                p["legenda"] = st.text_input("Legenda", value=p["legenda"], key=f"legenda_{i}",
                                              label_visibility="collapsed", placeholder="Legenda da foto")
            with c3:
                if st.button("Remover", key=f"del_{i}"):
                    to_delete = i
        if to_delete is not None:
            st.session_state.rdo_photos.pop(to_delete)
            st.rerun()

    st.divider()
    pronto = bool(resumo) and len(st.session_state.rdo_photos) > 0
    if st.button("Gerar RDO", type="primary", disabled=not pronto, use_container_width=True):
        with st.spinner("A gerar o PDF e a guardar na Drive..."):
            referencia = build_referencia(resp["iniciais"], obra["codigo_obra"], data_rdo)
            obra_pdf = dict(obra)
            if obra.get("capa_file_id"):
                obra_pdf["capa_bytes"] = drive.download_file_bytes(obra["capa_file_id"])

            pdf_bytes = generate_rdo_pdf(
                obra=obra_pdf,
                rdo={
                    "data": data_rdo.strftime("%d/%m/%Y"),
                    "hora": datetime.now(LISBOA).strftime("%H:%M"),
                    "referencia": referencia,
                    "resumo": resumo,
                    "responsavel_nome": resp["nome_completo"],
                    "responsavel_contacto": resp["contacto"],
                },
                photos=st.session_state.rdo_photos,
            )

            drive.save_rdo_pdf(obra["codigo_obra"], referencia, pdf_bytes)
            drive.save_rdo_photos(obra["codigo_obra"], data_rdo.isoformat(), st.session_state.rdo_photos)
            sheets.log_rdo(obra["id_obra"], data_rdo.isoformat(), resp["nome_completo"], referencia)

        st.success(f"RDO gerado e guardado na Drive: {referencia}.pdf")
        st.download_button("Descarregar PDF", data=pdf_bytes, file_name=f"{referencia}.pdf",
                            mime="application/pdf", use_container_width=True)


# ---------------------------------------------------------------------------
# Router Principal
# ---------------------------------------------------------------------------
profile, auth_status = check_authentication()

if auth_status == "login_required":
    view_login()
elif auth_status == "access_requested":
    view_pedido_acesso(profile)
else:
    VIEWS = {
        "dashboard": view_dashboard,
        "painel": view_painel,
        "gerar_rdo": view_gerar_rdo,
    }
    VIEWS[st.session_state.view](profile)
