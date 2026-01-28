import streamlit as st
import pandas as pd
import tempfile
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.validation import (
    detectar_encoding,
    detectar_delimitador,
    validar_csv_completo
)

@st.cache_data
def carregar_template():
    with open("database/template.json", "r") as f:
        return json.load(f)

@st.cache_data(show_spinner="Processando arquivo...") 
def processar_arquivo(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name

    try:
        encoding_detectado = detectar_encoding(tmp_path)
        delimitador_detectado = detectar_delimitador(tmp_path)
        
        # Otimização de leitura (apenas ler o necessário se o arquivo for gigante)
        df = pd.read_csv(tmp_path, encoding=encoding_detectado, sep=delimitador_detectado)
        
        template = carregar_template()
        resultado = validar_csv_completo(tmp_path, template)
        erros_duplicata = detectar_colisoes_validacao(df, resultado)
        
        if erros_duplicata:
            resultado["valido"] = False
            resultado["detalhes"].extend(erros_duplicata)
            resultado["total_erros"] = len(resultado["detalhes"])
        
        return df, encoding_detectado, delimitador_detectado, resultado
        
    finally:
        # Garante a limpeza do arquivo temporário
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# detectar_colunas_duplicadas
def detectar_colisoes_validacao(df: pd.DataFrame, resultado_validacao: dict) -> list:
    if "erro_leitura" in [e["tipo"] for e in resultado_validacao.get("detalhes", [])]:
        return []

    erro_nomes = next((e for e in resultado_validacao.get("detalhes", []) if e["tipo"] == "nomes_colunas"), None)
    
    if not erro_nomes or "mapeamento" not in erro_nomes:
        return []

    mapeamento = erro_nomes["mapeamento"] 
    colunas_existentes = set(df.columns)
    
    mapa_destino_origens = {}

    for origem, destino in mapeamento.items():
        if destino not in mapa_destino_origens:
            mapa_destino_origens[destino] = []
        
            if destino in colunas_existentes:
                mapa_destino_origens[destino].append(destino)
        
        mapa_destino_origens[destino].append(origem)

    conflitos = {
        dest: origs 
        for dest, origs in mapa_destino_origens.items() 
        if len(origs) > 1
    }

    erros_extras = []
    
    if conflitos:
        erros_extras.append({
            "tipo": "colunas_duplicadas",
            "conflitos": conflitos,
            "mensagem": "Múltiplas colunas referem-se ao mesmo campo final."
        })

    return erros_extras