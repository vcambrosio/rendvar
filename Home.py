import streamlit as st
from PIL import Image
import os

# Configuração antes de qualquer outro elemento do Streamlit
st.set_page_config(page_title="Home", layout="wide")

# Constantes
CAMINHO_IMAGENS = "02-imagens"

# Configuração do sidebar para mostrar o logo no topo
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
    # Cria duas colunas
    col_logo, col_texto = st.columns([1, 3])
    
    with col_logo:
        # Logo redimensionada para 50px de largura
        logo_path = os.path.join("02-imagens", "logo.png")
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            base_width = 50
            w_percent = (base_width / float(logo.size[0]))
            h_size = int((float(logo.size[1]) * float(w_percent)))
            logo = logo.resize((base_width, h_size), Image.Resampling.LANCZOS)
            st.image(logo, width=base_width)
    
    with col_texto:
        # Texto alinhado verticalmente ao centro
        st.markdown("""
        <div style='display: flex; align-items: center; height: 100%;'>
            <p style='margin: 0;'>Desenvolvido por Vladimir</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")  # Linha separadora abaixo

# Conteúdo principal
imagem_path = os.path.join(CAMINHO_IMAGENS, "rendvar_banner.jpg")

# Exibe imagem se existir
if os.path.exists(imagem_path):
    imagem = Image.open(imagem_path)
    base_width = 200
    w_percent = (base_width / float(imagem.size[0]))
    h_size = int((float(imagem.size[1]) * float(w_percent)))
    imagem = imagem.resize((base_width, h_size), Image.Resampling.LANCZOS)
    
    # Cria colunas para alinhar imagem e título
    col1, col2 = st.columns([1, 3])  # Proporção 1:3
    
    with col1:
        st.image(imagem, width=base_width)
    
    with col2:
        st.title("Sistema RendVar")
        st.markdown("<p style='font-size:0.9em; margin-top:-15px;'>Release 0 em 21/04/2025</p>", unsafe_allow_html=True)
else:
    st.title("📊 Sistema RendVar")
    st.markdown("<p style='font-size:0.9em; margin-top:-15px;'>Release 0 em 21/04/2025</p>", unsafe_allow_html=True)

st.write(""" 
Navegue pelo menu lateral para acessar as funcionalidades:

- 📥 Atualiza base de dados - Inclui novas listas de ativos e atualiza seus dados históricos.
- 📈 Setup IFR - Ativo único - Executa backtest em um ativo de uma lista pré-carregada e atualizada.
- 📘 Setup IFR - Lista azul  - Executa backtest em todos os ativos de uma lista pré-carregada e atualizada.
- 📊 Ativos mais líquidos - Cria uma lista de ativos mais líquidos de uma lista pré-carregada.         
""")