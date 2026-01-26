import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.insert_data import inserir_transacoes
from app.utils.ui_components import exibir_preview, exibir_relatorio

st.set_page_config(
    page_title="Franq | Inserção no Banco",
    page_icon=":bar_chart:",
    layout="wide"
)

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] { display: none; }
    </style>
""", unsafe_allow_html=True)

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
        st.session_state["pagina_anterior"] = "pages/3_Inserção_Banco.py"
        st.switch_page("pages/4_Dashboard.py")

st.title("Inserção no Banco de Dados")
st.divider()

if "fila_arquivos" not in st.session_state or not st.session_state["fila_arquivos"]:
    st.warning("Fila de arquivos vazia.")
    if st.button("Voltar para Início", type="primary"):
        st.switch_page("main.py")
    st.stop()

arquivo_atual = None

for f in st.session_state["fila_arquivos"]:
    if f.status in ["PRONTO_VALIDO", "PRONTO_IA", "PRONTO_CACHE"]:
        arquivo_atual = f
        break
    if f.status == "CONCLUIDO" and not f.relatorio_visualizado:
        arquivo_atual = f
        break

if arquivo_atual is None:
    st.success("Todos os arquivos válidos foram processados!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Voltar para Início", width='stretch'):
            st.session_state["fila_arquivos"] = []
            st.switch_page("main.py")
    with col2:
        if st.button("Ir para Dashboard", type="primary", width='stretch'):
            st.switch_page("pages/4_Dashboard.py")
    st.stop()

st.progress(0, text=f"Arquivo: {arquivo_atual.nome}")

if arquivo_atual.status == "CONCLUIDO":
    st.success(f"Processamento finalizado para: {arquivo_atual.nome}")
    
    exibir_relatorio(arquivo_atual.resultado_insercao, arquivo_atual.resultado_insercao["duracao"])
    
    if st.button("Próximo Arquivo", type="primary", width='stretch'):
        arquivo_atual.relatorio_visualizado = True
        st.rerun()

else:
    df_final = arquivo_atual.df_corrigido if arquivo_atual.df_corrigido is not None else arquivo_atual.df_original
    
    exibir_preview(df_final)
    
    st.warning("Esta ação irá escrever os dados no banco de dados.")
    
    col_act1, col_act2 = st.columns([3, 1])
    
    with col_act1:
        if st.button("Confirmar Inserção", type="primary", width='stretch'):
            with st.status("Inserindo registros...", expanded=False) as status:
                try:
                    inicio = time.time()
                    resultado = inserir_transacoes(df_final)
                    duracao = time.time() - inicio
                    
                    arquivo_atual.finalizar_insercao(resultado, duracao)
                    
                    status.update(label="Concluído!", state="complete")
                    st.rerun()
                    
                except Exception as e:
                    status.update(label="Erro crítico!", state="error")
                    arquivo_atual.logger.registrar_erro("INSERCAO", "Exception", str(e))
                    st.error(f"Falha na inserção: {str(e)}")

    with col_act2:
        if st.button("Pular", width='stretch'):
            arquivo_atual.status = "PULADO"
            st.rerun()