import streamlit as st
import os
from PIL import Image
from engine import gerar_pdf

# Proteção para o ícone
try:
    icone_pagina = Image.open("logo.png")
except FileNotFoundError:
    icone_pagina = "🏗️"

st.set_page_config(page_title="Diário de Obra - TWL", page_icon=icone_pagina, layout="centered")

# Botão para regressar ao painel inicial
if st.button("⬅️ Voltar ao Dashboard"):
    st.switch_page("app.py")

# Obter dados pré-selecionados da sessão
obra_ativa = st.session_state.get("obra_selecionada", {})

# Determinar valores padrão baseados no clique
nome_padrao = obra_ativa.get("Obra", "")
codigo_padrao = obra_ativa.get("Código", "")
diretor_padrao = obra_ativa.get("Diretor", "")

st.title("🏗️ TWL - Diário de Obra")
st.markdown(f"A preencher relatório para: **{nome_padrao if nome_padrao else 'Nova Obra'}**")

with st.form("form_diario"):
    st.subheader("1. Dados Gerais")
    col1, col2 = st.columns(2)
    with col1:
        relatorio_num = st.text_input("Nº do Relatório", "001")
        obra_nome = st.text_input("Obra", value=nome_padrao)
        diretor_obra = st.text_input("Diretor de Obra", value=diretor_padrao)
    with col2:
        data_relatorio = st.date_input("Data do Relatório")
        cod_obra = st.text_input("Código da Obra", value=codigo_padrao)
        meteorologia = st.selectbox("Meteorologia", ["Sol", "Chuva Ligeira", "Chuva Forte", "Nublado", "Vento Forte"])
    
    st.subheader("2. Trabalhos em Curso")
    resumo_trabalhos = st.text_area("Descrição das frentes de trabalho ativas", height=120)
    
    st.subheader("3. Registo Fotográfico")
    fotos_upload = st.file_uploader("Carregue as fotografias (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    legendas = []
    if fotos_upload:
        for i, foto in enumerate(fotos_upload[:2]):
            legenda = st.text_input(f"Legenda para a Foto {i+1} ({foto.name})", key=f"leg_{i}")
            legendas.append(legenda)

    submitted = st.form_submit_button("Gerar Diário em PDF", type="primary")

def comprimir_imagem(imagem_upload, caminho_destino, largura_maxima=800):
    img = Image.open(imagem_upload)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    proporcao = largura_maxima / float(img.size[0])
    nova_altura = int((float(img.size[1]) * float(proporcao)))
    img = img.resize((largura_maxima, nova_altura), Image.Resampling.LANCZOS)
    img.save(caminho_destino, format="JPEG", optimize=True, quality=75)

if submitted:
    with st.spinner("A processar dados e imagens para a TWL..."):
        if not os.path.exists("temp_images"):
            os.makedirs("temp_images")
            
        fotos_processadas = []
        if fotos_upload:
            for i, foto in enumerate(fotos_upload[:2]): 
                caminho_temp = os.path.join("temp_images", f"foto_{i}.jpg")
                comprimir_imagem(foto, caminho_temp)
                texto_legenda = legendas[i] if i < len(legendas) and legendas[i] else f"Registo {i+1} - {obra_nome}"
                fotos_processadas.append({
                    "caminho": caminho_temp,
                    "legenda": texto_legenda
                })
                
        dados_diario = {
            "relatorio_num": relatorio_num,
            "data": data_relatorio.strftime("%d/%m/%Y"),
            "obra_nome": obra_nome,
            "cod_obra": cod_obra,
            "diretor_obra": diretor_obra,
            "meteorologia": meteorologia,
            "resumo_trabalhos": resumo_trabalhos,
            "fotos": fotos_processadas
        }
        
        nome_ficheiro_pdf = f"Diario_{cod_obra}_N{relatorio_num}.pdf"
        try:
            gerar_pdf(dados_diario, output_filename=nome_ficheiro_pdf)
            st.success("✅ Diário de Obra gerado com sucesso!")
            with open(nome_ficheiro_pdf, "rb") as pdf_file:
                st.download_button(
                    label="📥 Descarregar Diário de Obra (PDF)",
                    data=pdf_file,
                    file_name=nome_ficheiro_pdf,
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
