import streamlit as st
from PIL import Image
import os


st.set_page_config(page_title="Home", layout="wide")

# Caminho para imagens
CAMINHO_IMAGENS = "02-imagens"
imagem_path = os.path.join(CAMINHO_IMAGENS, "rendvar_banner.jpg")

# Exibe imagem se existir
if os.path.exists(imagem_path):
    imagem = Image.open(imagem_path)
    st.image(imagem, use_container_width=True)

# Adiciona logomarca no menu lateral
with st.sidebar:
    # Logo no topo (substitua 'logo.png' pelo caminho da sua imagem)
    logo_path = os.path.join(CAMINHO_IMAGENS, "logo.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        st.image(logo, use_container_width=True)
    
    # Espaço para o conteúdo do menu (será adicionado automaticamente pelo Streamlit)
    
    # Rodapé
    st.markdown("---")  # Linha separadora
    st.markdown("### Desenvolvido por Vladimir")

st.title("📊 Sistema RendVar")
st.write("""
Bem-vindo ao sistema **RendVar**.

Navegue pelo menu lateral para acessar as funcionalidades:

- 📥 Atualiza base de dados
- 📈 IFR2 - Ativo único
- 📘 IFR2 - Lista azul
""")