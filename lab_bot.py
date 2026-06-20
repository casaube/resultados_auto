"""
lab_bot.py — Automação do sistema web Solo & Companhia via Selenium (Microsoft Edge)

Fluxo em lote:
  1. Abre o navegador e aguarda login manual do usuário
  2. Navega para Comercial → Pedidos
  3. Filtra por data e lê a tabela: coleta pedidos FINALIZADO + FATURADO
  4. Para cada pedido qualificado:
     a. Clica no pedido → captura telefone do cliente na tela de detalhe
     b. Verifica se TODAS as amostras são do tipo 'Solo'
     c. Navega para Produção → Resultados
     d. Filtra pelo número do pedido → baixa PDF da seção 'Solos'
     e. Salva PDF localmente
"""

import logging
import time
from pathlib import Path
from datetime import date, datetime
from typing import Optional

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException
)
from webdriver_manager.microsoft import EdgeChromiumDriverManager

import config

logger = logging.getLogger(__name__)

TIMEOUT = 20   # segundos para aguardar elementos
TIMEOUT_LOGIN = 180  # 3 minutos para o usuário fazer login manualmente


# ──────────────────────────────────────────────────────────────────────────────
# Inicialização do driver
# ──────────────────────────────────────────────────────────────────────────────

def iniciar_driver() -> webdriver.Edge:
    """
    Inicia o Microsoft Edge.
    Usa o perfil padrão do usuário para que o WhatsApp Web já esteja autenticado.
    """
    import os
    options = Options()

    perfil_edge = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        r"Microsoft\Edge\User Data"
    )
    options.add_argument(f"--user-data-dir={perfil_edge}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Força download de PDFs ao invés de visualização inline
    prefs = {
        "download.default_directory": str(config.PASTA_LAUDOS),
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    driver.maximize_window()
    logger.info("Driver Edge iniciado.")
    return driver


# ──────────────────────────────────────────────────────────────────────────────
# Login manual
# ──────────────────────────────────────────────────────────────────────────────

def aguardar_login_manual(driver: webdriver.Edge) -> None:
    """
    Abre a URL do sistema e aguarda o usuário fazer login manualmente.
    O script fica em pausa até detectar que a URL mudou (indicando login bem-sucedido)
    OU até o usuário pressionar Enter no terminal.
    """
    logger.info(f"Abrindo sistema: {config.LAB_URL}")
    driver.get(config.LAB_URL)

    print("\n" + "=" * 60)
    print("  🔐 FAÇA O LOGIN NO SISTEMA AGORA")
    print("  Após entrar, pressione ENTER aqui para continuar...")
    print("=" * 60 + "\n")
    input()

    logger.info("Login confirmado pelo usuário. Prosseguindo...")
    time.sleep(1)


# ──────────────────────────────────────────────────────────────────────────────
# Navegação — Comercial → Pedidos
# ──────────────────────────────────────────────────────────────────────────────

def navegar_para_pedidos(driver: webdriver.Edge) -> None:
    """
    Clica no menu Comercial e depois no sub-menu Pedidos.
    """
    wait = WebDriverWait(driver, TIMEOUT)
    logger.info("Navegando para Comercial → Pedidos...")

    # Clica no menu Comercial
    menu_comercial = wait.until(
        EC.element_to_be_clickable((By.XPATH, config.XPATH_MENU_COMERCIAL))
    )
    menu_comercial.click()
    time.sleep(0.8)

    # Clica no sub-menu Pedidos
    submenu_pedidos = wait.until(
        EC.element_to_be_clickable((By.XPATH, config.XPATH_SUBMENU_PEDIDOS))
    )
    submenu_pedidos.click()
    logger.info("Tela de Pedidos carregada.")
    time.sleep(1.5)


# ──────────────────────────────────────────────────────────────────────────────
# Filtro de data na tela de Pedidos
# ──────────────────────────────────────────────────────────────────────────────

def filtrar_pedidos_por_data(
    driver: webdriver.Edge,
    data_inicio: str,
    data_fim: str
) -> None:
    """
    Preenche os campos de data inicial e final e clica em Filtrar.

    Args:
        data_inicio: Data no formato dd/mm/aaaa
        data_fim:    Data no formato dd/mm/aaaa
    """
    wait = WebDriverWait(driver, TIMEOUT)
    logger.info(f"Filtrando pedidos de {data_inicio} a {data_fim}...")

    # Campo data inicial
    campo_inicio = wait.until(
        EC.element_to_be_clickable((By.XPATH, config.XPATH_FILTRO_DATA_INICIO))
    )
    campo_inicio.clear()
    campo_inicio.send_keys(data_inicio)

    # Campo data final
    campo_fim = driver.find_element(By.XPATH, config.XPATH_FILTRO_DATA_FIM)
    campo_fim.clear()
    campo_fim.send_keys(data_fim)

    # Clica em Filtrar
    btn_filtrar = driver.find_element(By.XPATH, config.XPATH_BTN_FILTRAR)
    btn_filtrar.click()
    logger.info("Filtro aplicado. Aguardando tabela carregar...")
    time.sleep(2)


# ──────────────────────────────────────────────────────────────────────────────
# Leitura da tabela de Pedidos — coleta pedidos qualificados
# ──────────────────────────────────────────────────────────────────────────────

def ler_pedidos_qualificados(driver: webdriver.Edge) -> list[dict]:
    """
    Varre TODAS as linhas da tabela de Pedidos (incluindo paginação)
    e retorna apenas os pedidos que atendem a TODOS os critérios:
      - Coluna Status (td[7])    = TEXTO_STATUS_FINALIZADO (ex: 'FINALIZADO')
      - Coluna Faturado (td[9])  = ícone com classe CLASSE_FATURADO_SIM (ex: 'fa-check')

    Retorna lista de dicts: [{'numero': '4836', 'linha_idx': 1, ...}, ...]
    """
    qualificados = []
    pagina = 1

    while True:
        logger.info(f"Lendo página {pagina} da tabela de pedidos...")
        time.sleep(1.5)

        linhas = driver.find_elements(By.XPATH, "//tbody/tr")
        if not linhas:
            logger.info("Nenhuma linha encontrada na tabela.")
            break

        for i, linha in enumerate(linhas, start=1):
            try:
                celulas = linha.find_elements(By.TAG_NAME, "td")
                if len(celulas) < 9:
                    continue  # linha inválida/cabeçalho fantasma

                # ── Coluna Pedido (índice 2 = td[3]) ──
                numero_pedido = celulas[2].text.strip()
                if not numero_pedido:
                    continue

                # ── Coluna Status (índice 6 = td[7]) ──
                status = celulas[6].text.strip().upper()

                # ── Coluna Faturado (índice 8 = td[9]) — ícone <i> ──
                try:
                    icone_faturado = celulas[8].find_element(By.TAG_NAME, "i")
                    classes_icone = icone_faturado.get_attribute("class") or ""
                    faturado = config.CLASSE_FATURADO_SIM.lower() in classes_icone.lower()
                except NoSuchElementException:
                    faturado = False

                status_ok = config.TEXTO_STATUS_FINALIZADO.upper() in status
                logger.debug(
                    f"Linha {i}: Pedido={numero_pedido} | "
                    f"Status='{status}' ({status_ok}) | "
                    f"Faturado={faturado}"
                )

                if status_ok and faturado:
                    qualificados.append({
                        "numero": numero_pedido,
                        "linha_elemento": linha,
                    })
                    logger.info(f"  ✔ Pedido {numero_pedido} qualificado (FINALIZADO + FATURADO)")

            except Exception as e:
                logger.warning(f"Erro ao ler linha {i}: {e}")
                continue

        # ── Verifica se há próxima página ──
        try:
            btn_proxima = driver.find_element(
                By.XPATH, "//a[contains(@class,'next') and not(contains(@class,'disabled'))]"
            )
            btn_proxima.click()
            pagina += 1
        except NoSuchElementException:
            logger.info(f"Fim da paginação. Total de páginas lidas: {pagina}")
            break

    logger.info(f"Total de pedidos qualificados encontrados: {len(qualificados)}")
    return qualificados


# ──────────────────────────────────────────────────────────────────────────────
# Captura de telefone na tela de detalhe do pedido
# ──────────────────────────────────────────────────────────────────────────────

def obter_dados_pedido(driver: webdriver.Edge, linha_elemento) -> dict:
    """
    Clica no pedido na tabela para abrir a tela de detalhe,
    captura o telefone e nome do cliente (campos <input> — lidos via atributo 'value'),
    depois volta para a listagem.

    Retorna dict: {'telefone': '62998887777', 'cliente': 'Nome do Cliente'}
    """
    wait = WebDriverWait(driver, TIMEOUT)
    url_listagem = driver.current_url

    # Tenta clicar no link da coluna Pedido (td[3]); se não houver link, clica na célula
    try:
        try:
            link_pedido = linha_elemento.find_element(By.XPATH, ".//td[3]/a")
        except NoSuchElementException:
            link_pedido = linha_elemento.find_element(By.XPATH, ".//td[3]")
        link_pedido.click()
    except Exception:
        linha_elemento.click()

    time.sleep(2)

    dados = {"telefone": "", "cliente": ""}

    # ── Telefone: campo <input> — lido via atributo 'value' ───────────────────
    try:
        elemento_tel = wait.until(
            EC.presence_of_element_located((By.XPATH, config.XPATH_TELEFONE_CLIENTE))
        )
        # Campos <input> têm o valor em .get_attribute("value"), não em .text
        tel_bruto = elemento_tel.get_attribute("value") or ""
        # Remove tudo que não for dígito para garantir formato correto no WhatsApp
        dados["telefone"] = "".join(c for c in tel_bruto if c.isdigit())
        logger.info(f"Telefone capturado: '{tel_bruto}' → '{dados['telefone']}'")
    except (TimeoutException, NoSuchElementException):
        logger.warning(
            "Telefone do cliente não encontrado na tela do pedido. "
            "Verifique XPATH_TELEFONE_CLIENTE no .env."
        )

    # ── Nome do cliente: campo <input> — lido via atributo 'value' ───────────
    try:
        elemento_nome = driver.find_element(By.XPATH, config.XPATH_NOME_CLIENTE)
        dados["cliente"] = (elemento_nome.get_attribute("value") or "").strip()
        logger.info(f"Nome capturado: '{dados['cliente']}'")
    except NoSuchElementException:
        logger.warning(
            "Nome do cliente não encontrado. "
            "Verifique XPATH_NOME_CLIENTE no .env."
        )

    # Volta para a listagem de pedidos
    driver.get(url_listagem)
    time.sleep(2)

    return dados


# ──────────────────────────────────────────────────────────────────────────────
# Verificação de amostras Solo na tela de detalhe do pedido
# ──────────────────────────────────────────────────────────────────────────────

def verificar_amostras_solo(driver: webdriver.Edge) -> tuple[bool, list[str]]:
    """
    Lê a tabela de amostras do pedido e verifica se TODAS são do tipo configurado
    em TIPO_AMOSTRA_PERMITIDO (padrão: 'Solo').

    A coluna de tipo é identificada pelo cabeçalho HEADER_COLUNA_TIPO_AMOSTRA (padrão: 'Tipo').

    Returns:
        (True, tipos_encontrados)  — se todos forem Solo
        (False, tipos_encontrados) — se houver outros tipos
    """
    wait = WebDriverWait(driver, TIMEOUT)

    try:
        tabela = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, config.SELETOR_TABELA_AMOSTRAS)
            )
        )
    except TimeoutException:
        raise RuntimeError(
            "Tabela de amostras não encontrada. "
            "Verifique SELETOR_TABELA_AMOSTRAS no .env."
        )

    # Localiza índice da coluna 'Tipo'
    cabecalhos = tabela.find_elements(
        By.CSS_SELECTOR,
        "thead th, thead td, tr:first-child th, tr:first-child td"
    )
    indice_coluna = None
    alvo = config.HEADER_COLUNA_TIPO_AMOSTRA.lower()

    for idx, th in enumerate(cabecalhos):
        if alvo in th.text.lower().strip():
            indice_coluna = idx
            break

    if indice_coluna is None:
        raise RuntimeError(
            f"Coluna '{config.HEADER_COLUNA_TIPO_AMOSTRA}' não encontrada. "
            f"Cabeçalhos: {[t.text for t in cabecalhos]}"
        )

    linhas = tabela.find_elements(By.CSS_SELECTOR, "tbody tr")
    if not linhas:
        linhas = tabela.find_elements(By.TAG_NAME, "tr")[1:]

    tipos_encontrados = []
    tipo_permitido = config.TIPO_AMOSTRA_PERMITIDO.lower()

    for linha in linhas:
        celulas = linha.find_elements(By.CSS_SELECTOR, "td, th")
        if indice_coluna < len(celulas):
            tipo = celulas[indice_coluna].text.strip()
            if tipo:
                tipos_encontrados.append(tipo)

    if not tipos_encontrados:
        raise RuntimeError("Não foi possível ler os tipos de amostra da tabela.")

    tipos_divergentes = [t for t in tipos_encontrados if tipo_permitido not in t.lower()]
    todas_solo = len(tipos_divergentes) == 0

    logger.info(
        f"Tipos encontrados: {tipos_encontrados} | "
        f"Todos '{config.TIPO_AMOSTRA_PERMITIDO}': {todas_solo}"
        + (f" | Divergentes: {tipos_divergentes}" if not todas_solo else "")
    )

    return todas_solo, tipos_encontrados


# ──────────────────────────────────────────────────────────────────────────────
# Navegação — Produção → Resultados
# ──────────────────────────────────────────────────────────────────────────────

def navegar_para_resultados(driver: webdriver.Edge) -> None:
    """
    Clica no menu Produção e depois no sub-menu Resultados.
    """
    wait = WebDriverWait(driver, TIMEOUT)
    logger.info("Navegando para Produção → Resultados...")

    menu_producao = wait.until(
        EC.element_to_be_clickable((By.XPATH, config.XPATH_MENU_PRODUCAO))
    )
    menu_producao.click()
    time.sleep(0.8)

    submenu_resultados = wait.until(
        EC.element_to_be_clickable((By.XPATH, config.XPATH_SUBMENU_RESULTADOS))
    )
    submenu_resultados.click()
    logger.info("Tela de Resultados carregada.")
    time.sleep(1.5)


# ──────────────────────────────────────────────────────────────────────────────
# Filtro por número do pedido em Resultados
# ──────────────────────────────────────────────────────────────────────────────

def filtrar_resultado_por_pedido(driver: webdriver.Edge, numero_pedido: str) -> None:
    """
    Preenche Id Inicial = Id Final = numero_pedido e clica em Filtrar.
    """
    wait = WebDriverWait(driver, TIMEOUT)
    logger.info(f"Filtrando resultados pelo pedido {numero_pedido}...")

    campo_id_inicial = wait.until(
        EC.element_to_be_clickable((By.XPATH, config.XPATH_ID_INICIAL))
    )
    campo_id_inicial.clear()
    campo_id_inicial.send_keys(numero_pedido)

    campo_id_final = driver.find_element(By.XPATH, config.XPATH_ID_FINAL)
    campo_id_final.clear()
    campo_id_final.send_keys(numero_pedido)

    btn_filtrar = driver.find_element(By.XPATH, config.XPATH_BTN_FILTRAR)
    btn_filtrar.click()
    logger.info("Filtro de pedido aplicado. Aguardando resultados...")
    time.sleep(2)


# ──────────────────────────────────────────────────────────────────────────────
# Download do laudo PDF na tela de Resultados
# ──────────────────────────────────────────────────────────────────────────────

def baixar_laudo_resultados(driver: webdriver.Edge, numero_pedido: str) -> Optional[Path]:
    """
    Clica no botão PDF da primeira linha de resultados (seção Solos).
    O PDF abre em nova aba — capturamos a URL e baixamos via requests
    reutilizando os cookies da sessão Selenium.

    Retorna o caminho local do PDF salvo, ou None se não encontrado.
    """
    wait = WebDriverWait(driver, TIMEOUT)
    abas_antes = set(driver.window_handles)

    try:
        btn_pdf = wait.until(
            EC.element_to_be_clickable((By.XPATH, config.XPATH_BTN_PDF))
        )
        btn_pdf.click()
        logger.info("Botão PDF clicado. Aguardando nova aba...")
    except TimeoutException:
        logger.warning(
            f"Botão PDF não encontrado para o pedido {numero_pedido}. "
            "Verifique XPATH_BTN_PDF no .env."
        )
        return None

    # Aguarda a nova aba abrir
    try:
        wait.until(lambda d: set(d.window_handles) != abas_antes)
    except TimeoutException:
        logger.warning("A aba do PDF não abriu a tempo.")
        return None

    nova_aba = (set(driver.window_handles) - abas_antes).pop()
    driver.switch_to.window(nova_aba)
    time.sleep(2)

    url_pdf = driver.current_url
    logger.info(f"URL do PDF: {url_pdf}")

    # Reutiliza cookies da sessão para baixar o PDF autenticado
    sessao = requests.Session()
    for cookie in driver.get_cookies():
        sessao.cookies.set(cookie["name"], cookie["value"])

    try:
        resposta = sessao.get(url_pdf, timeout=30)
        resposta.raise_for_status()
    except Exception as e:
        logger.error(f"Erro ao baixar PDF: {e}")
        driver.close()
        driver.switch_to.window(list(driver.window_handles)[0])
        return None

    data_hoje = date.today().strftime("%Y-%m-%d")
    nome_arquivo = f"laudo_{numero_pedido}_{data_hoje}.pdf"
    caminho_pdf = config.PASTA_LAUDOS / nome_arquivo
    caminho_pdf.write_bytes(resposta.content)
    logger.info(f"PDF salvo: {caminho_pdf}")

    # Fecha aba do PDF e volta para Resultados
    driver.close()
    driver.switch_to.window(list(driver.window_handles)[0])

    return caminho_pdf
