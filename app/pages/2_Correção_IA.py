import streamlit as st
from app.utils import formatar_titulo_erro

st.set_page_config(
    page_title="Franq | Correção IA",
    page_icon=":bar_chart:",
    layout="wide"
)

with st.sidebar:
    st.markdown("""
    **Como funciona:**
    1. Suba o arquivo CSV.
    2. O sistema valida os dados.
    3. A IA corrige erros automaticamente.
    4. Dados corrigidos são inseridos no banco.
    """)

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Correção Automática via IA")
st.divider()

if "arquivo_erros" not in st.session_state or "df_original" not in st.session_state:
    st.warning("Nenhum arquivo com erros foi carregado!")
    st.info("Por favor, volte para a página principal e faça o upload de um arquivo CSV.")
    
    if st.button("Voltar para Upload", type="primary"):
        st.switch_page("main.py")
    st.stop()

resultado_validacao = st.session_state["arquivo_erros"]
df = st.session_state["df_original"]

st.subheader("Resumo dos Erros Detectados")

col1, col2, col3 = st.columns(3)
col1.metric("Total de Erros", resultado_validacao["total_erros"])
col2.metric("Linhas no Arquivo", len(df))
col3.metric("Status", "Necessita Correção")

st.divider()

if st.button("Voltar para a pagina de upload", type="primary"):
    st.switch_page("main.py")

st.subheader("Tipos de Erros Encontrados")

for i, erro in enumerate(resultado_validacao["detalhes"]):
    tipo_erro = erro.get("tipo")
    st.write(f"**{i+1}.** {formatar_titulo_erro(tipo_erro)}")
    
    if tipo_erro == 'nomes_colunas':
        mapeamento = erro.get("mapeamento", {})
        if mapeamento:
            st.caption(f"{len(mapeamento)} colunas com nomes diferentes")
    elif tipo_erro == 'formato_valor':
        formato = erro.get("formato_detectado", "Desconhecido")
        st.caption(f"Formato detectado: {formato}")
    elif tipo_erro == 'formato_data':
        formato = erro.get("formato_detectado", "Desconhecido")
        st.caption(f"Formato detectado: {formato}")
    elif tipo_erro == 'colunas_faltando':
        colunas = erro.get("colunas", [])
        st.caption(f"Faltam {len(colunas)} colunas obrigatórias")

st.divider()