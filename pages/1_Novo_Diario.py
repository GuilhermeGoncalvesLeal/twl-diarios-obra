import streamlit as st
import os
from PIL import Image
from engine import gerar_pdf 

# Configuração da página
st.set_page_config(page_title="Diário de Obra - TWL", page_icon="🏗️", layout="centered")

st.title("🏗️ TWL - Diário de Obra")
st.markdown("Preencha os dados da obra no terreno.")

def comprimir_imagem(imagem_upload, caminho_destino, largura_maxima=800):
    """Lê a imagem do upload, redimensiona-a (mantendo a proporção) e guarda no disco."""
    img = Image.open(imagem_upload)
    
    # Converter para RGB (evita erros com PNGs transparentes ao guardar como JPEG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    # Calcular a nova altura mantendo a proporção (Aspect Ratio)
    proporcao = largura_maxima / float(img.size[0])
    nova_altura = int((float(img.size[1]) * float(proporcao)))
    
    # Redimensionar usando o filtro LANCZOS (alta qualidade)
    img = img.resize((largura_maxima, nova_altura), Image.Resampling.LANCZOS)
    
    # Guardar a imagem comprimida (Qualidade 75 é o "sweet spot" entre tamanho e nitidez)
    img.save(caminho_destino, format="JPEG", optimize=True, quality=75)

# Formulário da Interface
with st.form("form_diario"):
    st.subheader("1. Dados Gerais")
    col1, col2 = st.columns(2)
    with col1:
        relatorio_num = st.text_input("Nº do Relatório", "002")
        obra_nome = st.selectbox("Obra", ["Edifício Sede Boavista", "Reabilitação Baixa", "Loteamento Sul"])
        diretor_obra = st.text_input("Diretor de Obra", "Eng. Guilherme Leal")
    with col2:
        data_relatorio = st.date_input("Data do Relatório")
        cod_obra = st.text_input("Código da Obra", "TWL-2026-02")
        meteorologia = st.selectbox("Meteorologia", ["Sol", "Chuva Ligeira", "Chuva Forte", "Nublado"])
    
    st.subheader("2. Trabalhos em Curso")
    resumo_trabalhos = st.text_area("Descrição das frentes de trabalho ativas", height=100)
    
    st.subheader("3. Registo Fotográfico")
    st.info("Pode carregar 1 ou 2 fotografias. O sistema irá comprimi-las automaticamente.")
    fotos_upload = st.file_uploader("Carregue as fotografias (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    # Text inputs dinâmicos para as legendas
    legendas = []
    if fotos_upload:
        for i, foto in enumerate(fotos_upload[:2]):
            legenda = st.text_input(f"Legenda para a Foto {i+1} ({foto.name})", key=f"legenda_{i}")
            legendas.append(legenda)

    # Botão de Gerar
    submitted = st.form_submit_button("Gerar Diário em PDF", type="primary")

# Acções após clique no botão
if submitted:
    with st.spinner("A comprimir imagens e a gerar o PDF da TWL..."):
        if not os.path.exists("temp_images"):
            os.makedirs("temp_images")
            
        fotos_processadas = []
        if fotos_upload:
            for i, foto in enumerate(fotos_upload[:2]): 
                # Alteramos sempre a extensão para .jpg porque vamos guardar como JPEG
                nome_seguro = f"foto_{i}.jpg"
                caminho_temp = os.path.join("temp_images", nome_seguro)
                
                # Chamamos a nossa nova função de compressão!
                comprimir_imagem(foto, caminho_temp)
                
                texto_legenda = legendas[i] if i < len(legendas) else "Sem legenda."
                fotos_processadas.append({
                    "caminho": caminho_temp,
                    "legenda": texto_legenda
                })
                
        # Empacotar dados
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
            st.success("✅ O Diário de Obra foi gerado e as imagens otimizadas!")
            
            with open(nome_ficheiro_pdf, "rb") as pdf_file:
                st.download_button(
                    label="📥 Descarregar Diário de Obra (PDF)",
                    data=pdf_file,
                    file_name=nome_ficheiro_pdf,
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
