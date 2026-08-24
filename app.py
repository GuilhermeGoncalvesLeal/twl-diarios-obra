import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuração global da página
st.set_page_config(page_title="TWL - Portal de Obra", page_icon="🏢", layout="wide")

# Imagem padrão para obras sem fotografia definida
IMAGEM_PADRAO = "https://images.unsplash.com/photo-1541888946425-d0fbb1861593?w=600"

# Ligação à Base de Dados Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Código", "Obra", "Diretor", "Progresso", "Estado", "Imagem"])
        # Limpeza de dados para prevenir erros de tipos nulos
        df["Código"] = df["Código"].fillna("SEM-COD").astype(str)
        df["Obra"] = df["Obra"].fillna("Obra sem nome").astype(str)
        df["Diretor"] = df["Diretor"].fillna("Não atribuído").astype(str)
        df["Progresso"] = pd.to_numeric(df["Progresso"], errors="coerce").fillna(0).astype(int)
        df["Estado"] = df["Estado"].fillna("No Prazo").astype(str)
        df["Imagem"] = df["Imagem"].fillna(IMAGEM_PADRAO).astype(str)
        return df
    except Exception:
        return pd.DataFrame(columns=["Código", "Obra", "Diretor", "Progresso", "Estado", "Imagem"])

df_obras = carregar_dados()

st.title("🏢 TWL Engenharia & Construção")
st.subheader("Visão Geral das Obras (Dashboard)")

# Modal para registar nova obra
@st.dialog("➕ Registar Nova Obra")
def modal_nova_obra():
    with st.form("form_nova_obra"):
        novo_cod = st.text_input("Código da Obra", placeholder="TWL-2026-04")
        novo_nome = st.text_input("Nome da Obra", placeholder="Nova Construção")
        novo_diretor = st.text_input("Diretor de Obra Responsável", placeholder="Eng. João Santos")
        novo_progresso = st.slider("Progresso Inicial (%)", 0, 100, 0)
        novo_estado = st.selectbox("Estado", ["No Prazo", "Atrasado", "Na Reta Final"])
        nova_img = st.text_input("URL da Imagem de Capa", value=IMAGEM_PADRAO)
        
        btn_gravar = st.form_submit_button("Guardar Obra na Base de Dados", type="primary")
        
        if btn_gravar:
            if not novo_cod.strip() or not novo_nome.strip():
                st.error("Por favor, preencha o código e o nome da obra.")
            else:
                img_final = nova_img.strip() if nova_img.strip() else IMAGEM_PADRAO
                nova_linha = pd.DataFrame([{
                    "Código": novo_cod.strip(),
                    "Obra": novo_nome.strip(),
                    "Diretor": novo_diretor.strip(),
                    "Progresso": int(novo_progresso),
                    "Estado": novo_estado,
                    "Imagem": img_final
                }])
                
                df_atualizado = pd.concat([df_obras, nova_linha], ignore_index=True)
                conn.update(data=df_atualizado)
                st.success("Obra registada com sucesso!")
                st.rerun()

# Barra Superior de Métricas
col_btn, col_m1, col_m2, col_m3 = st.columns([2, 1, 1, 1])

with col_btn:
    if st.button("➕ Registar Nova Obra", type="primary"):
        modal_nova_obra()

with col_m1:
    st.metric(label="Obras Ativas", value=len(df_obras))
with col_m2:
    media_prog = int(df_obras["Progresso"].mean()) if not df_obras.empty else 0
    st.metric(label="Média de Execução", value=f"{media_prog}%")
with col_m3:
    atrasos = len(df_obras[df_obras["Estado"] == "Atrasado"]) if not df_obras.empty else 0
    st.metric(label="Alertas (Atrasos)", value=atrasos, delta=f"-{atrasos}" if atrasos > 0 else "0")

st.divider()

# Listagem das Obras
st.markdown("### Obras em Curso")

if df_obras.empty:
    st.info("Nenhuma obra registada. Clique no botão acima para adicionar a primeira obra.")
else:
    for _, obra in df_obras.iterrows():
        with st.container():
            col_img, col_info, col_prog, col_acao = st.columns([1.5, 2, 2, 1])
            
            with col_img:
                url_foto = obra["Imagem"] if isinstance(obra["Imagem"], str) and obra["Imagem"].startswith("http") else IMAGEM_PADRAO
                st.image(url_foto, use_container_width=True)
                
            with col_info:
                st.markdown(f"**{obra['Obra']}**")
                st.caption(f"Código: `{obra['Código']}`")
                st.caption(f"Diretor: {obra['Diretor']}")
                
            with col_prog:
                prog_val = int(obra["Progresso"])
                st.progress(prog_val / 100)
                st.caption(f"Progresso: {prog_val}% — {obra['Estado']}")
                
            with col_acao:
                if st.button("Gerar Diário", key=f"btn_{obra['Código']}"):
                    st.session_state["obra_selecionada"] = obra.to_dict()
                    st.switch_page("pages/1_Novo_Diario.py")
                    
        st.divider()
