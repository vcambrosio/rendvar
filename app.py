import streamlit as st
from PIL import Image
from coleta_dados import atualizar_dados
from ifr2_ativo import executar_ifr2_ativo
from ifr2_lista import executar_ifr2_lista

st.set_page_config(page_title="RendVar", layout="wide")

menu = st.sidebar.selectbox("Menu", ["Home", "Atualiza base de dados", "IFR2 - Ativo único", "IFR2 - Lista azul"])

CAMINHO_IMAGENS = "A:/02-Projetos_Python/rendvar/02-images"

if menu == "Home":
    st.title("📊 Projeto RendVar")
    st.markdown("""
        Bem-vindo à plataforma **RendVar**, voltada para análise de ações utilizando setups técnicos.
        - Atualização automática de dados via Yahoo Finance
        - Análise do setup **IFR2**
    """)
    try:
        imagem = Image.open(f"{CAMINHO_IMAGENS}/rendvar_banner.jpg")
        st.image(imagem, use_container_width=True)
    except FileNotFoundError:
        st.warning("Imagem não encontrada em /02-imagens.")

elif menu == "Atualiza base de dados":
    st.header("🔄 Atualização da Base de Dados")
    if st.button("Iniciar atualização"):
        atualizar_dados()
        st.success("Atualização concluída!")

elif menu == "IFR2 - Ativo único":
    st.header("📈 Setup IFR2 - Ativo Único")
    executar_ifr2_ativo()

elif menu == "IFR2 - Lista azul":
    st.header("📊 Setup IFR2 - Lista Azul")
    executar_ifr2_lista()
