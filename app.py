import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
import base64
import os

# --- 1. CONFIGURAÇÕES BASE E ÍCONE TWL ---
icone_pagina = "🏢"
logo_b64 = ""
if os.path.exists("logo.png"):
    icone_pagina = Image.open("logo.png")
    with open("logo.png", "rb") as img_f:
        logo_b64 = base64.b64encode(img_f.read()).decode()

st.set_page_config(page_title="TWL - Portal de Obra", page_icon=icone_pagina, layout="wide")

if logo_b64:
    st.markdown(
        f"""
        <head>
            <link rel="apple-touch-icon" href="data:image/png;base64,{logo_b64}">
            <link rel="icon" type="image/png" href="data:image/png;base64,{logo_b64}">
        </head>
        """,
        unsafe_allow_html=True
    )

# --- 2. INJEÇÃO DE ESTILO CSS (INSPIRADO NO PINTEREST) ---
st.markdown("""
    <style>
    /* Esconder cabeçalho e rodapé do Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Fundo Global Cinza Claro */
    .stApp {
        background-color: #F2F4F7;
    }

    /* Títulos Principais mais modernos e pesados */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -1.5px !important;
        color: #111111 !important;
        margin-bottom: 0px !important;
    }
    h3 {
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
        color: #111111 !important;
    }

    /* Cartões de Métrica Arredondados e Brancos */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 24px;
        box-shadow: 0px 4px 16px rgba(0, 0, 0, 0.04);
    }
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #111111 !important;
    }

    /* Personalização do Cartão da Obra (usando a borda nativa do Streamlit) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 32px !important;
        border: none !important;
        box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.04) !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
    }

    /* Botões estilo Pílula (Escuros e Redondos) */
    .stButton > button {
        background-color: #161616 !important;
        color: #FFFFFF !important;
        border-radius: 40px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #333333 !important;
        transform: scale(1.02);
    }

    /* Barra de progresso preta fina */
    .stProgress > div > div > div > div {
        background-color: #161616;
        border-radius: 10px;
    }

    /* Imagens com cantos arredondados */
    img {
        border-radius: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. DADOS E LÓGICA (MANTIDO INTACTO) ---
IMAGEM_PLACEHOLDER = "https://images.unsplash.com/photo-1541888946425-d0fbb1861593?w=600&auto=format&fit=crop&q=80"
NOME_ABA = "Folha1"

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        df = conn.read(worksheet=NOME_ABA, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Código", "Obra", "Diretor", "Progresso", "Estado", "Imagem"])
        df["Código"] = df["Código"].fillna("SEM-COD").astype(str)
        df["Obra"] = df["Obra"].fillna("Obra sem nome").astype(str)
        df["Diretor"] = df["Diretor"].fillna("Não atribuído").astype(str)
        df["Progresso"] = pd.to_numeric(df["Progresso"], errors="coerce").fillna(0).astype(int)
        df["Estado"] = df["Estado"].fillna("No Prazo").astype(str)
        df["Imagem"] = df["Imagem"].fillna("").astype(str)
        return df
    except Exception:
        return pd.DataFrame(columns=["Código", "Obra", "Diretor", "Progresso", "Estado", "Imagem"])

df_obras = carregar_dados()

def resolver_imagem(url):
    url = str(url).strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return IMAGEM_PLACEHOLDER

# --- 4. INTERFACE ---
st.markdown("<h1>TWL Obras</h1>", unsafe_allow_html=True)
st.caption("Visão Geral do Portfólio")
st.write("") # Espaçamento

@st.dialog("Nova Obra")
def modal_nova_obra():
    with st.form("form_nova_obra", clear_on_submit=True):
        novo_cod = st.text_input("Código da Obra", placeholder="Ex: TWL-2026-04")
        novo_nome = st.text_input("Nome da Obra", placeholder="Ex: Construção Edifício Sede")
        novo_diretor = st.text_input("Diretor de Obra Responsável", placeholder="Ex: Eng. João Santos")
        novo_progresso = st.slider("Progresso Inicial (%)", 0, 100, 0)
        novo_estado = st.selectbox("Estado", ["No Prazo", "Atrasado", "Na Reta Final"])
        nova_img = st.text_input("URL da Imagem de Capa (Opcional)", placeholder="Deixe em branco para usar a imagem padrão")
        
        btn_gravar = st.form_submit_button("Guardar Registo", type="primary")
        
        if btn_gravar:
            if not novo_cod.strip() or not novo_nome.strip():
                st.error("Por favor, preencha o código e o nome da obra.")
            else:
                img_final = nova_img.strip() if (nova_img.strip().startswith("http://") or nova_img.strip().startswith("https://")) else IMAGEM_PLACEHOLDER
                nova_linha = pd.DataFrame([{
                    "Código": novo_cod.strip(),
                    "Obra": novo_nome.strip(),
                    "Diretor": novo_diretor.strip(),
                    "Progresso": int(novo_progresso),
                    "Estado": novo_estado,
                    "Imagem": img_final
                }])
                df_atualizado = pd.concat([df_obras, nova_linha], ignore_index=True)
                conn.update(worksheet=NOME_ABA, data=df_atualizado)
                st.success("Obra registada com sucesso!")
                st.rerun()

# Botão superior limpo e Métricas
if st.button("➕ Registar Nova Obra"):
    modal_nova_obra()
    
st.write("")

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric(label="Ativas", value=len(df_obras))
with col_m2:
    media_prog = int(df_obras["Progresso"].mean()) if not df_obras.empty else 0
    st.metric(label="Média Execução", value=f"{media_prog}%")
with col_m3:
    atrasos = len(df_obras[df_obras["Estado"] == "Atrasado"]) if not df_obras.empty else 0
    st.metric(label="Alertas", value=atrasos)

st.write("---")
st.markdown("<h3>Em Curso</h3>", unsafe_allow_html=True)
st.write("")

if df_obras.empty:
    st.info("Nenhuma obra registada. Adicione a primeira obra.")
else:
    for _, obra in df_obras.iterrows():
        # Usamos border=True para o CSS capturar o class do cartão
        with st.container(border=True):
            col_img, col_info, col_acao = st.columns([1.5, 2, 1])
            
            with col_img:
                st.image(resolver_imagem(obra["Imagem"]), use_container_width=True)
                
            with col_info:
                st.markdown(f"**{obra['Obra']}**")
                st.caption(f"{obra['Código']} • {obra['Diretor']}")
                prog_val = int(obra["Progresso"])
                st.progress(prog_val / 100)
                st.caption(f"{prog_val}% concluído — {obra['Estado']}")
                
            with col_acao:
                st.write("") # Empurrar o botão mais para o meio
                st.write("")
                if st.button("Diário", key=f"btn_{obra['Código']}"):
                    st.session_state["obra_selecionada"] = obra.to_dict()
                    st.switch_page("pages/1_Novo_Diario.py")
