import streamlit as st
import json
import pandas as pd
from openai import OpenAI
from pathlib import Path
import os
from dotenv import load_dotenv
from app.services.script_cache import gerar_hash_estrutura, buscar_script_cache
from app.utils.data_handler import carregar_template
from app.utils.ui_components import formatar_titulo_erro

def _construir_instrucoes_dinamicas(detalhes_erros):
    instrucoes = []
    
    for erro in detalhes_erros:
        tipo = erro.get("tipo")
        
        if tipo == "colunas_faltando":
            cols = erro.get("colunas", [])
            cols_str = ", ".join([f"'{c}'" for c in cols])
            instrucoes.append(
                f"CRITICO - COLUNAS FALTANDO: O DataFrame NAO possui as colunas obrigatorias [{cols_str}]. "
                f"Voce DEVE cria-las explicitamente. Preencha com None (objeto Python nativo) para garantir compatibilidade com SQL. NAO use pd.NA."
            )
            
        elif tipo == "nomes_colunas":
            mapeamento = erro.get("mapeamento", {})
            if mapeamento:
                instrucoes.append(
                    f"RENOMEACAO: As colunas estao incorretas. Use examente este mapeamento no rename: {json.dumps(mapeamento)}."
                )

        elif tipo == "formato_valor":
            instrucoes.append(
                "FORMATACAO DE VALOR: Identifique colunas monetarias (ex: com 'R$', pontos de milhar). "
                "Converta para float: remova 'R$', remova pontos, substitua virgula por ponto."
            )
            
        elif tipo == "formato_data":
            instrucoes.append(
                "FORMATACAO DE DATA: Converta colunas de data para datetime e depois para string 'YYYY-MM-DD'. "
                "Use pd.to_datetime(..., dayfirst=True, errors='coerce')."
            )
            
        elif tipo == "duplicatas":
            instrucoes.append("DUPLICATAS: Remova linhas duplicadas mantendo a primeira ocorrencia (df.drop_duplicates()).")

    if not instrucoes:
        instrucoes.append("Analise os dados e aplique as correcoes necessarias para adequar ao schema.")
        
    return "\n".join([f"{i+1}. {inst}" for i, inst in enumerate(instrucoes)])

def gerar_codigo_correcao_ia(df, resultado_validacao):
    colunas_df = list(df.columns)
    hash_estrutura = gerar_hash_estrutura(colunas_df, resultado_validacao["detalhes"])
    
    script_cache = buscar_script_cache(hash_estrutura)
    
    if script_cache:
        return (
            script_cache["script"],
            True,
            hash_estrutura,
            script_cache["id"],
            script_cache["vezes_utilizado"],
            0,
            script_cache.get("custo_tokens", 0)
        )
    
    env_path = Path(__file__).parent.parent / "secrets.env"
    load_dotenv(env_path)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    if not GROQ_API_KEY:
        raise ValueError("API Key não encontrada! Configure o arquivo secrets.env")
    
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY
    )
    
    template = carregar_template()
    
    instrucoes_especificas = _construir_instrucoes_dinamicas(resultado_validacao["detalhes"])
    
    sample_data = df.head(3).to_dict('records')
    dtypes_info = df.dtypes.to_string()
    
    historico_tentativas = ""
    if "script_anterior" in st.session_state and "erro_anterior" in st.session_state:
        historico_tentativas = f"""
        TENTATIVA ANTERIOR FALHOU COM O ERRO:
        {st.session_state['erro_anterior']}
        
        CODIGO QUE FALHOU:
        {st.session_state['script_anterior']}
        """

    prompt = f"""
    Voce e um Engenheiro de Dados Senior especialista em Pandas.
    Sua tarefa e gerar um script Python para corrigir um DataFrame chamado `df`.

    CONTEXTO DOS DADOS:
    - Colunas Atuais: {colunas_df}
    - Tipos de Dados (dtypes):
    {dtypes_info}
    - Amostra (head 3):
    {json.dumps(sample_data, indent=2, ensure_ascii=False)}

    {historico_tentativas}

    LISTA DE TAREFAS OBRIGATORIAS (Baseada nos erros detectados):
    {instrucoes_especificas}

    REGRAS GERAIS:
    1. Sempre remova colunas extras que nao estejam no template: {list(template["colunas"].keys())}.
    2. O codigo deve assumir que 'df' e 'pd' ja existem.
    3. NAO use blocos markdown (```python). Retorne apenas o codigo.
    4. Se precisar de regex, importe 're'. Se precisar de numpy, importe 'numpy as np'.
    5. A saida final deve ser a alteracao do dataframe `df`.

    Gere apenas o codigo Python:
    """
    
    chat_completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "Voce gera apenas codigo Python puro, sem formatacao Markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=4096,
    )

    tokens_gastos = 0
    codigo_correcao = chat_completion.choices[0].message.content
    codigo_correcao = codigo_correcao.replace("```python", "").replace("```", "").strip()

    if hasattr(chat_completion, 'usage') and chat_completion.usage:
        tokens_gastos = chat_completion.usage.total_tokens
    
    return (
        codigo_correcao,
        False,  
        hash_estrutura,
        None,
        0,
        tokens_gastos,
        0
    )

def new_correction(codigo_correcao, resultado_revalidacao, df_corrigido):
    st.session_state["script_anterior"] = codigo_correcao
    erros_detalhados = "\n".join([f"- {formatar_titulo_erro(e.get('tipo'))}" for e in resultado_revalidacao["detalhes"]])
    st.session_state["erro_anterior"] = f"Erros restantes após execução:\n{erros_detalhados}"
    
    st.session_state["arquivo_erros"] = resultado_revalidacao
    st.session_state["df_original"] = df_corrigido
    
    if "codigo_gerado" in st.session_state:
        del st.session_state["codigo_gerado"]
    if "usou_cache" in st.session_state:
        del st.session_state["usou_cache"]
    if "hash_estrutura" in st.session_state:
        del st.session_state["hash_estrutura"]
    
    st.rerun()