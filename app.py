"""
TWL Obras — app Streamlit.

Fluxo:
    Dashboard (obras ativas)  -->  Painel de obra  -->  Gerador de RDO

Navegação implementada via st.session_state (sem multipage nativo), para
poder passar a obra selecionada entre "páginas" sem depender de query params.
"""
from datetime import date, datetime

import streamlit as st

from services import drive, sheets
from services.pdf_generator import generate_rdo_pdf

st.set_page_config(page_title="TWL Obras", page_icon="⬛", layout="wide")

# ---------------------------------------------------------------------------
# Estilo — clean, minimalista, preto/branco/cinza
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=Playfair+Display&display=swap');
        html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
        h1, h2, h3 { font-family: 'Playfair Display', serif; font-weight: 400; }
        div.stButton > button {
            border-radius: 0; border: 1px solid #111; background: #fff; color: #111;
        }
        div.stButton > button:hover { background: #111; color: #fff; }
        div.stButton > button[kind="primary"] { background: #111; color: #fff; border: 1px solid #111; }
        .obra-card { border: 1px solid #e2e2e2; padding: 1rem; margin-bottom: 1rem; }
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
# Vista 1 — Dashboard
# ---------------------------------------------------------------------------
def view_dashboard():
    st.title("Obras")
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
def view_painel():
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
def view_gerar_rdo():
    obra = st.session_state.selected_obra
    if st.button("← Voltar ao painel de obra"):
        go_to("painel")

    st.title(f"Gerar RDO — {obra['nome_obra']}")

    responsaveis = sheets.get_responsaveis()
    if not responsaveis:
        st.error("Sem responsáveis ativos na sheet 'Responsaveis'.")
        return
    nomes = [r["nome_completo"] for r in responsaveis]
    resp_nome = st.selectbox("Responsável", nomes)
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
                    "hora": datetime.now().strftime("%H:%M"),
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
# Router
# ---------------------------------------------------------------------------
VIEWS = {"dashboard": view_dashboard, "painel": view_painel, "gerar_rdo": view_gerar_rdo}
VIEWS[st.session_state.view]()
