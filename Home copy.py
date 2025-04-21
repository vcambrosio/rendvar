import streamlit as st
from PIL import Image
import os

# Configuração antes de qualquer outro elemento do Streamlit
st.set_page_config(page_title="Home", layout="wide")

# Configuração do sidebar para mostrar o logo no topo
# Use CSS para forçar o logo a aparecer acima do menu de navegação
st.markdown("""
<style>
    section[data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
    }
    section[data-testid="stSidebar"] > div:first-child > div:first-child {
        order: -1;
    }
</style>
""", unsafe_allow_html=True)

# Adiciona logomarca no menu lateral
with st.sidebar:
    # Logo no topo
    logo_path = os.path.join("02-imagens", "logo.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        st.image(logo, use_container_width=True)
    
    # Rodapé
    st.markdown("---")  # Linha separadora
    st.markdown("### Desenvolvido por Vladimir")

# Conteúdo principal
# Caminho para imagens
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