import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.insert_data import inserir_transacoes

st.set_page_config(
    page_title="Franq | Inserção no Banco",
    page_icon=":bar_chart:",
    layout="wide"
)

with st.sidebar:
    st.markdown("""
    **Como funciona:**
    1. Revise os dados corrigidos.
    2. Confirme a inserção no banco.
    3. Visualize o relatório de status.
    """)

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Inserção no Banco de Dados")
st.divider()

if "df_corrigido" not in st.session_state or "validacao_aprovada" not in st.session_state:
    st.warning("Nenhum dado validado encontrado!")
    st.info("Por favor, volte para a página de Correção IA e valide os dados primeiro.")
    
    if st.button("Voltar para Correção IA", type="primary"):
        st.switch_page("pages/2_Correção_IA.py")
    st.stop()

df_corrigido = st.session_state["df_corrigido"]

if not st.session_state.get("insercao_concluida", False):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Registros", len(df_corrigido))
    with col2:
        st.metric("Colunas", len(df_corrigido.columns))
    with col3:
        if "valor" in df_corrigido.columns:
            valor_total = df_corrigido["valor"].sum()
            st.metric("Valor Total", f"R$ {valor_total:,.2f}")
    
    st.divider()
    
    st.subheader("Preview dos Dados")
    st.info("Revise os dados abaixo antes de confirmar a inserção no banco de dados.")
    
    num_preview = min(10, len(df_corrigido))
    st.dataframe(
        df_corrigido.head(num_preview),
        use_container_width=True,
        hide_index=False
    )
    
    if len(df_corrigido) > num_preview:
        st.caption(f"Mostrando {num_preview} de {len(df_corrigido)} registros.")
    
    st.divider()
else:
    st.success("Dados inseridos com sucesso no banco de dados!")
    st.divider()
    
    resultado = st.session_state.get("resultado_insercao", {})
    duracao = st.session_state.get("duracao_insercao", 0)
    
    st.subheader("Relatório de Inserção")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Registros", resultado.get("total_registros", 0))
    with col2:
        st.metric("Inseridos com Sucesso", resultado.get("registros_inseridos", 0), 
                  delta_color="normal")
    with col3:
        erros_count = len(resultado.get("erros", []))
        st.metric("Erros", erros_count, delta_color="inverse")
    with col4:
        st.metric("Tempo de Execução", f"{duracao:.2f}s")
    
    st.divider()
    
    erros = resultado.get("erros", [])
    if erros:
        st.warning(f"Atenção: {len(erros)} registro(s) não foram inseridos devido a erros.")
        
        with st.expander("Ver Detalhes dos Erros", expanded=True):
            erros_df = pd.DataFrame(erros)
            st.dataframe(
                erros_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "linha": st.column_config.NumberColumn("Linha CSV", width="small"),
                    "id_transacao": st.column_config.TextColumn("ID Transação", width="medium"),
                    "erro": st.column_config.TextColumn("Descrição do Erro", width="large")
                }
            )
    else:
        st.success("Todos os registros foram inseridos sem erros!")
    
    st.divider()

if st.session_state.get("confirmar_insercao", False):
    st.session_state["confirmar_insercao"] = False
    
    st.subheader("Inserindo Dados...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        progress_bar.progress(10)
        status_text.text("Conectando ao banco de dados...")
        time.sleep(0.3)
        
        progress_bar.progress(30)
        status_text.text("Iniciando inserção dos registros...")
        time.sleep(0.3)
        
        inicio = time.time()
        resultado = inserir_transacoes(df_corrigido)
        duracao = time.time() - inicio
        
        progress_bar.progress(90)
        status_text.text("Finalizando...")
        time.sleep(0.3)
        
        progress_bar.progress(100)
        status_text.text("Inserção concluída!")
        time.sleep(0.5)
        
        st.session_state["resultado_insercao"] = resultado
        st.session_state["duracao_insercao"] = duracao
        st.session_state["insercao_concluida"] = True
        
        progress_bar.empty()
        status_text.empty()
        
        st.rerun()
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Erro durante a inserção: {str(e)}")
        st.exception(e)
        st.stop()

if not st.session_state.get("insercao_concluida", False):
    st.subheader("Confirmar Inserção")
    st.warning("Esta ação irá inserir os dados no banco de dados. Certifique-se de que os dados estão corretos.")
    
    col_confirmar, col_voltar = st.columns([1, 1])
    
    with col_confirmar:
        if st.button("Confirmar e Inserir no Banco", type="primary", use_container_width=True):
            st.session_state["confirmar_insercao"] = True
            st.rerun()
    
    with col_voltar:
        if st.button("Voltar para Correção", use_container_width=True):
            st.switch_page("pages/2_Correção_IA.py")
    
    st.divider()

if st.session_state.get("insercao_concluida", False):
    if st.button("Voltar para Início", type="primary", use_container_width=True):
        st.switch_page("main.py")
else:
    if st.button("Voltar para Início", use_container_width=True):
        st.switch_page("main.py")

