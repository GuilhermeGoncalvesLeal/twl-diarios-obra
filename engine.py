import os
import qrcode
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from datetime import datetime

def gerar_qr_code(url, caminho_saida="qr_code.png"):
    """Gera um QR code que aponta para o site da TWL"""
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(caminho_saida)
    return caminho_saida

def gerar_pdf(dados, output_filename="Diario_Obra.pdf"):
    # 1. Gerar o QR code atualizado
    caminho_qr = gerar_qr_code("https://www.twl-construcao.pt")
    
    # 2. Configurar o ambiente Jinja2 (HTML)
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template_rdo.html')
    
    # 3. Tratamento das Imagens da Obra
    fotos = dados.get("fotos", [])
    num_fotos = len(fotos)
    
    # Define a foto de capa (se não houver fotos na app, usa a default)
    if num_fotos > 0:
        foto_capa = fotos[0]["caminho"]
    else:
        foto_capa = "https://images.unsplash.com/photo-1541888946425-d0fbb1861593?w=800"

    # Preparar hora atual
    hora_atual = datetime.now().strftime("%H:%Mh")

    # 4. Renderizar o HTML preenchido com as variáveis da App
    html_out = template.render(
        data=dados.get("data", ""),
        hora=hora_atual,
        nome_obra=dados.get("obra_nome", "Obra Não Definida"),
        localizacao="Localização em Base de Dados", # Podes adicionar este campo no app.py dps
        diretor_obra=dados.get("diretor_obra", "Eng. Guilherme Leal"),
        resumo_trabalhos=dados.get("resumo_trabalhos", "Sem trabalhos registados hoje."),
        fotos=fotos,
        num_fotos=num_fotos,
        foto_capa=foto_capa,
        qr_code_path=os.path.abspath(caminho_qr),
        # Precisarás de ter as imagens na pasta assets
        logo_pequeno=os.path.abspath("assets/logo_twl_pequeno.png"),
        logo_grande_branco=os.path.abspath("assets/logo_twl_grande_branco.png")
    )
    
    # 5. Converter para PDF com WeasyPrint
    base_url = os.path.dirname(os.path.abspath(__file__))
    HTML(string=html_out, base_url=base_url).write_pdf(
        output_filename, 
        stylesheets=[CSS('estilo_rdo.css')]
    )
