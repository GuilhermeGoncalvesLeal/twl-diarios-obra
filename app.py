import streamlit as st
import pandas as pd

st.set_page_config(page_title="TWL - Portal de Obra", page_icon="🏢", layout="wide")

st.title("🏢 TWL Engenharia & Construção")
st.subheader("Visão Geral das Obras (Dashboard)")

# 1. Simulação de uma base de dados das obras ativas
dados_obras = {
    "Código": ["TWL-2026-01", "TWL-2026-02", "TWL-2026-03"],
    "Obra": ["Edifício Sede Boavista", "Reabilitação Baixa", "Loteamento Sul"],
    "Diretor": ["Eng. Guilherme Leal", "Eng. Tiago Silva", "Eng. Guilherme Leal"],
    "Progresso": [65, 12, 90],
    "Estado": ["No Prazo", "Atrasado", "Na Reta Final"]
}
df_obras = pd.DataFrame(dados_obras)

# 2. Mostrar Métricas Globais Rápidas
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Obras Ativas", value="3")
with col2:
    st.metric(label="Média de Execução", value="55%")
with col3:
    st.metric(label="Alertas (Atrasos)", value="1", delta="-1")

st.divider()

# 3. Mostrar os "Cartões" das Obras
st.markdown("### Obras em Curso")

for index, obra in df_obras.iterrows():
    # Criar uma "caixa" visual para cada obra
    with st.container():
        colA, colB, colC = st.columns([2, 2, 1])
        with colA:
            st.markdown(f"**{obra['Obra']}** ({obra['Código']})")
            st.caption(f"Diretor: {obra['Diretor']}")
        with colB:
            # Barra de progresso visual do Streamlit
            st.progress(obra['Progresso'] / 100)
            st.caption(f"Progresso: {obra['Progresso']}% - {obra['Estado']}")
        with colC:
            # Botão de ação
            if st.button(f"Gerar Diário", key=f"btn_{obra['Código']}"):
    st.switch_page("pages/1_Novo_Diario.py")

