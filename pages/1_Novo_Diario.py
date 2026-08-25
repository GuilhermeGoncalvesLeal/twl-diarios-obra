import streamlit as st
import os
from PIL import Image
from engine import gerar_pdf

# Configuração da página e ícone
icone_pagina = "🏗️"
if os.path.exists("logo.png"):
    try:
        icone_pagina = Image.open("logo.png")
    except Exception:
        pass

st.set_page_config(page_title="TWL - Gerar RDO", page_icon=icone_pagina, layout="wide")

# CSS personalizado para o formulário (Estilo Minimalista TWL)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stApp {
        background-color: #F2F4F7 !important;
    }
    
    p, div, span, label {
        color: #333333 !important;
    }
    
    h1, h2, h3, h4 {
        color: #111111 !important;
        font-weight: 800 !important;
        letter-spacing: -1px !important;
    }
    
    /* Contentores arredondados em branco */
    [data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border-radius: 28px !important;
        border: none !important;
        box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.05) !important;
        padding: 30px !important;
    }
    
    /* Botões estilo Pílula */
    .stButton > button {
        background-color: #161616 !important;
        border-radius: 40px !important;
        border: none !important;
        padding: 10px 24px !important;
        transition: all 0.3s ease;
    }
    .stButton > button * {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover {
        background-color: #333333 !important;
        transform: scale(1.02);
    }
    
    /* Inputs arredondados */
    input, textarea, select {
        border-radius: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Botão superior de navegação
col_nav, _ = st.columns([1, 4])
with col_nav:
    if st.button("⬅️ Voltar ao Painel"):
        st.switch_page("app.py")

# Obter dados pré-selecionados do Dashboard
obra_ativa = st.session_state.get("obra_selecionada", {})
nome_padrao = obra_ativa.get("Obra", "")
codigo_padrao = obra_ativa.get("Código", "")
diretor_padrao = obra_ativa.get("Diretor", "Eng. Guilherme Gonçalves Leal")

st.markdown("<h1>Novo Relatório Diário de Obra (RDO)</h1>", unsafe_allow_html=True)
if nome_padrao:
    st.caption(f"A emitir documento oficial para: **{nome_padrao}** (`{codigo_padrao}`)")
else:
    st.caption("Preencha as informações técnicas e o registo fotográfico do dia.")

st.write("")

with st.form("form_rdo"):
    st.markdown("### 1. Identificação do Projeto")
    col1, col2 = st.columns(2)
    with col1:
        relatorio_num = st.text_input("Nº do Relatório", value="01")
        obra_nome = st.text_input("Nome da Obra", value=nome_padrao if nome_padrao else "Delta Expresso")
        localizacao = st.text_input("Localização", value="R. de Alexandre Braga 2, 4000-409 Porto")
    with col2:
        data_relatorio = st.date_input("Data do Relatório")
        cod_obra = st.text_input("Referência / Código", value=codigo_padrao if codigo_padrao else "GL_DE_01")
        diretor_obra = st.text_input("Responsável Técnico", value=diretor_padrao)

    st.write("---")
    st.markdown("### 2. Atividades Realizadas")
    resumo_trabalhos = st.text_area(
        "Descrição dos trabalhos executados",
        value="Continuação dos trabalhos de pintura, acabamentos e detalhamentos. Receção de material luminoso e elétrico.",
        height=120
    )

    st.write("---")
    st.markdown("### 3. Registo Fotográfico")
    st.caption("A primeira foto carregada será utilizada como fotografia de destaque na capa do RDO.")
    fotos_upload = st.file_uploader("Carregar Fotografias da Obra", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    legendas = []
    if fotos_upload:
        st.write("Legendas das Fotografias:")
        cols_leg = st.columns(2)
        for i, foto in enumerate(fotos_upload):
            with cols_leg[i % 2]:
                legenda = st.text_input(f"Legenda Foto {i+1} ({foto.name})", value=f"Registo {i+1}", key=f"leg_{i}")
                legendas.append(legenda)

    st.write("")
    btn_gerar = st.form_submit_button("Gerar RDO em PDF", type="primary")

def processar_imagem(upload, destino, largura_maxima=1200):
    img = Image.open(upload)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    proporcao = largura_maxima / float(img.size[0])
    nova_altura = int((float(img.size[1]) * float(proporcao)))
    img = img.resize((largura_maxima, nova_altura), Image.Resampling.LANCZOS)
    img.save(destino, format="JPEG", optimize=True, quality=85)

if btn_gerar:
    if not obra_nome.strip():
        st.error("Por favor, indique o nome da obra.")
    else:
        with st.spinner("A compilar o Relatório Diário de Obra em alta resolução..."):
            if not os.path.exists("temp_images"):
                os.makedirs("temp_images")

            fotos_processadas = []
            if fotos_upload:
                for i, foto in enumerate(fotos_upload):
                    caminho_temp = os.path.join("temp_images", f"foto_{i}.jpg")
                    processar_imagem(foto, caminho_temp)
                    texto_legenda = legendas[i] if i < len(legendas) and legendas[i] else f"Figura {i+1}"
                    fotos_processadas.append({
                        "caminho": caminho_temp,
                        "legenda": texto_legenda
                    })

            dados_diario = {
                "relatorio_num": relatorio_num,
                "data": data_relatorio.strftime("%d/%m/%Y"),
                "obra_nome": obra_nome,
                "cod_obra": cod_obra,
                "localizacao": localizacao,
                "diretor_obra": diretor_obra,
                "resumo_trabalhos": resumo_trabalhos,
                "fotos": fotos_processadas
            }

            nome_pdf = f"RDO_{cod_obra}_N{relatorio_num}.pdf"
            try:
                gerar_pdf(dados_diario, output_filename=nome_pdf)
                st.success("✅ RDO compilado com sucesso!")
                with open(nome_pdf, "rb") as f:
                    st.download_button(
                        label="📥 Descarregar RDO Oficial (PDF)",
                        data=f,
                        file_name=nome_pdf,
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Erro na compilação do PDF: {e}")
