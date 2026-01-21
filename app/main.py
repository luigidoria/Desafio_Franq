import streamlit as st

st.set_page_config(
    page_title="Franq | Ingestão de Dados",
    page_icon=":bar_chart:",
    layout="wide"
)

st.title("Portal de Ingestão de Transações")
st.divider()

with st.sidebar:
    st.header("Configurações")
    st.caption("Sistema de Ingestão v1.0")
    st.divider()
    st.markdown("""
    **Como funciona:**
    1. Suba o arquivo CSV.
    2. O sistema valida os dados.
    3. A IA corrige erros automaticamente.
    4. Dados corrigidos são inseridos no banco.
    """)