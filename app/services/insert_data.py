import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict

def inserir_transacoes(df: pd.DataFrame) -> Dict:
    db_path = Path(__file__).parent.parent.parent / "database" / "transacoes.db"
    conn = None
        
    try:
        df["id_transacao"] = df["id_transacao"].astype(str).str.strip()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        ids_transacao = df['id_transacao'].astype(str).tolist()
        placeholders = ','.join(['?'] * len(ids_transacao))
        
        query_check = f"SELECT id_transacao FROM transacoes_financeiras WHERE id_transacao IN ({placeholders})"
        cursor.execute(query_check, ids_transacao)
        
        ids_existentes = set(row[0] for row in cursor.fetchall())
        
        novos_registros = []
        erros = []
        registros_duplicados = 0
        
        for index, row in df.iterrows():
            id_transacao = row['id_transacao']
            if id_transacao in ids_existentes:
                registros_duplicados += 1
                erros.append({
                    "linha": index + 1,
                    "id_transacao": id_transacao,
                    "erro": "ID duplicado (já existe no banco)"
                })
                continue
            
            try:             
                dados_tupla = (
                    id_transacao,
                    row['data_transacao'],
                    float(row['valor']),
                    row.get('tipo'),
                    row.get('categoria'),
                    row.get('descricao'),
                    row['conta_origem'],
                    row.get('conta_destino'),
                    row.get('status')
                )
                novos_registros.append(dados_tupla)
                
            except Exception as e:
                erros.append({
                    "linha": index + 1,
                    "id_transacao": id_transacao,
                    "erro": str(e)
                })
        
        if novos_registros:
            cursor.executemany(
                """
                INSERT INTO transacoes_financeiras 
                (id_transacao, data_transacao, valor, tipo, categoria, 
                 descricao, conta_origem, conta_destino, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                novos_registros
            )
            conn.commit()
        
        return {
            "sucesso": True, 
            "registros_inseridos": len(novos_registros),
            "registros_duplicados": registros_duplicados,
            "total_registros": len(df),
            "erros": erros
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        
        return {
            "sucesso": False,
            "registros_inseridos": 0,
            "registros_duplicados": 0,
            "total_registros": len(df),
            "erros": [{"erro": f"Erro fatal no banco: {str(e)}"}]
        }
    
    finally:
        if conn:
            conn.close()

def registrar_log_ingestao(arquivo_nome: str, registros_total: int, registros_sucesso: int, registros_erro: int,
                           usou_ia: bool, script_id: int = None, duracao_segundos: float = 0.0) -> bool:
    
    db_path = Path(__file__).parent.parent.parent / "database" / "transacoes.db"
    conn = None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO log_ingestao 
            (arquivo_nome, registros_total, registros_sucesso, registros_erro, 
             usou_ia, script_id, duracao_segundos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                arquivo_nome,
                registros_total,
                registros_sucesso,
                registros_erro,
                usou_ia,
                script_id,
                duracao_segundos
            )
        )
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Erro ao registrar log de ingestão: {e}")
        return False
        
    finally:
        if conn:
            conn.close()
