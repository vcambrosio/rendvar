import streamlit as st
from PIL import Image
import os
from datetime import datetime
import pandas as pd
import hashlib
import json
import time

# Configuração antes de qualquer outro elemento do Streamlit
st.set_page_config(page_title="Home", layout="wide")

# Constantes
SENHA_ADMIN = "Trabalho2025"  # Senha para editar/excluir posts
CAMINHO_USUARIOS = os.path.join("01-dados", "usuarios.json")
CAMINHO_IMAGENS = "02-imagens"
TEMPO_SESSAO = 3600  # Tempo de sessão em segundos (1 hora)

# Funções de autenticação
def verificar_hash(senha, hash_armazenado):
    """Verifica se a senha corresponde ao hash armazenado."""
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return senha_hash == hash_armazenado

def gerar_hash(senha):
    """Gera um hash SHA-256 para a senha."""
    return hashlib.sha256(senha.encode()).hexdigest()

def carregar_usuarios():
    """Carrega os usuários do arquivo JSON."""
    if os.path.exists(CAMINHO_USUARIOS):
        with open(CAMINHO_USUARIOS, 'r') as arquivo:
            return json.load(arquivo)
    else:
        # Cria um usuário admin padrão se não existir arquivo
        usuarios_padrao = {
            "admin": {
                "senha": gerar_hash("admin123"),
                "nivel": "admin"
            }
        }
        salvar_usuarios(usuarios_padrao)
        return usuarios_padrao

def salvar_usuarios(usuarios):
    """Salva os usuários no arquivo JSON."""
    os.makedirs(os.path.dirname(CAMINHO_USUARIOS), exist_ok=True)
    with open(CAMINHO_USUARIOS, 'w') as arquivo:
        json.dump(usuarios, arquivo, indent=4)

def verificar_sessao_valida():
    """Verifica se a sessão do usuário ainda é válida."""
    if 'ultimo_acesso' in st.session_state:
        tempo_atual = time.time()
        if tempo_atual - st.session_state.ultimo_acesso <= TEMPO_SESSAO:
            st.session_state.ultimo_acesso = tempo_atual
            return True
    return False

def atualizar_sessao():
    """Atualiza o timestamp da sessão."""
    st.session_state.ultimo_acesso = time.time()

# Inicialização das variáveis de sessão
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = None
if 'nivel_usuario' not in st.session_state:
    st.session_state.nivel_usuario = None
if 'ultimo_acesso' not in st.session_state:
    st.session_state.ultimo_acesso = None

# Verifica se a sessão expirou
if st.session_state.autenticado and not verificar_sessao_valida():
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.session_state.nivel_usuario = None
    st.warning("Sua sessão expirou. Por favor, faça login novamente.")

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
            st.image(logo, use_container_width=False)
    
    with col_texto:
        # Texto alinhado verticalmente ao centro
        st.markdown("""
        <div style='display: flex; align-items: center; height: 100%;'>
            <p style='margin: 0;'>Desenvolvido por Vladimir</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")  # Linha separadora abaixo
    
    # Exibe informações do usuário se autenticado
    if st.session_state.autenticado:
        st.markdown(f"**Usuário:** {st.session_state.usuario_atual}")
        if st.button("📤 Logout"):
            st.session_state.autenticado = False
            st.session_state.usuario_atual = None
            st.session_state.nivel_usuario = None
            st.rerun()

# Sistema de login se não estiver autenticado
if not st.session_state.autenticado:
    # Estrutura visual do sistema
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
    
    # Container de login com estilo melhorado
    st.markdown("""
    <style>
    .login-container {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        max-width: 500px;
        margin: 0 auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.subheader("🔐 Login")
    st.write("Por favor, faça login para acessar o sistema.")
    
    # Formulário de login
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("🔑 Entrar")
        
        if submitted:
            usuarios = carregar_usuarios()
            if usuario in usuarios and verificar_hash(senha, usuarios[usuario]["senha"]):
                st.session_state.autenticado = True
                st.session_state.usuario_atual = usuario
                st.session_state.nivel_usuario = usuarios[usuario]["nivel"]
                atualizar_sessao()
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    
    # Opção para cadastro (apenas para demonstração - em produção pode querer restringir)
    with st.expander("Não tem uma conta? Cadastre-se"):
        with st.form("cadastro_form"):
            novo_usuario = st.text_input("Novo usuário")
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirmar senha", type="password")
            
            if st.form_submit_button("📝 Cadastrar"):
                if not novo_usuario or not nova_senha:
                    st.error("Preencha todos os campos.")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
                else:
                    usuarios = carregar_usuarios()
                    if novo_usuario in usuarios:
                        st.error("Usuário já existe.")
                    else:
                        usuarios[novo_usuario] = {
                            "senha": gerar_hash(nova_senha),
                            "nivel": "usuario"  # Nível padrão para novos usuários
                        }
                        salvar_usuarios(usuarios)
                        st.success("Cadastro realizado com sucesso! Faça login para continuar.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Se o usuário estiver autenticado, mostra o conteúdo do sistema
else:
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

    - 📥 Atualiza base de dados - Inclui novas listas de ativos e atualiza seus dados historicos.
    - 📈 Setup IFR - Ativo único - Executa backtest em um ativo de uma lista pré-carregada e atualizada.
    - 📘 Setup IFR - Lista azul  - Executa backtest em todos os ativos de uma lista pré-carregada e atualizada.
    - 📊 Ativos mais líquidos - Cria uma lista de ativos mais liquidos de uma lista pré-carregada.         
    """)

    # Seção do Microblog (apenas administradores podem editar/excluir)
    st.markdown("---")

    # Funções para manipulação do arquivo CSV
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

    # Inicialização do session_state para posts
    if 'posts' not in st.session_state:
        st.session_state.posts = carregar_posts()
        
    if 'editando_id' not in st.session_state:
        st.session_state.editando_id = None
    if 'excluindo_id' not in st.session_state:
        st.session_state.excluindo_id = None
    if 'mostrar_senha' not in st.session_state:
        st.session_state.mostrar_senha = False

    # Formulário para novo post ou edição (apenas para admins)
    if st.session_state.nivel_usuario == "admin":
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
                        'data': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        'autor': st.session_state.usuario_atual
                    }
                    st.session_state.editando_id = None
                    salvar_posts(st.session_state.posts)
                    st.success("Informações atualizadas com sucesso!")
                else:
                    post_com_data = {
                        'texto': novo_post,
                        'data': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        'autor': st.session_state.usuario_atual
                    }
                    st.session_state.posts.insert(0, post_com_data)
                    salvar_posts(st.session_state.posts)
                    st.success("Atualizações publicadas com sucesso!")
            
            if st.session_state.editando_id is not None and 'cancelar_edicao' in locals() and cancelar_edicao:
                st.session_state.editando_id = None
                st.info("Edição cancelada")

    # Exibição dos posts
    if st.session_state.posts:
        st.markdown("📝 Atualizações e novidades:")
        for i, post in enumerate(st.session_state.posts):
            # Cria um container com duas colunas
            col_post, col_btns = st.columns([4, 1])  # 4/5 para o post, 1/5 para os botões
            
            with col_post:
                autor_info = f"Autor: {post.get('autor', 'Sistema')}" if 'autor' in post else ""
                st.markdown(f"""
                <div style='background-color:#f0f2f6; padding:10px; border-radius:5px; margin:10px 0;'>
                    <p style='font-size:0.8em; color:#666;'>{post['data']} {autor_info}</p>
                    <p style='color:#000000;'>{post['texto']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Apenas administradores podem editar/excluir posts
            if st.session_state.nivel_usuario == "admin":
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
                            st.session_state.editando_id = i
                            st.rerun()
                        
                        if st.button(f"🗑️ Excluir", key=f"excluir_{i}"):
                            if st.session_state.nivel_usuario == "admin":
                                # Confirmação de exclusão
                                st.session_state.excluindo_id = i
                                st.warning(f"Confirma exclusão do post de {post.get('data', '(sem data)')}?")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ Sim", key=f"confirm_del_{i}"):
                                        del st.session_state.posts[i]
                                        salvar_posts(st.session_state.posts)
                                        st.session_state.excluindo_id = None
                                        st.success("Post excluído com sucesso!")
                                        st.rerun()
                                with col2:
                                    if st.button("❌ Não", key=f"cancel_del_{i}"):
                                        st.session_state.excluindo_id = None
                                        st.rerun()
    else:
        st.info("Nenhuma informação ou atualização. Seja o primeiro a compartilhar algo!")

    # Seção de administração (apenas para admins)
    if st.session_state.nivel_usuario == "admin":
        st.markdown("---")
        with st.expander("⚙️ Administração do Sistema"):
            st.subheader("Gerenciamento de Usuários")
            
            # Lista de usuários
            usuarios = carregar_usuarios()
            
            # Tabela de usuários
            df_usuarios = pd.DataFrame([
                {"Usuário": user, "Nível": data["nivel"]} 
                for user, data in usuarios.items()
            ])
            st.dataframe(df_usuarios)
            
            # Formulário para adicionar/modificar usuários
            with st.form("form_admin_usuario"):
                st.subheader("Adicionar/Modificar Usuário")
                nome_usuario = st.text_input("Nome de usuário")
                senha_usuario = st.text_input("Senha (deixe em branco para manter atual)", type="password")
                nivel_usuario = st.selectbox("Nível", ["usuario", "admin"])
                
                col1, col2 = st.columns(2)
                with col1:
                    salvar = st.form_submit_button("💾 Salvar Usuário")
                with col2:
                    excluir = st.form_submit_button("🗑️ Excluir Usuário")
                
                if salvar:
                    if not nome_usuario:
                        st.error("Nome de usuário é obrigatório.")
                    else:
                        if nome_usuario in usuarios:
                            # Atualiza usuário existente
                            if senha_usuario:  # Se a senha foi fornecida
                                usuarios[nome_usuario]["senha"] = gerar_hash(senha_usuario)
                            usuarios[nome_usuario]["nivel"] = nivel_usuario
                            salvar_usuarios(usuarios)
                            st.success(f"Usuário '{nome_usuario}' atualizado com sucesso!")
                        else:
                            # Cria novo usuário
                            if not senha_usuario:
                                st.error("Senha é obrigatória para novos usuários.")
                            else:
                                usuarios[nome_usuario] = {
                                    "senha": gerar_hash(senha_usuario),
                                    "nivel": nivel_usuario
                                }
                                salvar_usuarios(usuarios)
                                st.success(f"Usuário '{nome_usuario}' criado com sucesso!")
                
                if excluir:
                    if not nome_usuario or nome_usuario not in usuarios:
                        st.error("Usuário não encontrado.")
                    elif nome_usuario == "admin":
                        st.error("O usuário admin não pode ser excluído.")
                    elif nome_usuario == st.session_state.usuario_atual:
                        st.error("Você não pode excluir seu próprio usuário.")
                    else:
                        del usuarios[nome_usuario]
                        salvar_usuarios(usuarios)
                        st.success(f"Usuário '{nome_usuario}' excluído com sucesso!")