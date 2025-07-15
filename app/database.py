import sqlite3
from pathlib import Path
from app.settings import DB_PATH
from datetime import datetime

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leituras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            valor REAL NOT NULL,
            porta TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    conn.commit()
    conn.close()

def salvar_leitura(valor: float, porta: str):
    """Salva uma nova leitura no banco."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO leituras (valor, porta) VALUES (?, ?)",
        (valor, porta)
    )
    conn.commit()
    conn.close()

def buscar_leituras(porta: str = None, limite: int = 100):
    """Busca as últimas leituras, filtradas por porta (opcional)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if porta:
        cursor.execute(
            "SELECT valor, porta, timestamp FROM leituras WHERE porta = ? ORDER BY timestamp DESC LIMIT ?",
            (porta, limite)
        )
    else:
        cursor.execute(
            "SELECT valor, porta, timestamp FROM leituras ORDER BY timestamp DESC LIMIT ?",
            (limite,)
        )
    
    leituras = cursor.fetchall()
    conn.close()
    return leituras

def buscar_picos(limite: int = 10):
    """Busca os maiores picos de torque registrados."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT valor, porta, timestamp FROM leituras ORDER BY valor DESC LIMIT ?",
        (limite,)
    )
    picos = cursor.fetchall()
    conn.close()
    return picos

def buscar_leituras_por_data(data_inicio: str, data_fim: str, porta: str = None):
    """Busca leituras entre duas datas (formato: 'YYYY-MM-DD HH:MM:SS')"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT valor, porta, timestamp 
        FROM leituras 
        WHERE timestamp BETWEEN ? AND ?
    """
    params = [data_inicio, data_fim]
    
    if porta:
        query += " AND porta = ?"
        params.append(porta)
    
    query += " ORDER BY timestamp DESC"
    cursor.execute(query, params)
    
    leituras = cursor.fetchall()
    conn.close()
    return leituras