"""
Módulo para cache de scripts de correção baseado em similaridade.
"""
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Optional


def gerar_hash_estrutura(colunas: list, erros: list) -> str:
    colunas_ordenadas = sorted(colunas)
    
    tipos_erros = sorted([erro.get("tipo", "") for erro in erros])
    
    estrutura = {
        "colunas": colunas_ordenadas,
        "tipos_erros": tipos_erros
    }
    
    estrutura_json = json.dumps(estrutura, sort_keys=True, ensure_ascii=False)

    hash_obj = hashlib.md5(estrutura_json.encode('utf-8'))
    
    return hash_obj.hexdigest()


def buscar_script_cache(hash_estrutura: str) -> Optional[dict]:
    """
    Busca um script de correção no cache pelo hash.
    
    Args:
        hash_estrutura: Hash gerado pela função gerar_hash_estrutura()
    
    Returns:
        dict com 'script' e 'id' se encontrado, None caso contrário
        
    Exemplo:
        >>> script_info = buscar_script_cache("abc123def456")
        >>> if script_info:
        >>>     print(script_info['script'])
    """
    db_path = Path(__file__).parent.parent.parent / "database" / "transacoes.db"
    
    # Se o banco não existe, retorna None
    if not db_path.exists():
        return None
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, script_python FROM scripts_transformacao WHERE hash_estrutura = ?",
        (hash_estrutura,)
    )
    
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        return {
            "id": resultado["id"],
            "script": resultado["script_python"]
        }
    
    return None
