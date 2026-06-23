"""
config.py — Carrega e valida todas as configurações do arquivo .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")


def _exigir(chave: str) -> str:
    """Lê variável de ambiente e lança erro claro se não estiver definida."""
    valor = os.getenv(chave, "").strip()
    if not valor:
        raise EnvironmentError(
            f"\n[ERRO] A variável '{chave}' não está definida no arquivo .env.\n"
            f"       Copie .env.example para .env e preencha os valores."
        )
    return valor


# ── Sistema ────────────────────────────────────────────────────────────────────
LAB_URL = _exigir("LAB_URL")
DIAS_ATRAS = int(os.getenv("DIAS_ATRAS", "0").strip())


# ── XPath — Navegação: Comercial → Pedidos ─────────────────────────────────────
XPATH_MENU_COMERCIAL = os.getenv(
    "XPATH_MENU_COMERCIAL",
    "//body/section[@class='ftco-section pt-3 print-none']/nav[@id='ftco-navbar']"
    "/div[@class='container-fluid']/div[@id='ftco-nav']"
    "/ul[@class='navbar-nav m-auto']/li[4]/a[1]"
).strip()

XPATH_SUBMENU_PEDIDOS = os.getenv(
    "XPATH_SUBMENU_PEDIDOS",
    "//a[normalize-space()='Pedidos']"
).strip()

# ── XPath — Filtros na tela de Pedidos ────────────────────────────────────────
XPATH_FILTRO_DATA_INICIO = os.getenv(
    "XPATH_FILTRO_DATA_INICIO",
    "//input[@id='dataInicialFiltro']"
).strip()

XPATH_FILTRO_DATA_FIM = os.getenv(
    "XPATH_FILTRO_DATA_FIM",
    "//input[@id='dataFinalFiltro']"
).strip()

XPATH_BTN_FILTRAR = os.getenv(
    "XPATH_BTN_FILTRAR",
    "//button[@type='submit']"
).strip()

# ── Critérios de qualificação na tabela de Pedidos ────────────────────────────
# Texto da coluna Status (td[7]) que indica pedido pronto
TEXTO_STATUS_FINALIZADO = os.getenv("TEXTO_STATUS_FINALIZADO", "FINALIZADO").strip()

# Classe CSS do ícone <i> na coluna Faturado (td[9]) que indica pago
# Descubra via: F12 → Console → document.querySelector('#tabela_pedido tbody tr td:nth-child(9) i').className
CLASSE_FATURADO_SIM = os.getenv("CLASSE_FATURADO_SIM", "fa-check").strip()

# ── XPath — Tela de detalhe do Pedido (telefone e nome do cliente) ─────────────
XPATH_TELEFONE_CLIENTE = os.getenv(
    "XPATH_TELEFONE_CLIENTE",
    "//body/section/div[@class='col page']/main[@id='mainRelatorio']"
    "/div[@class='container-box-shadow pt-1 pb-1 pr-3 pl-3 mt-3 corpo_impressao']"
    "/div[4]/div[2]/div[2]/div[1]/input[1]"
).strip()

XPATH_NOME_CLIENTE = os.getenv(
    "XPATH_NOME_CLIENTE",
    "//div[4]//div[1]//div[1]//div[1]//input[1]"
).strip()

# ── Validação de tipo de amostra ───────────────────────────────────────────────
# Seletor CSS da tabela de amostras dentro do pedido
SELETOR_TABELA_AMOSTRAS = os.getenv("SELETOR_TABELA_AMOSTRAS", "table").strip()

# Cabeçalho da coluna de tipo (conforme pedido PDF: "Tipo")
HEADER_COLUNA_TIPO_AMOSTRA = os.getenv("HEADER_COLUNA_TIPO_AMOSTRA", "Tipo").strip()

# Valor permitido — pedidos com outro tipo são ignorados
TIPO_AMOSTRA_PERMITIDO = os.getenv("TIPO_AMOSTRA_PERMITIDO", "Solo").strip()

# ── XPath — Navegação: Produção → Resultados ──────────────────────────────────
XPATH_MENU_PRODUCAO = os.getenv(
    "XPATH_MENU_PRODUCAO",
    "//li[@class='nav-item dropdown show']//a[@id='dropdown05']"
).strip()

XPATH_SUBMENU_RESULTADOS = os.getenv(
    "XPATH_SUBMENU_RESULTADOS",
    "//a[normalize-space()='Resultados']"
).strip()

# ── XPath — Filtros na tela de Resultados ─────────────────────────────────────
XPATH_ID_INICIAL = os.getenv(
    "XPATH_ID_INICIAL",
    "//input[@id='idPedidoInicialFiltro']"
).strip()

XPATH_ID_FINAL = os.getenv(
    "XPATH_ID_FINAL",
    "//input[@id='idPedidoFinalFiltro']"
).strip()

# ── XPath — Botão PDF do laudo na tela de Resultados ─────────────────────────
# tr[1] = primeira linha de resultado após filtrar pelo pedido específico
# button[2] = segundo botão da linha (PDF)
XPATH_BTN_PDF = os.getenv(
    "XPATH_BTN_PDF",
    "//tbody/tr[1]/td[4]/div[1]/div[1]/button[2]"
).strip()

# ── Armazenamento ──────────────────────────────────────────────────────────────
PASTA_LAUDOS = Path(_exigir("PASTA_LAUDOS"))
PASTA_LAUDOS.mkdir(parents=True, exist_ok=True)

# ── Mensagem WhatsApp ──────────────────────────────────────────────────────────
MSG_TEMPLATE = _exigir("MSG_TEMPLATE")
