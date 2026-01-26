import streamlit as st
import pandas as pd
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.validation import validar_csv_completo
from app.utils.ui_components import formatar_titulo_erro
from app.services.script_cache import salvar_script_cache, buscar_script_cache, gerar_hash_estrutura
from app.services.ai_code_generator import gerar_codigo_correcao_ia
from app.utils.data_handler import carregar_template

st.set_page_config(
    page_title="Franq | Correção IA",
    page_icon=":bar_chart:",
    layout="wide"
)

with st.sidebar:
    st.markdown("""
    **Como funciona:**
    1. Suba os arquivos CSV.
    2. O sistema valida os dados.
    3. A IA corrige erros automaticamente.
    4. Dados corrigidos são inseridos no banco.
    """)

    st.divider() 
    if st.button("Ver Dashboard", width='stretch'):
        st.session_state["pagina_anterior"] = "pages/2_Correção_IA.py"
        st.switch_page("pages/4_Dashboard.py")

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Correção Automática via IA")
st.divider()

if "fila_arquivos" not in st.session_state or not st.session_state["fila_arquivos"]:
    st.warning("Fila vazia.")
    if st.button("Voltar para Upload"):
        st.switch_page("main.py")
    st.stop()

arquivo_atual = None
idx_atual = -1

for i, f in enumerate(st.session_state["fila_arquivos"]):
    if f.status == "PENDENTE_CORRECAO":
        arquivo_atual = f
        idx_atual = i
        break

if arquivo_atual is None:
    st.success("Todos os arquivos da fila foram processados!")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Voltar para Lista", width='stretch'):
            st.switch_page("main.py")
    with col2:
        if st.button("Ir para Inserção no Banco", type="primary", width='stretch'):
            st.switch_page("pages/3_Inserção_Banco.py")
    st.stop()

total_files = len(st.session_state["fila_arquivos"])
st.progress((idx_atual) / total_files, text=f"Processando arquivo {idx_atual + 1} de {total_files}: {arquivo_atual.nome}")

col_info1, col_info2, col_info3 = st.columns(3)
col_info1.metric("Erros", arquivo_atual.validacao["total_erros"])
col_info2.metric("Linhas", len(arquivo_atual.df_original))
col_info3.metric("Status", "Aguardando Correção")

with st.expander("Detalhes dos Erros", expanded=False):
    for i, erro in enumerate(arquivo_atual.validacao["detalhes"]):
        st.write(f"{i+1}. {formatar_titulo_erro(erro.get('tipo'))}")

st.divider()

session_key_code = f"code_gen_{arquivo_atual.id}"
session_key_meta = f"meta_gen_{arquivo_atual.id}"
session_key_exec = f"exec_ok_{arquivo_atual.id}"
session_key_error = f"gen_error_{arquivo_atual.id}"
session_key_auto = f"auto_run_{arquivo_atual.id}"

if session_key_code not in st.session_state:
    
    colunas_hash = list(arquivo_atual.df_original.columns)
    hash_est = gerar_hash_estrutura(colunas_hash, arquivo_atual.validacao["detalhes"])
    
    found_in_cache = False
    
    if session_key_auto not in st.session_state and not st.session_state.get(session_key_error):
        script_cache = buscar_script_cache(hash_est)
        
        if script_cache:
            st.session_state[session_key_code] = script_cache["script"]
            st.session_state[session_key_meta] = {
                "hash": hash_est,
                "tokens": 0, 
                "econ": script_cache.get("custo_tokens", 0),
                "fonte": "CACHE",
                "vezes_utilizado": script_cache.get("vezes_utilizado", 0)
            }
            found_in_cache = True
            st.rerun()
    
    if not found_in_cache:
        if session_key_error in st.session_state:
            st.error(f"Falha na tentativa anterior: {st.session_state[session_key_error]}")
            st.warning("Verifique sua conexão ou tente novamente.")

        if session_key_auto not in st.session_state:
            st.info("Necessário gerar correção via IA.")
        
        trigger_generation = False
        if session_key_auto in st.session_state:
            trigger_generation = True
            st.info("Gerando novo código automaticamente...")
        else:
            if st.button("Gerar Script de Correção", type="primary"):
                trigger_generation = True

        if trigger_generation:
            if session_key_error in st.session_state:
                del st.session_state[session_key_error]
            
            if session_key_auto in st.session_state:
                del st.session_state[session_key_auto]
                
            with st.spinner("IA analisando dados..."):
                try:
                    codigo, usou_cache, hash_est, s_id, qtd, tokens, econ = gerar_codigo_correcao_ia(
                        arquivo_atual.df_original, 
                        arquivo_atual.validacao
                    )
                    
                    st.session_state[session_key_code] = codigo
                    st.session_state[session_key_meta] = {
                        "hash": hash_est,
                        "tokens": tokens,
                        "econ": econ,
                        "fonte": "IA" 
                    }
                    
                    arquivo_atual.update_ia_stats(tokens, "IA", econ)
                    st.rerun()
                    
                except Exception as e:
                    arquivo_atual.logger.registrar_erro("GERACAO_SCRIPT", "API Error", str(e))
                    st.session_state[session_key_error] = str(e)
                    st.rerun()

else:
    meta = st.session_state[session_key_meta]
    codigo_atual = st.session_state[session_key_code]
    
    if meta["fonte"] == "CACHE":
        vezes = meta.get("vezes_utilizado", 0)
        st.success(f"Código recuperado do CACHE. Verifique e execute. (Utilizado {vezes} vezes)")
    else:
        st.info("Código gerado pela IA. Verifique e execute.")
        
    st.code(codigo_atual, language="python")
    
    if session_key_exec not in st.session_state:
        
        c_exec, c_disc = st.columns([3, 1])
        
        with c_exec:
            if st.button("Executar Código", type="primary", use_container_width=True):
                try:
                    local_ns = {"df": arquivo_atual.df_original.copy(), "pd": pd}
                    exec(codigo_atual, local_ns)
                    df_temp = local_ns["df"]
                    
                    st.session_state[session_key_exec] = df_temp
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro de Execução: {e}")
        
        with c_disc:
            if st.button("Descartar e Tentar Novamente", type="secondary", use_container_width=True):
                del st.session_state[session_key_code]
                del st.session_state[session_key_meta]
                st.session_state[session_key_auto] = True
                if session_key_error in st.session_state: del st.session_state[session_key_error]
                st.rerun()
                
    else:
        df_temp = st.session_state[session_key_exec]
        st.success("Código executado com sucesso! Veja o preview abaixo.")
        st.dataframe(df_temp.head())
        
        col_act1, col_act2 = st.columns([1, 1])
        
        with col_act1:
            if st.button("Confirmar e Próximo", type="primary", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', encoding='utf-8') as tmp:
                    df_temp.to_csv(tmp.name, index=False)
                    tmp_path = tmp.name
                
                try:
                    template = carregar_template()
                    res = validar_csv_completo(tmp_path, template)
                finally:
                    os.remove(tmp_path)
                
                if res["valido"]:
                    arquivo_atual.df_corrigido = df_temp
                    arquivo_atual.status = "PRONTO_IA"
                    
                    if meta["fonte"] == "IA":
                        tipos_erros = [e.get("tipo") for e in arquivo_atual.validacao["detalhes"]]
                        salvar_script_cache(
                            meta["hash"], 
                            codigo_atual, 
                            f"Auto-fix: {tipos_erros}", 
                            tokens=meta["tokens"]
                        )
                    
                    if meta["fonte"] == "CACHE":
                        arquivo_atual.update_ia_stats(0, "CACHE", meta["econ"])

                    del st.session_state[session_key_code]
                    del st.session_state[session_key_meta]
                    del st.session_state[session_key_exec]
                    if session_key_error in st.session_state: del st.session_state[session_key_error]
                    st.rerun()
                else:
                    st.error(f"A validação falhou com {res['total_erros']} erros.")
                    del st.session_state[session_key_exec] 

        with col_act2:
            if meta["fonte"] == "IA":
                if st.button("Descartar e Gerar Novo Código", type="secondary", use_container_width=True):
                    del st.session_state[session_key_code]
                    del st.session_state[session_key_meta]
                    del st.session_state[session_key_exec] 
                    st.session_state[session_key_auto] = True
                    if session_key_error in st.session_state: del st.session_state[session_key_error]
                    st.rerun()

st.divider()

button_col1, button_col2, button_col3 = st.columns(3)
if button_col1.button("Voltar para Lista", width='stretch'):
    st.switch_page("main.py")

if button_col3.button("Pular este arquivo (Marcar como Falha)", type="secondary", width='stretch'):
    arquivo_atual.status = "FALHA_MANUAL"
    
    arquivo_atual.logger.registrar_erro("GERACAO_SCRIPT", "Manual", "Usuario pulou o arquivo")
    
    if session_key_code in st.session_state: del st.session_state[session_key_code]
    if session_key_meta in st.session_state: del st.session_state[session_key_meta]
    if session_key_exec in st.session_state: del st.session_state[session_key_exec]
    if session_key_error in st.session_state: del st.session_state[session_key_error]
    if session_key_auto in st.session_state: del st.session_state[session_key_auto]
    
    st.rerun()