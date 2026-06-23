"""
main.py — Automação em LOTE da rotina diária do Laboratório Solo & Companhia

Fluxo:
  1. Abre Edge e aguarda login manual
  2. Navega Comercial → Pedidos → filtra por data
  3. Escaneia a tabela: coleta pedidos FINALIZADO + FATURADO
  4. Para cada pedido qualificado:
     - Abre o pedido → captura telefone e nome do cliente
     - Verifica se todas as amostras são do tipo 'Solo'
     - Navega Produção → Resultados → filtra pelo número
     - Baixa o PDF do laudo
     - Envia WhatsApp (texto + PDF)
  5. Exibe resumo final

Uso:
    python main.py
    python main.py --data-inicio 01/06/2026 --data-fim 20/06/2026
    python main.py --data-inicio 19/06/2026  (data fim = hoje automaticamente)
    python main.py --sem-whatsapp             (só baixa PDFs, sem envio)
"""

import argparse
import logging
import sys
from datetime import date

import lab_bot
import whatsapp_bot
import config
import tracker



# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("lab_automation.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


# ──────────────────────────────────────────────────────────────────────────────
# Argumentos de linha de comando
# ──────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automação em lote — Laboratório Solo & Companhia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data-inicio",
        default=None,
        help="Data inicial do filtro (dd/mm/aaaa). Padrão: Hoje menos DIAS_ATRAS definido no .env",
    )
    parser.add_argument(
        "--data-fim",
        default=None,
        help="Data final do filtro (dd/mm/aaaa). Padrão: hoje",
    )
    parser.add_argument(
        "--sem-whatsapp",
        action="store_true",
        help="Só baixa os PDFs, sem enviar WhatsApp",
    )
    return parser.parse_args()



# ──────────────────────────────────────────────────────────────────────────────
# Fluxo principal
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    sem_whatsapp = args.sem_whatsapp
    data_hoje = date.today().strftime("%d/%m/%Y")

    # Calcula as datas de acordo com os parâmetros ou arquivo .env
    from datetime import timedelta
    if args.data_inicio is None:
        data_inicio_dt = date.today() - timedelta(days=config.DIAS_ATRAS)
        data_inicio = data_inicio_dt.strftime("%d/%m/%Y")
    else:
        data_inicio = args.data_inicio

    if args.data_fim is None:
        data_fim = data_hoje
    else:
        data_fim = args.data_fim


    logger.info("=" * 65)
    logger.info("  🧪 AUTOMAÇÃO LABORATÓRIO SOLO & COMPANHIA — MODO LOTE")
    logger.info(f"  Período  : {data_inicio} → {data_fim}")
    logger.info(f"  Tipo     : apenas pedidos 100% '{config.TIPO_AMOSTRA_PERMITIDO}'")
    logger.info(f"  WhatsApp : {'DESATIVADO' if sem_whatsapp else 'ATIVADO'}")
    logger.info("=" * 65)

    driver = None

    # Contadores para o resumo final
    processados   = []
    ignorados_tipo = []
    sem_telefone  = []
    erros         = []

    try:
        # Inicializa o rastreador de envios (SQLite + CSV)
        tracker.inicializar_rastreador()

        # ── 1. Inicia o Edge e aguarda login manual ───────────────────────────

        logger.info("ETAPA 1 — Iniciando navegador Edge...")
        driver = lab_bot.iniciar_driver()
        lab_bot.aguardar_login_manual(driver)

        # ── 2. Navega para Comercial → Pedidos e filtra ───────────────────────
        logger.info("ETAPA 2 — Navegando para Pedidos e aplicando filtro de data...")
        lab_bot.navegar_para_pedidos(driver)
        lab_bot.filtrar_pedidos_por_data(driver, data_inicio, data_fim)

        # ── 3. Lê a tabela e coleta pedidos qualificados ──────────────────────
        logger.info("ETAPA 3 — Escaneando tabela de pedidos (FINALIZADO + FATURADO)...")
        pedidos_qualificados = lab_bot.ler_pedidos_qualificados(driver)

        if not pedidos_qualificados:
            logger.info("⚠  Nenhum pedido FINALIZADO + FATURADO encontrado no período.")
            logger.info("   Encerrando sem processar.")
            return

        logger.info(
            f"\n{'─'*65}\n"
            f"  📋 {len(pedidos_qualificados)} pedido(s) qualificado(s) encontrado(s):\n"
            + "\n".join(f"     • Pedido {p['numero']}" for p in pedidos_qualificados)
            + f"\n{'─'*65}"
        )

        # ── 4. Processa cada pedido ───────────────────────────────────────────
        for idx, pedido in enumerate(pedidos_qualificados, start=1):
            numero = pedido["numero"]

            if tracker.pedido_ja_enviado(numero):
                logger.info(f"⏭  Pedido {numero} já enviado anteriormente. Pulando...")
                continue

            logger.info(f"\n{'─'*65}")
            logger.info(f"  📄 PROCESSANDO {idx}/{len(pedidos_qualificados)}: Pedido {numero}")
            logger.info(f"{'─'*65}")


            try:
                # 4a. Abre o pedido e captura telefone + nome do cliente
                logger.info(f"  [4a] Capturando dados do cliente...")
                dados_cliente = lab_bot.obter_dados_pedido(driver, pedido["linha_elemento"])
                nome_cliente = dados_cliente.get("cliente", f"Cliente do Pedido {numero}")
                telefone = dados_cliente.get("telefone", "")

                if not telefone and not sem_whatsapp:
                    logger.warning(
                        f"  ⚠  Telefone não encontrado para o pedido {numero}. "
                        "PDF será salvo, mas WhatsApp não será enviado."
                    )

                # 4b. Verifica tipo de amostras (Solo)
                logger.info(f"  [4b] Verificando tipos de amostra...")
                try:
                    # Reabre o pedido para verificação de amostras
                    pedido["linha_elemento"].find_element(By.XPATH, ".//td[3]").click()
                    import time; time.sleep(1.5)

                    apenas_solo, tipos = lab_bot.verificar_amostras_solo(driver)

                    if not apenas_solo:
                        outros = [t for t in tipos if config.TIPO_AMOSTRA_PERMITIDO.lower() not in t.lower()]
                        logger.warning(
                            f"  ⚠  Pedido {numero} tem amostras de outros tipos: {outros}. "
                            "Ignorando — requer tratamento diferenciado."
                        )
                        ignorados_tipo.append({"numero": numero, "tipos": tipos})
                        driver.back()
                        import time; time.sleep(1)
                        continue

                    logger.info(f"  ✔  Todas as amostras são '{config.TIPO_AMOSTRA_PERMITIDO}'.")
                    driver.back()
                    import time; time.sleep(1)

                except Exception as e_tipo:
                    logger.warning(f"  ⚠  Não foi possível verificar tipo de amostras: {e_tipo}. Prosseguindo...")

                # 4c. Navega para Produção → Resultados
                logger.info(f"  [4c] Navegando para Resultados...")
                lab_bot.navegar_para_resultados(driver)

                # 4d. Filtra pelo número do pedido
                logger.info(f"  [4d] Filtrando pelo pedido {numero}...")
                lab_bot.filtrar_resultado_por_pedido(driver, numero)

                # 4e. Baixa o PDF
                logger.info(f"  [4e] Baixando laudo PDF...")
                caminho_pdf = lab_bot.baixar_laudo_resultados(driver, numero)

                if not caminho_pdf:
                    logger.warning(f"  ⚠  PDF não encontrado para o pedido {numero}.")
                    erros.append({"numero": numero, "erro": "PDF não encontrado"})
                    # Volta para a listagem de pedidos
                    lab_bot.navegar_para_pedidos(driver)
                    lab_bot.filtrar_pedidos_por_data(driver, data_inicio, data_fim)
                    continue

                logger.info(f"  ✔  PDF salvo: {caminho_pdf}")

                # 4f. Envia via WhatsApp
                if not sem_whatsapp and telefone:
                    logger.info(f"  [4f] Enviando WhatsApp para {nome_cliente} ({telefone})...")

                    mensagem = config.MSG_TEMPLATE.format(
                        nome=nome_cliente,
                        numero_pedido=numero,
                        data=data_hoje,
                    )

                    whatsapp_bot.encontrar_aba_whatsapp(driver)
                    whatsapp_bot.abrir_conversa(driver, telefone)
                    whatsapp_bot.enviar_mensagem(driver, mensagem)
                    whatsapp_bot.enviar_arquivo(driver, caminho_pdf)

                    logger.info(f"  ✔  WhatsApp enviado para {nome_cliente}.")
                    tracker.registrar_envio(numero, nome_cliente, telefone, "ENVIADO")
                    processados.append({
                        "numero": numero,
                        "cliente": nome_cliente,
                        "pdf": caminho_pdf,
                        "whatsapp": True,
                    })


                    # Volta ao sistema do laboratório (pode ter mudado de aba)
                    lab_bot.navegar_para_pedidos(driver)
                    lab_bot.filtrar_pedidos_por_data(driver, data_inicio, data_fim)

                elif not sem_whatsapp and not telefone:
                    sem_telefone.append({"numero": numero, "cliente": nome_cliente, "pdf": caminho_pdf})
                    processados.append({
                        "numero": numero,
                        "cliente": nome_cliente,
                        "pdf": caminho_pdf,
                        "whatsapp": False,
                    })
                else:
                    processados.append({
                        "numero": numero,
                        "cliente": nome_cliente,
                        "pdf": caminho_pdf,
                        "whatsapp": False,
                    })

                # Volta para a listagem para o próximo pedido
                lab_bot.navegar_para_pedidos(driver)
                lab_bot.filtrar_pedidos_por_data(driver, data_inicio, data_fim)

            except Exception as e:
                logger.error(f"  ❌ ERRO no pedido {numero}: {e}", exc_info=True)
                erros.append({"numero": numero, "erro": str(e)})
                # Tenta voltar para a listagem e continuar com o próximo
                try:
                    lab_bot.navegar_para_pedidos(driver)
                    lab_bot.filtrar_pedidos_por_data(driver, data_inicio, data_fim)
                except Exception:
                    pass

        # ── 5. Resumo final ───────────────────────────────────────────────────
        logger.info("\n" + "=" * 65)
        logger.info("  ✅ PROCESSAMENTO CONCLUÍDO — RESUMO")
        logger.info("=" * 65)
        logger.info(f"  Total qualificados  : {len(pedidos_qualificados)}")
        logger.info(f"  PDFs baixados       : {len(processados)}")
        logger.info(f"  WhatsApp enviados   : {sum(1 for p in processados if p['whatsapp'])}")
        logger.info(f"  Ignorados (tipo)    : {len(ignorados_tipo)}")
        logger.info(f"  Sem telefone        : {len(sem_telefone)}")
        logger.info(f"  Erros               : {len(erros)}")

        if processados:
            logger.info("\n  📄 PDFs salvos:")
            for p in processados:
                wa = "✔ WA" if p["whatsapp"] else "— sem WA"
                logger.info(f"     • Pedido {p['numero']} — {p['cliente']} — {wa}")

        if ignorados_tipo:
            logger.info("\n  ⚠  Ignorados (amostras de outro tipo):")
            for p in ignorados_tipo:
                logger.info(f"     • Pedido {p['numero']} — tipos: {p['tipos']}")

        if sem_telefone:
            logger.info("\n  📵 Sem telefone (PDF salvo, WhatsApp pendente):")
            for p in sem_telefone:
                logger.info(f"     • Pedido {p['numero']} — {p['cliente']} — {p['pdf']}")

        if erros:
            logger.info("\n  ❌ Erros:")
            for e in erros:
                logger.info(f"     • Pedido {e['numero']} — {e['erro']}")

        logger.info("=" * 65)

    except Exception as erro_geral:
        logger.error(f"❌ ERRO GERAL: {erro_geral}", exc_info=True)
        sys.exit(1)

    finally:
        if driver:
            logger.info("\nEncerrando navegador...")
            driver.quit()


if __name__ == "__main__":
    main()
