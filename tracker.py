"""
tracker.py — Gerenciamento do histórico de envios (SQLite + CSV)
Garante que os laudos não sejam reenviados e fornece uma planilha visual para o usuário.
"""

import sqlite3
import csv
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger("tracker")

# Caminhos locais para o banco de dados e para a planilha CSV
DB_PATH = Path(__file__).parent / "historico_envios.db"
CSV_PATH = Path(__file__).parent / "historico_envios.csv"


def inicializar_rastreador() -> None:
    """Cria a tabela SQLite e a planilha CSV se ainda não existirem."""
    # 1. Inicializa o SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS envios (
                pedido_id TEXT PRIMARY KEY,
                cliente TEXT,
                telefone TEXT,
                data_envio TEXT,
                status TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.debug("Banco de dados SQLite inicializado.")
    except Exception as e:
        logger.error(f"Erro ao inicializar o banco de dados SQLite: {e}")

    # 2. Inicializa o CSV (com cabeçalhos)
    try:
        if not CSV_PATH.exists():
            # utf-8-sig garante que acentos e emojis apareçam corretamente no Excel brasileiro
            with open(CSV_PATH, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Data/Hora Envio", "Número do Pedido", "Cliente", "Telefone", "Status"])
            logger.debug("Planilha CSV inicializada com cabeçalho.")
    except Exception as e:
        logger.error(f"Erro ao inicializar a planilha CSV: {e}")


def pedido_ja_enviado(pedido_id: str) -> bool:
    """Verifica no SQLite se o pedido já foi enviado com sucesso."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM envios WHERE pedido_id = ? AND status = 'ENVIADO'", (pedido_id,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado is not None
    except Exception as e:
        logger.error(f"Erro ao verificar envio do pedido {pedido_id} no SQLite: {e}")
        return False


def registrar_envio(pedido_id: str, cliente: str, telefone: str, status: str = "ENVIADO") -> None:
    """Registra o status de envio do pedido tanto no SQLite quanto no arquivo CSV."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # 1. Salva no SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO envios (pedido_id, cliente, telefone, data_envio, status)
            VALUES (?, ?, ?, ?, ?)
        """, (pedido_id, cliente, telefone, agora, status))
        conn.commit()
        conn.close()
        logger.info(f"💾 Status do pedido {pedido_id} ({status}) gravado no SQLite.")
    except Exception as e:
        logger.error(f"Erro ao gravar no SQLite para o pedido {pedido_id}: {e}")

    # 2. Salva no CSV
    try:
        with open(CSV_PATH, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([agora, pedido_id, cliente, telefone, status])
        logger.info(f"📊 Status do pedido {pedido_id} ({status}) adicionado à planilha CSV.")
    except Exception as e:
        logger.error(f"Erro ao adicionar na planilha CSV para o pedido {pedido_id}: {e}")
