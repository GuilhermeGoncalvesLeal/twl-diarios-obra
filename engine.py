import os
import base64
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

def image_to_base64(image_path):
    """Lê uma imagem e converte para base64 para injetar no HTML."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode('utf-8')
            ext = os.path.splitext(image_path)[1].replace('.', '')
            # Normalizar extensões jpg para jpeg
            if ext.lower() == 'jpg':
                ext = 'jpeg'
            return f"data:image/{ext};base64,{encoded}"
    return ""

def gerar_pdf(dados_diario, output_filename="Diario_Obra_Teste.pdf"):
    print("A iniciar a geração do PDF...")
    
    # 1. Configurar o Jinja2 para ler os templates da pasta correta
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('template_diario.html')
    
    # 2. Processar as fotos do dicionário de dados, convertendo para Base64
    for foto in dados_diario.get('fotos', []):
        if 'caminho' in foto:
            foto['imagem_base64'] = image_to_base64(foto['caminho'])
        else:
            foto['imagem_base64'] = ""

    # 3. Injetar os dados no HTML (Jinja2 render)
    html_out = template.render(dados_diario)
    
    # (Opcional) Guardar o HTML gerado para debug
    with open("temp_debug.html", "w", encoding="utf-8") as f:
        f.write(html_out)
        
    # 4. Converter o HTML renderizado em PDF usando o WeasyPrint
    try:
        print("A converter HTML para PDF com WeasyPrint...")
        HTML(string=html_out).write_pdf(output_filename)
        print(f"SUCESSO! PDF guardado como: {output_filename}")
    except Exception as e:
        print(f"ERRO ao gerar PDF: {e}")

# ==========================================
# TESTE DO MOTOR: DADOS FALSOS
# ==========================================
if __name__ == "__main__":
    # Vamos criar dados falsos simulando o preenchimento do Diretor de Obra
    dados_teste = {
        "relatorio_num": "001",
        "data": "23/08/2026",
        "obra_nome": "Edifício Sede Boavista",
        "cod_obra": "TWL-2026-01",
        "diretor_obra": "Eng. Guilherme Leal",
        "meteorologia": "Sol / 25ºC",
        "resumo_trabalhos": "Conclusão da cofragem dos pilares do Piso 1.\nInício das armaduras da laje.\nLimpeza geral do estaleiro no final do dia.",
        "fotos": [
            # NOTA: O script não vai falhar se a imagem não existir, apenas não mostra a foto.
            {"caminho": "assets/foto_teste.jpg", "legenda": "Cofragem Piso 1 concluída."},
        ]
    }
    
    # Executar a função
    gerar_pdf(dados_teste)