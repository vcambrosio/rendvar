import streamlit as st
from PIL import Image
import os
from datetime import datetime
import pandas as pd

# Configuração antes de qualquer outro elemento do Streamlit
st.set_page_config(page_title="Home", layout="wide")

# Senha de acesso
SENHA_CORRETA = "Trabalho2025"

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
    # Cria duas colunas (ajuste a proporção conforme necessário)
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
            st.image(logo, use_container_width=False)
    
    with col_texto:
        # Texto alinhado verticalmente ao centro
        st.markdown("""
        <div style='display: flex; align-items: center; height: 100%;'>
            <p style='margin: 0;'>Desenvolvido por Vladimir</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")  # Linha separadora abaixo

# Conteúdo principal
CAMINHO_IMAGENS = "02-imagens"
imagem_path = os.path.join(CAMINHO_IMAGENS, "rendvar_banner.jpg")

# Exibe imagem se existir
# Exibe imagem se existir
if os.path.exists(imagem_path):
    imagem = Image.open(imagem_path)
    base_width = 200
    w_percent = (base_width / float(imagem.size[0]))
    h_size = int((float(imagem.size[1]) * float(w_percent)))
    imagem = imagem.resize((base_width, h_size), Image.Resampling.LANCZOS)
    
    # Cria colunas para alinhar imagem e título
    col1, col2 = st.columns([1, 3])  # Proporção 1:3 (imagem ocupa 1/4, título 3/4)
    
    with col1:
        st.image(imagem, width=base_width)
    
    with col2:
        st.title("Sistema RendVar")
        st.markdown("<p style='font-size:0.9em; margin-top:-15px;'>Release 0 em 21/04/2025</p>", unsafe_allow_html=True)
        
else:
    st.title("📊 Sistema RendVar")  # Caso a imagem não exista
    st.markdown("<p style='font-size:0.9em; margin-top:-15px;'>Release 0 em 21/04/2025</p>", unsafe_allow_html=True)
        

st.write(""" 
Navegue pelo menu lateral para acessar as funcionalidades:

- 📥 Atualiza base de dados - Inclui novas listas de ativos e atualiza seus dados historicos.
- 📈 Setup IFR - Ativo único - Executa backtest em um ativo de uma lista pré-carregada e atualizada.
- 📘 Setup IFR - Lista azul  - Executa backtest em todos os ativos de uma lista pré-carregada e atualizada.
- 📊 Ativos mais líquidos - Cria uma lista de ativos mais liquidos de uma lista pré-carregada.         
""")

# Seção do Microblog
st.markdown("---")
#st.subheader("📝 Atualizações e novidades:")

# Funções para manipulação do arquivo CSV (permanecem as mesmas)
def carregar_posts():
    caminho_csv = os.path.join("01-dados", "microblog.csv")
    if os.path.exists(caminho_csv):
        return pd.read_csv(caminho_csv).to_dict('records')
    return []

def salvar_posts(posts):
    caminho_csv = os.path.join("01-dados", "microblog.csv")
    os.makedirs("01-dados", exist_ok=True)
    df = pd.DataFrame(posts)
    df.to_csv(caminho_csv, index=False)

# Inicialização do session_state (permanece a mesma)
if 'posts' not in st.session_state:
    st.session_state.posts = carregar_posts()
    
if 'editando_id' not in st.session_state:
    st.session_state.editando_id = None
if 'excluindo_id' not in st.session_state:
    st.session_state.excluindo_id = None
if 'mostrar_senha' not in st.session_state:
    st.session_state.mostrar_senha = False

# Formulário para novo post ou edição (permanece o mesmo)
with st.form(key='microblog_form'):
    if st.session_state.editando_id is not None:
        post_editando = st.session_state.posts[st.session_state.editando_id]
        novo_post = st.text_area("Edite as atualizações e novidades:", value=post_editando['texto'], height=100)
    else:
        novo_post = st.text_area("Inclua as atualizações e novidades:", height=100)
    
    col1, col2 = st.columns(2)
    with col1:
        submit_button = st.form_submit_button("💾 Salvar" if st.session_state.editando_id is not None else "📤 Publicar")
    with col2:
        if st.session_state.editando_id is not None:
            cancelar_edicao = st.form_submit_button("❌ Cancelar")

    if submit_button and novo_post:
        if st.session_state.editando_id is not None:
            st.session_state.posts[st.session_state.editando_id] = {
                'texto': novo_post,
                'data': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            st.session_state.editando_id = None
            salvar_posts(st.session_state.posts)
            st.success("Informações atualizadas com sucesso!")
        else:
            post_com_data = {
                'texto': novo_post,
                'data': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            st.session_state.posts.insert(0, post_com_data)
            salvar_posts(st.session_state.posts)
            st.success("Atualizações publicadas com sucesso!")
    
    if st.session_state.editando_id is not None and cancelar_edicao:
        st.session_state.editando_id = None
        st.info("Edição cancelada")

# Nova exibição dos posts com botões à direita
if st.session_state.posts:
    st.markdown("📝 Atualizações e novidades:")
    for i, post in enumerate(st.session_state.posts):
        # Cria um container com duas colunas
        col_post, col_btns = st.columns([4, 1])  # 4/5 para o post, 1/5 para os botões
        
        with col_post:
            st.markdown(f"""
            <div style='background-color:#f0f2f6; padding:10px; border-radius:5px; margin:10px 0;'>
                <p style='font-size:0.8em; color:#666;'>{post['data']}</p>
                <p style='color:#000000;'>{post['texto']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_btns:
            # Container vertical para os botões com texto menor
            with st.container():
                st.markdown("""
                <style>
                    .small-font .stButton>button {
                        font-size: 0.8em;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                if st.button(f"✏️ Editar", key=f"editar_{i}"):
                    st.session_state.mostrar_senha = True
                    st.session_state.acao = "editar"
                    st.session_state.id_acao = i
                
                if st.button(f"🗑️ Excluir", key=f"excluir_{i}"):
                    st.session_state.mostrar_senha = True
                    st.session_state.acao = "excluir"
                    st.session_state.id_acao = i

# Modal de verificação de senha (permanece o mesmo)
if st.session_state.get('mostrar_senha', False):
    with st.expander("🔒 Verificação de Segurança", expanded=True):
        senha = st.text_input("Digite a senha para confirmar a ação:", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar"):
                if senha == SENHA_CORRETA:
                    if st.session_state.acao == "editar":
                        st.session_state.editando_id = st.session_state.id_acao
                        st.session_state.mostrar_senha = False
                        st.rerun()
                    elif st.session_state.acao == "excluir":
                        del st.session_state.posts[st.session_state.id_acao]
                        salvar_posts(st.session_state.posts)
                        st.session_state.mostrar_senha = False
                        st.success("Excluído com sucesso!")
                        st.rerun()
                else:
                    st.error("Senha incorreta!")
        with col2:
            if st.button("❌ Cancelar"):
                st.session_state.mostrar_senha = False
                st.rerun()

else:
    if not st.session_state.posts:
        st.info("Nenhuma informação ou atualização. Seja o primeiro a compartilhar algo!")