"""
whatsapp_bot.py — Automação do WhatsApp Web via Selenium (Microsoft Edge)

Pré-requisito: O WhatsApp Web deve estar aberto e autenticado no Edge
antes de executar o script. O robô localiza a aba existente e interage com ela.
"""

import logging
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)

# URL base do WhatsApp Web
WHATSAPP_URL = "https://web.whatsapp.com"

# Tempo máximo (segundos) para aguardar elementos carregarem
TIMEOUT = 30

# Seletores do WhatsApp Web (atualizados — podem mudar com updates do WA)
SEL_CAMPO_TEXTO = 'div[contenteditable="true"][data-tab="10"]'
SEL_BTN_ANEXO = 'span[data-icon="attach-menu-plus"]'
SEL_INPUT_ARQUIVO = 'input[accept*="application/pdf"]'
SEL_BTN_ENVIAR_ARQUIVO = 'span[data-icon="send"]'
SEL_CONVERSA_CARREGADA = 'header[data-testid="conversation-header"]'


# ──────────────────────────────────────────────────────────────────────────────
# Localização da aba do WhatsApp Web
# ──────────────────────────────────────────────────────────────────────────────

def encontrar_aba_whatsapp(driver: webdriver.Edge) -> None:
    """
    Varre todas as abas abertas no Edge e muda o foco para a aba
    que contém o WhatsApp Web. Lança erro se não encontrar.
    """
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if WHATSAPP_URL in driver.current_url:
            logger.info(f"Aba do WhatsApp Web encontrada: {driver.current_url}")
            return

    raise RuntimeError(
        "Aba do WhatsApp Web não encontrada no Edge. \n"
        "Abra https://web.whatsapp.com e faça o login antes de executar o script."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Abertura de conversa
# ──────────────────────────────────────────────────────────────────────────────

def abrir_conversa(driver: webdriver.Edge, telefone: str) -> None:
    """
    Abre a conversa com o número informado usando o deep link do WhatsApp Web.
    O número deve estar no formato internacional sem '+' nem espaços.
    Exemplo: 5511987654321
    """
    # Remove qualquer caractere não numérico do telefone
    numero_limpo = "".join(filter(str.isdigit, telefone))
    url_conversa = f"{WHATSAPP_URL}/send?phone={numero_limpo}"

    logger.info(f"Abrindo conversa com: {numero_limpo}")
    driver.get(url_conversa)

    wait = WebDriverWait(driver, TIMEOUT)

    # Aguarda o cabeçalho da conversa aparecer (indica que carregou)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SEL_CONVERSA_CARREGADA)))
        logger.info("Conversa aberta com sucesso.")
        time.sleep(2)  # pausa extra para garantir que o campo de texto esteja pronto
    except TimeoutException:
        raise RuntimeError(
            f"Não foi possível abrir a conversa com o número {numero_limpo}. \n"
            "Verifique se o número está correto e se o WhatsApp Web está autenticado."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Envio de mensagem de texto
# ──────────────────────────────────────────────────────────────────────────────

def enviar_mensagem(driver: webdriver.Edge, texto: str) -> None:
    """
    Digita e envia uma mensagem de texto na conversa aberta.
    Suporta múltiplas linhas — cada '\n' no texto vira Shift+Enter no WhatsApp.
    """
    wait = WebDriverWait(driver, TIMEOUT)

    campo_texto = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_CAMPO_TEXTO))
    )
    campo_texto.click()

    # Digita o texto linha por linha (Shift+Enter para quebra de linha, Enter para enviar)
    linhas = texto.split("\n")
    for i, linha in enumerate(linhas):
        campo_texto.send_keys(linha)
        if i < len(linhas) - 1:
            campo_texto.send_keys(Keys.SHIFT + Keys.RETURN)

    campo_texto.send_keys(Keys.RETURN)
    logger.info("Mensagem de texto enviada.")
    time.sleep(1)


# ──────────────────────────────────────────────────────────────────────────────
# Envio do PDF como anexo
# ──────────────────────────────────────────────────────────────────────────────

def enviar_arquivo(driver: webdriver.Edge, caminho_pdf: Path) -> None:
    """
    Envia o arquivo PDF como anexo na conversa aberta no WhatsApp Web.

    Estratégia:
    1. Clica no botão de anexo (clipe)
    2. Localiza o input de arquivo oculto
    3. Envia o caminho absoluto do PDF para o input
    4. Aguarda o preview do arquivo e clica em Enviar
    """
    wait = WebDriverWait(driver, TIMEOUT)
    caminho_absoluto = str(caminho_pdf.resolve())

    logger.info(f"Anexando PDF: {caminho_absoluto}")

    # Clica no botão de anexo
    btn_anexo = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_BTN_ANEXO))
    )
    btn_anexo.click()
    time.sleep(1)

    # Localiza o input de arquivo (pode estar oculto — usamos JS para torná-lo visível)
    try:
        input_arquivo = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SEL_INPUT_ARQUIVO))
        )
        # Garante visibilidade do input via JavaScript
        driver.execute_script("arguments[0].style.display = 'block';", input_arquivo)
        input_arquivo.send_keys(caminho_absoluto)
        logger.info("Arquivo selecionado no input.")
    except TimeoutException:
        raise RuntimeError(
            "Não foi possível localizar o input de arquivo no WhatsApp Web. "
            "O seletor pode estar desatualizado. Verifique SEL_INPUT_ARQUIVO em whatsapp_bot.py."
        )

    # Aguarda o preview do arquivo aparecer e clica em Enviar
    time.sleep(3)  # aguarda o WhatsApp processar o arquivo
    btn_enviar = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_BTN_ENVIAR_ARQUIVO))
    )
    btn_enviar.click()
    logger.info("PDF enviado como anexo com sucesso.")
    time.sleep(2)
