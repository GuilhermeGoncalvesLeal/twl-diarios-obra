"""
Gerador de PDF do RDO (Relatório Diário de Obra) — TWL Construção.

Reproduz o layout do template oficial. O logo e o QR não são imagens comuns:
são os paths vetoriais exatos extraídos do ficheiro de design original,
pré-renderizados a alta resolução em assets/vector/ (ver README).

Uso:
    from services.pdf_generator import generate_rdo_pdf

    pdf_bytes = generate_rdo_pdf(obra, rdo, photos)

    obra = {
        "nome_obra": "Delta Expresso",
        "localizacao": "R. de Alexandre Braga 2, 4000-409 Porto",
        "capa_bytes": b"...",  # bytes da imagem de capa (opcional)
    }
    rdo = {
        "data": "25/08/2026",
        "hora": "21:47",
        "referencia": "GL_DE_25_08_2026",
        "resumo": "texto livre das atividades realizadas...",
        "responsavel_nome": "Eng.º Guilherme Gonçalves Leal",
        "responsavel_contacto": "(+351) 961 743 951",
    }
    photos = [{"bytes": b"...", "legenda": "Provadores"}, ...]  # qualquer nº de fotos
"""
import io
import os

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
VECTOR_DIR = os.path.join(ASSETS, "vector")
FONTS_DIR = os.path.join(ASSETS, "fonts")

# Página medida diretamente do template (210 x 297mm), em pt (1/72")
PAGE_W, PAGE_H = 596.0, 842.0
BLACK = (0, 0, 0)

# --- Grelha de fotos (constantes extraídas do template — não mexer sem remedir) ---
GRID_LEFT_X = 33.22
GRID_RIGHT_X = 314.61
GRID_COL_W = 248.17
GRID_ROW_H = 185.92
GRID_ROW_GAP = 46.93
CAPTION_GAP = 19.19       # da base da foto até à baseline da legenda
GRID_TOP_AFTER_TITLE = 36.56   # da baseline do título "Registro Fotográfico" até ao topo da 1ª foto
CONTINUATION_GRID_TOP = 177.66  # topo fixo da grelha em páginas só de fotos (sem "Atividades")

MARGIN_X = 33.22
CONTENT_W = 562.78 - 33.22


# ---------------------------------------------------------------------------
# Registo de fontes — usa Inter / Playfair Display reais assim que os .ttf
# existirem em assets/fonts/. Até lá, cai em Helvetica/Times-Roman.
# ---------------------------------------------------------------------------
def _register_fonts():
    mapping = {
        "PlayfairDisplay-Regular": "PlayfairDisplay-Regular.ttf",
        "Inter-Regular": "Inter-Regular.ttf",
        "Inter-Medium": "Inter-Medium.ttf",
        "Inter-Light": "Inter-Light.ttf",
    }
    available = {}
    for name, fname in mapping.items():
        path = os.path.join(FONTS_DIR, fname)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                available[name] = name
            except Exception:
                pass
    return available


_FONTS = _register_fonts()
SERIF = _FONTS.get("PlayfairDisplay-Regular", "Times-Roman")
SANS_REG = _FONTS.get("Inter-Regular", "Helvetica")
SANS_MED = _FONTS.get("Inter-Medium", "Helvetica-Bold")
SANS_LIGHT = _FONTS.get("Inter-Light", "Helvetica")


# ---------------------------------------------------------------------------
# Helpers de desenho
# ---------------------------------------------------------------------------
def _y(y_top_down):
    """Converte y medido a partir do topo (como no template) para o sistema
    do ReportLab, cuja origem é o canto inferior-esquerdo."""
    return PAGE_H - y_top_down


def _draw_image_cover(c, img_bytes, x0, y0_td, x1, y1_td):
    """Desenha a imagem preenchendo a caixa, cortando o excesso (object-fit: cover)."""
    box_w, box_h = x1 - x0, y1_td - y0_td
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    iw, ih = img.size
    box_ratio, img_ratio = box_w / box_h, iw / ih
    if img_ratio > box_ratio:
        new_w = int(ih * box_ratio)
        off = (iw - new_w) // 2
        img = img.crop((off, 0, off + new_w, ih))
    else:
        new_h = int(iw / box_ratio)
        off = (ih - new_h) // 2
        img = img.crop((0, off, iw, off + new_h))
    c.drawImage(ImageReader(img), x0, _y(y1_td), width=box_w, height=box_h,
                preserveAspectRatio=False, mask="auto")


def _draw_vector(c, filename, x0, y0_td, x1, y1_td):
    # Fundo sólido embutido na própria imagem (sem canal alfa) — evita um bug
    # de renderização do Firefox/PDF.js com máscaras de transparência que
    # invertia visualmente o logo nalguns visualizadores.
    path = os.path.join(VECTOR_DIR, filename)
    c.drawImage(ImageReader(path), x0, _y(y1_td), width=x1 - x0, height=y1_td - y0_td)


def _draw_text(c, text, x, y_baseline_td, font, size, fill=BLACK):
    c.setFont(font, size)
    c.setFillColorRGB(*fill)
    c.drawString(x, _y(y_baseline_td), text)


def _wrap_text(c, text, font, size, max_width):
    c.setFont(font, size)
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if c.stringWidth(trial, font, size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_justified_paragraph(c, text, x, y_start_td, font, size, max_width, line_height):
    """Desenha um parágrafo justificado (alinhado à esquerda E à direita),
    como o texto de um jornal. A última linha do parágrafo fica alinhada só
    à esquerda, como é convenção tipográfica normal."""
    lines = _wrap_text(c, text, font, size, max_width)
    c.setFont(font, size)
    c.setFillColorRGB(*BLACK)
    y = y_start_td
    for i, line in enumerate(lines):
        words = line.split()
        is_last_line = (i == len(lines) - 1)
        if is_last_line or len(words) == 1:
            c.drawString(x, _y(y), line)
        else:
            words_width = sum(c.stringWidth(w, font, size) for w in words)
            extra_space = (max_width - words_width) / (len(words) - 1)
            cx = x
            for w in words:
                c.drawString(cx, _y(y), w)
                cx += c.stringWidth(w, font, size) + extra_space
        y += line_height
    return y


def _header(c):
    _draw_vector(c, "logo_black.png", 33.22, 46.93, 118.0, 75.94)
    _draw_vector(c, "qr_black.png", 486.77, 46.93, 562.78, 122.86)


def _footer(c):
    c.setStrokeColorRGB(*BLACK)
    c.setLineWidth(0.75)
    c.line(33.22, _y(795.07), 562.78, _y(795.07))
    _draw_text(c, "www.twl-construcao.pt", 33.05, 819.5, SANS_LIGHT, 8.38)
    _draw_text(c, "Rua do Barroco 174 - Armazem R, 4465-591 Leça do Balio", 352.23, 819.5, SANS_LIGHT, 8.38)


def _photo_grid(c, photos_chunk, start_index, grid_top):
    """Desenha até 4 fotos em grelha 2x2 a partir de grid_top (topo-baixo)."""
    positions = [
        (GRID_LEFT_X, grid_top),
        (GRID_RIGHT_X, grid_top),
        (GRID_LEFT_X, grid_top + GRID_ROW_H + GRID_ROW_GAP),
        (GRID_RIGHT_X, grid_top + GRID_ROW_H + GRID_ROW_GAP),
    ]
    for i, photo in enumerate(photos_chunk[:4]):
        x0, y0 = positions[i]
        x1, y1 = x0 + GRID_COL_W, y0 + GRID_ROW_H
        _draw_image_cover(c, photo["bytes"], x0, y0, x1, y1)
        legenda = photo.get("legenda", "")
        caption = f"Figura {start_index + i + 1} - {legenda}" if legenda else f"Figura {start_index + i + 1}"
        c.setFont(SANS_LIGHT, 8.38)
        text_w = c.stringWidth(caption, SANS_LIGHT, 8.38)
        cx = x0 + (GRID_COL_W - text_w) / 2
        _draw_text(c, caption, cx, y1 + CAPTION_GAP, SANS_LIGHT, 8.38)


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
def _page_capa(c, obra, rdo):
    _header(c)
    c.setFont(SERIF, 41.34)
    c.setFillColorRGB(*BLACK)
    c.drawString(31.48, _y(153.0), "Relatório")
    c.drawString(31.48, _y(194.3), "Diário de Obra")

    _draw_text(c, f"{rdo['data']} - {rdo['hora']}h", 32.56, 238.0, SANS_REG, 13.56)

    c.saveState()
    c.translate(560.0, _y(472.21))
    c.rotate(90)
    c.setFont(SANS_REG, 13.56)
    c.setFillColorRGB(*BLACK)
    c.drawString(0, 0, f"REF.: {rdo['referencia']}")
    c.restoreState()

    _draw_text(c, "Obra", 32.64, 296.0, SANS_MED, 13.56)
    _draw_text(c, obra["nome_obra"], 32.19, 317.3, SANS_REG, 13.56)

    _draw_text(c, "Localização", 32.28, 348.0, SANS_MED, 13.56)
    _draw_text(c, obra["localizacao"], 32.19, 369.3, SANS_REG, 13.56)

    _draw_text(c, "Responsável", 32.28, 429.0, SANS_MED, 13.56)
    _draw_text(c, rdo["responsavel_nome"], 32.19, 452.3, SANS_REG, 13.56)
    _draw_text(c, rdo["responsavel_contacto"], 32.19, 470.1, SANS_REG, 13.56)

    if obra.get("capa_bytes"):
        _draw_image_cover(c, obra["capa_bytes"], 0.0, 520.4, 595.99, 842.0)


def _page_atividades(c, resumo, total_fotos, first_chunk):
    _header(c)
    c.setFont(SERIF, 25.55)
    c.setFillColorRGB(*BLACK)
    c.drawString(33.4, _y(140.0), "Atividades Realizadas")

    y = _draw_justified_paragraph(c, resumo, 32.56, 182.0, SANS_LIGHT, 13.56, CONTENT_W, 17.5)

    title_baseline = y + 60.0
    c.setFont(SERIF, 25.55)
    c.setFillColorRGB(*BLACK)
    c.drawString(32.15, _y(title_baseline), f"Registro Fotográfico ({total_fotos})")

    grid_top = title_baseline + GRID_TOP_AFTER_TITLE
    _photo_grid(c, first_chunk, 0, grid_top)
    _footer(c)


def _page_registro_continuacao(c, chunk, start_index, total_fotos):
    _header(c)
    c.setFont(SERIF, 25.55)
    c.setFillColorRGB(*BLACK)
    c.drawString(32.15, _y(141.0), f"Registro Fotográfico ({total_fotos})")
    _photo_grid(c, chunk, start_index, CONTINUATION_GRID_TOP)
    _footer(c)


def _page_contracapa(c):
    c.setFillColorRGB(0, 0, 0)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Calcular aspect ratio a partir das dimensões reais da imagem
    img = Image.open(os.path.join(VECTOR_DIR, "logo_white.png"))
    img_w, img_h = img.size
    logo_w = 200.0
    logo_h = logo_w * (img_h / img_w)
    x0 = (PAGE_W - logo_w) / 2
    y0_td = (PAGE_H - logo_h) / 2
    _draw_vector(c, "logo_white.png", x0, y0_td, x0 + logo_w, y0_td + logo_h)


# ---------------------------------------------------------------------------
# Entrada pública
# ---------------------------------------------------------------------------
def generate_rdo_pdf(obra: dict, rdo: dict, photos: list) -> bytes:
    """Gera o PDF completo do RDO e devolve os bytes (pronto para download_button
    ou para upload direto para a Drive)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))

    _page_capa(c, obra, rdo)
    c.showPage()

    first_chunk, remaining = photos[:4], photos[4:]
    _page_atividades(c, rdo["resumo"], len(photos), first_chunk)
    c.showPage()

    idx = 4
    while remaining:
        chunk, remaining = remaining[:4], remaining[4:]
        _page_registro_continuacao(c, chunk, idx, len(photos))
        c.showPage()
        idx += 4

    _page_contracapa(c)
    c.showPage()

    c.save()
    return buf.getvalue()
