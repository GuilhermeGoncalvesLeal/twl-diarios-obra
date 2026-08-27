"""
Script de configuração única — cria a Google Sheet "TWL_Obras" já com os 3
separadores e as colunas certas, e imprime o ID a colar em secrets.toml.

Como correr (fora do Streamlit, no teu computador):

    pip install gspread google-auth
    python setup_gsheets.py caminho/para/credenciais_service_account.json teu-email@gmail.com

O segundo argumento (o teu email pessoal) é para a folha ficar também
partilhada contigo como Editor — senão só a service account consegue vê-la.
"""
import sys

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEETS = {
    "Obras": [
        "id_obra", "nome_obra", "codigo_obra", "localizacao",
        "percentagem", "descricao_curta", "capa_file_id", "estado",
    ],
    "Responsaveis": ["nome_completo", "iniciais", "contacto", "ativo"],
    "RDOs": ["id_obra", "data", "responsavel", "referencia"],
}

EXEMPLO_OBRA = [
    "1", "Delta Expresso", "DE", "R. de Alexandre Braga 2, 4000-409 Porto",
    "80", "Quiosque de café em contexto de retalho.", "", "ativa",
]
EXEMPLO_RESPONSAVEL = ["Eng.º Guilherme Gonçalves Leal", "GL", "(+351) 961 743 951", "sim"]


def main():
    if len(sys.argv) < 2:
        print("Uso: python setup_gsheets.py credenciais.json [teu-email@gmail.com]")
        sys.exit(1)

    cred_path = sys.argv[1]
    share_email = sys.argv[2] if len(sys.argv) > 2 else None

    creds = Credentials.from_service_account_file(cred_path, scopes=SCOPES)
    client = gspread.authorize(creds)

    sh = client.open("TWL_Obras")
    if share_email:
        sh.share(share_email, perm_type="user", role="writer")

    # a spreadsheet vem com um separador "Sheet1" por omissão — reaproveita-o
    first = True
    for name, headers in SHEETS.items():
        if first:
            ws = sh.sheet1
            ws.update_title(name)
            first = False
        else:
            ws = sh.add_worksheet(title=name, rows=100, cols=len(headers))
        ws.update("A1", [headers])
        ws.format(f"A1:{chr(64 + len(headers))}1", {"textFormat": {"bold": True}})

    sh.worksheet("Obras").append_row(EXEMPLO_OBRA)
    sh.worksheet("Responsaveis").append_row(EXEMPLO_RESPONSAVEL)

    print("\nSpreadsheet criada com sucesso.")
    print("Nome:", sh.title)
    print("ID  :", sh.id)
    print("URL :", sh.url)
    print("\nCola este ID em secrets.toml -> [twl] -> spreadsheet_id")
    print("\nNota: a coluna 'capa_file_id' na linha de exemplo ficou vazia —")
    print("preenche com o ID do ficheiro .png da capa depois de o carregares para a Drive.")


if __name__ == "__main__":
    main()
