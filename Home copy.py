import streamlit as st
from PIL import Image
import os

st.set_page_config(page_title="Home", layout="wide")

# Caminho para imagem
CAMINHO_IMAGENS = "02-imagens"
imagem_path = os.path.join(CAMINHO_IMAGENS, "rendvar_banner.jpg")

# Exibe imagem se existir
if os.path.exists(imagem_path):
    imagem = Image.open(imagem_path)
    st.image(imagem, use_container_width=True)

st.title("📊 Sistema RendVar")
st.write("""
Bem-vindo ao sistema **RendVar**.

Navegue pelo menu lateral para acessar as funcionalidades:

- 📥 Atualiza base de dados
- 📈 IFR2 - Ativo único
- 📘 IFR2 - Lista azul
""")
