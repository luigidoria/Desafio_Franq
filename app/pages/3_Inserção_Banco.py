import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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

# Verificar se há dados corrigidos para inserir
if "df_corrigido" not in st.session_state or "validacao_aprovada" not in st.session_state:
    st.warning("Nenhum dado validado encontrado!")
    st.info("Por favor, volte para a página de Correção IA e valide os dados primeiro.")
    
    if st.button("Voltar para Correção IA", type="primary"):
        st.switch_page("app/pages/2_Correção_IA.py")
    st.stop()

df_corrigido = st.session_state["df_corrigido"]

st.success("Dados validados e prontos para inserção!")
st.metric("Total de Registros", len(df_corrigido))

st.divider()

if st.session_state["sem_modficadoes_necessarias"] == False:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("Voltar para Correção", use_container_width=True):
            st.switch_page("pages/2_Correção_IA.py")
    with col3:
        if st.button("Voltar para Início", use_container_width=True):
            st.switch_page("main.py")
else:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("Voltar para Início", use_container_width=True):
            st.switch_page("main.py")