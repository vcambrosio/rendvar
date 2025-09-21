import streamlit as st
import pandas as pd
import os
import io
import re
import yfinance as yf
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import time
from PIL import Image


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


# Título do aplicativo
st.title("📊 Coleta Híbrida de Dados (YFinance + MetaTrader5)")
st.markdown("**🔥 Estratégia Híbrida:** Dados históricos extensos do Yahoo Finance + Dados precisos e recentes do MetaTrader5")

st.markdown("[🔗 Link para baixar lista do Índice Bovespa](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice de ações com governança corporativa diferenciada (IGC B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-governanca/indice-de-acoes-com-governanca-corporativa-diferenciada-igcx-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice Brasil 100 (IBrX 100 B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-100-ibrx-100-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice Brasil Amplo BM&FBOVESPA (IBrA B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-amplo-ibra-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice de BDRs não patrocinado-Global (BDRX B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/indice-de-bdrs-nao-patrocinados-global-bdrx-composicao-da-carteira.htm)")

# === CONFIGURAÇÕES ===
TIMEFRAME_MT5 = mt5.TIMEFRAME_D1  # diário para MT5
ANOS_YFINANCE = 15  # Mais anos para YFinance (dados históricos extensos)
ANOS_MT5 = 5  # AJUSTADO: 5 anos de dados do MT5 (dados recentes e precisos)

# Configurações da estratégia híbrida
DIAS_OVERLAP = 30  # Dias de sobreposição para garantir continuidade
DATA_CORTE_MT5 = datetime.now() - timedelta(days=365 * 5)  # AJUSTADO: 5 anos atrás como ponto de corte

# Função para criar o diretório se não existir
def criar_diretorio():
    diretorio = os.path.join("01-dados", "listas_csv")
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    return diretorio

# Função para listar arquivos no diretório
def listar_arquivos(diretorio):
    if os.path.exists(diretorio):
        return [f for f in os.listdir(diretorio) if f.endswith('.csv')]
    return []

# Função para extrair nome do arquivo sem extensão
def extrair_nome_arquivo(nome_arquivo):
    return os.path.splitext(nome_arquivo)[0]

# Função para processar arquivo simples (formato original)
def processar_arquivo_simples(uploaded_file, novo_nome, diretorio):
    # Ler o arquivo CSV
    df = pd.read_csv(uploaded_file)
    
    # Verificar se tem a coluna 'Código'
    if 'Código' not in df.columns:
        return False, "O arquivo deve conter uma coluna chamada 'Código'."
    
    # Extrair apenas a coluna 'Código'
    codigos = df['Código'].tolist()
    
    # Salvar em um novo arquivo sem cabeçalho, um ticker por linha
    caminho_completo = os.path.join(diretorio, f"{novo_nome}.csv")
    with open(caminho_completo, 'w') as f:
        for codigo in codigos:
            f.write(f"{codigo}\n")
    
    return True, f"Arquivo '{novo_nome}.csv' salvo com sucesso!"

# Função para detectar se o arquivo é complexo
def detectar_arquivo_complexo(content_str):
    return ';' in content_str and re.search(r'[A-Z0-9]{4}[0-9]?;', content_str)

# Função para processar arquivo complexo
def processar_arquivo_complexo(content_str, novo_nome, diretorio):
    linhas = content_str.strip().split('\n')
    codigos = []

    # Definir padrão de ticker com base no nome do arquivo
    if "BDR" in novo_nome.upper():
        padrao_ticker = r'^[A-Z]{4}34$'
    else:
        padrao_ticker = r'^[A-Z]{4}(3|4|11)$'

    for i, linha in enumerate(linhas):
        linha = linha.strip()
        if linha.startswith('Quantidade') or linha.startswith('Redutor'):
            continue
        if i < 2:
            continue

        partes = linha.split(';')
        for parte in partes:
            parte = parte.replace('"', '').strip()
            if re.match(padrao_ticker, parte):
                codigos.append(parte)
                break

    caminho_completo = os.path.join(diretorio, f"{novo_nome}.csv")
    with open(caminho_completo, 'w') as f:
        for codigo in codigos:
            f.write(f"{codigo}\n")

    return True, f"Arquivo complexo processado. '{novo_nome}.csv' salvo com {len(codigos)} tickers!"

# Função principal de processamento que identifica o tipo de arquivo
def processar_arquivo(uploaded_file, novo_nome, diretorio):
    content = uploaded_file.read()
    content_str = content.decode('utf-8', errors='replace')
    uploaded_file.seek(0)
    
    if detectar_arquivo_complexo(content_str):
        return processar_arquivo_complexo(content_str, novo_nome, diretorio)
    else:
        try:
            return processar_arquivo_simples(uploaded_file, novo_nome, diretorio)
        except Exception as e:
            return False, f"Erro ao processar o arquivo: {str(e)}"

# Função para ler os tickers de um arquivo CSV
def ler_tickers_do_arquivo(caminho_arquivo):
    tickers = []
    with open(caminho_arquivo, 'r') as file:
        for linha in file:
            ticker = linha.strip()
            if ticker:
                tickers.append(ticker)
    return tickers

# Função para verificar arquivo parquet corrompido
def verificar_parquet(caminho_bd):
    if os.path.exists(caminho_bd):
        try:
            _ = pd.read_parquet(caminho_bd)
            return True
        except Exception as e:
            st.warning(f"Arquivo parquet corrompido: {str(e)}. Será criado um novo banco de dados.")
            try:
                os.remove(caminho_bd)
            except Exception as del_e:
                st.error(f"Não foi possível remover o arquivo corrompido: {str(del_e)}")
                return False
            return True
    return True

# === FUNÇÕES YFINANCE ===

def baixar_dados_yfinance(tickers, nome_lista, base_existente):
    """Baixa dados históricos extensos usando yfinance"""
    
    if not tickers:
        return pd.DataFrame(), []
    
    # Configurar período de download (mais extenso para YFinance)
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=ANOS_YFINANCE*365)
    
    all_data = pd.DataFrame()
    sucessos_yf = []
    
    for i, ticker in enumerate(tickers):
        try:
            ticker_yf = f"{ticker}.SA"
            
            # Baixar dados
            dados = yf.download(ticker_yf, 
                               start=data_inicio.strftime('%Y-%m-%d'), 
                               end=data_fim.strftime('%Y-%m-%d'), 
                               progress=False)
            
            if not dados.empty:
                dados.reset_index(inplace=True)
                
                dados_processados = pd.DataFrame()
                dados_processados['Date'] = dados['Date']
                
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if col in dados.columns:
                        dados_processados[col] = dados[col]
                    else:
                        dados_processados[col] = None
                
                dados_processados['Ticker'] = ticker
                dados_processados['Lista'] = nome_lista
                dados_processados['Fonte'] = 'YFinance'  # Marcar a fonte
                
                # Filtrar dados até a data de corte do MT5 (deixar overlap)
                data_limite = DATA_CORTE_MT5 + timedelta(days=DIAS_OVERLAP)
                dados_processados = dados_processados[dados_processados['Date'] <= data_limite]
                
                if not dados_processados.empty:
                    all_data = pd.concat([all_data, dados_processados], ignore_index=True)
                    sucessos_yf.append(ticker)
                
            time.sleep(0.1)  # Pausa para evitar sobrecarga
            
        except Exception as e:
            st.warning(f"Erro YFinance para {ticker}: {str(e)}")
    
    return all_data, sucessos_yf

# === FUNÇÕES MT5 ===

def conectar_mt5():
    """Conecta ao MetaTrader5"""
    if not mt5.initialize():
        return False, f"Falha ao inicializar MetaTrader5: {mt5.last_error()}"
    
    account_info = mt5.account_info()
    if account_info is None:
        mt5.shutdown()
        return False, f"Não conectado ao servidor: {mt5.last_error()}"
    
    return True, f"Conectado à conta: {account_info.login} - Servidor: {account_info.server}"

def verificar_simbolo_mt5(ativo):
    """Verifica se o símbolo existe no MT5"""
    symbols = mt5.symbols_get()
    if symbols is None:
        return False
    
    symbol_names = [s.name for s in symbols]
    return ativo in symbol_names

def baixar_dados_mt5(tickers, nome_lista, base_existente):
    """Baixa dados recentes e precisos usando MT5"""
    
    if not tickers:
        return pd.DataFrame(), [], []
    
    # Conectar ao MT5
    conectado, msg_conexao = conectar_mt5()
    if not conectado:
        st.error(f"Erro MT5: {msg_conexao}")
        return pd.DataFrame(), [], []
    
    all_data = pd.DataFrame()
    sucessos_mt5 = []
    nao_encontrados_mt5 = []
    
    # Data de início para MT5 (dados recentes)
    data_inicio_mt5 = DATA_CORTE_MT5 - timedelta(days=DIAS_OVERLAP)
    data_fim = datetime.now()
    
    for ticker in tickers:
        # Lista de variações para tentar
        variantes = [ticker, ticker + "F"]
        dados_coletados = False
        
        for ativo in variantes:
            if not verificar_simbolo_mt5(ativo):
                continue
                
            try:
                # Tentar coletar dados do MT5
                rates = mt5.copy_rates_range(ativo, TIMEFRAME_MT5, data_inicio_mt5, data_fim)
                
                if rates is None:
                    # Método alternativo
                    total_days = (data_fim - data_inicio_mt5).days
                    rates = mt5.copy_rates_from(ativo, TIMEFRAME_MT5, data_fim, total_days)
                
                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    
                    # Filtrar apenas dados a partir da data de corte
                    df = df[df['time'] >= data_inicio_mt5]
                    
                    if len(df) > 0:
                        df_fmt = pd.DataFrame({
                            "Date": df['time'],
                            "Open": df['open'],
                            "High": df['high'],
                            "Low": df['low'],
                            "Close": df['close'],
                            "Volume": df['tick_volume'].astype("int64"),
                            "Ticker": ticker,  # Sempre usar ticker original
                            "Lista": nome_lista,
                            "Fonte": 'MT5'  # Marcar a fonte
                        })
                        
                        all_data = pd.concat([all_data, df_fmt], ignore_index=True)
                        sucessos_mt5.append(f"{ticker}" + (f" (via {ativo})" if ativo != ticker else ""))
                        dados_coletados = True
                        break
                        
            except Exception as e:
                continue
        
        if not dados_coletados:
            nao_encontrados_mt5.append(ticker)
        
        time.sleep(0.1)
    
    mt5.shutdown()
    return all_data, sucessos_mt5, nao_encontrados_mt5

# === FUNÇÃO HÍBRIDA PRINCIPAL ===

def baixar_dados_hibridos(tickers, nome_lista):
    """
    Estratégia híbrida: YFinance para dados históricos + MT5 para dados recentes
    """
    
    if not tickers:
        return False, "Nenhum ticker encontrado para baixar."
    
    # Caminho para o arquivo parquet
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
    
    # Verificar arquivo parquet corrompido
    if not verificar_parquet(caminho_bd):
        return False, "Erro ao tratar o arquivo parquet existente."
    
    # Carregar base existente
    if os.path.exists(caminho_bd):
        try:
            base_existente = pd.read_parquet(caminho_bd)
        except:
            base_existente = pd.DataFrame()
    else:
        base_existente = pd.DataFrame()
    
    # Progress bar
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    resultados = {
        'yfinance_sucessos': [],
        'mt5_sucessos': [],
        'mt5_nao_encontrados': [],
        'total_registros_yf': 0,
        'total_registros_mt5': 0
    }
    
    try:
        # FASE 1: Coleta via YFinance (dados históricos extensos)
        status_text.text("🔄 FASE 1: Coletando dados históricos via Yahoo Finance...")
        progress_bar.progress(0.1)
        
        dados_yfinance, sucessos_yf = baixar_dados_yfinance(tickers, nome_lista, base_existente)
        resultados['yfinance_sucessos'] = sucessos_yf
        resultados['total_registros_yf'] = len(dados_yfinance)
        
        progress_bar.progress(0.5)
        
        # FASE 2: Coleta via MT5 (dados recentes e precisos)
        status_text.text("🔄 FASE 2: Coletando dados recentes via MetaTrader5...")
        
        dados_mt5, sucessos_mt5, nao_encontrados_mt5 = baixar_dados_mt5(tickers, nome_lista, base_existente)
        resultados['mt5_sucessos'] = sucessos_mt5
        resultados['mt5_nao_encontrados'] = nao_encontrados_mt5
        resultados['total_registros_mt5'] = len(dados_mt5)
        
        progress_bar.progress(0.8)
        
        # FASE 3: Consolidação dos dados
        status_text.text("🔄 FASE 3: Consolidando dados híbridos...")
        
        # Combinar dados YFinance e MT5
        dados_consolidados = pd.DataFrame()
        
        if not dados_yfinance.empty:
            dados_consolidados = pd.concat([dados_consolidados, dados_yfinance], ignore_index=True)
        
        if not dados_mt5.empty:
            dados_consolidados = pd.concat([dados_consolidados, dados_mt5], ignore_index=True)
        
        if dados_consolidados.empty:
            progress_bar.empty()
            status_text.empty()
            return False, "Nenhum dado coletado por nenhuma das fontes."
        
        # Remover duplicatas (priorizar MT5 sobre YFinance para datas sobrepostas)
        dados_consolidados['Date'] = pd.to_datetime(dados_consolidados['Date'])
        dados_consolidados = dados_consolidados.sort_values(['Ticker', 'Date', 'Fonte'])
        
        # Em caso de duplicata na mesma data e ticker, manter MT5 (vem depois na ordenação)
        dados_consolidados = dados_consolidados.drop_duplicates(
            subset=['Date', 'Ticker'], keep='last'
        )
        
        # Remover dados antigos da mesma lista
        if not base_existente.empty and 'Lista' in base_existente.columns:
            base_existente = base_existente[base_existente['Lista'] != nome_lista]
            
            if not base_existente.empty:
                # Garantir que todas as colunas necessárias existam
                for col in ['Fonte']:
                    if col not in base_existente.columns:
                        base_existente[col] = 'Legacy'  # Marcar dados antigos
                
                dados_finais = pd.concat([base_existente, dados_consolidados], ignore_index=True)
            else:
                dados_finais = dados_consolidados
        else:
            dados_finais = dados_consolidados
        
        progress_bar.progress(0.9)
        
        # Salvar dados
        os.makedirs(os.path.dirname(caminho_bd), exist_ok=True)
        
        dados_finais = dados_finais.sort_values(by=['Lista', 'Ticker', 'Date'])
        dados_finais = dados_finais.drop_duplicates(subset=["Date","Ticker"])
        dados_finais.to_parquet(caminho_bd, index=False)
        
        progress_bar.progress(1.0)
        
    finally:
        # Limpar progress bar
        progress_bar.empty()
        status_text.empty()
    
    # Criar mensagem de resultado
    mensagem = f"🎯 **Coleta Híbrida Concluída para '{nome_lista}'**\n\n"
    
    mensagem += f"📊 **Yahoo Finance (Dados Históricos):**\n"
    mensagem += f"   • Sucessos: {len(resultados['yfinance_sucessos'])}\n"
    mensagem += f"   • Registros: {resultados['total_registros_yf']:,}\n\n"
    
    mensagem += f"🎯 **MetaTrader5 (Dados Precisos):**\n"
    mensagem += f"   • Sucessos: {len(resultados['mt5_sucessos'])}\n"
    mensagem += f"   • Não encontrados: {len(resultados['mt5_nao_encontrados'])}\n"
    mensagem += f"   • Registros: {resultados['total_registros_mt5']:,}\n\n"
    
    total_registros = resultados['total_registros_yf'] + resultados['total_registros_mt5']
    mensagem += f"📈 **Total Consolidado:** {total_registros:,} registros"
    
    return True, mensagem

# Função para atualizar dados históricos de uma lista específica
def atualizar_lista(nome_arquivo, diretorio):
    caminho_arquivo = os.path.join(diretorio, nome_arquivo)
    nome_lista = extrair_nome_arquivo(nome_arquivo)
    tickers = ler_tickers_do_arquivo(caminho_arquivo)
    
    # Usar função híbrida
    sucesso, mensagem = baixar_dados_hibridos(tickers, nome_lista)
    return sucesso, mensagem

# Função para atualizar todas as listas
def atualizar_todas_listas(diretorio):
    arquivos = listar_arquivos(diretorio)
    
    if not arquivos:
        return False, "Nenhuma lista encontrada para atualizar."
    
    resultados = []
    
    for arquivo in arquivos:
        st.write(f"🔄 Processando lista: {arquivo}")
        sucesso, mensagem = atualizar_lista(arquivo, diretorio)
        status = '✅' if sucesso else '❌'
        resultados.append(f"{status} Lista '{extrair_nome_arquivo(arquivo)}'")
        
        if sucesso:
            st.success(mensagem)
        else:
            st.error(f"Erro na lista {arquivo}: {mensagem}")
    
    return True, f"🎯 **Processo Híbrido Concluído:**\n" + "\n".join(resultados)

def remover_dados_historicos_por_lista(nome_lista):
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
    
    if not os.path.exists(caminho_bd):
        return True
    
    try:
        df = pd.read_parquet(caminho_bd)
        
        if 'Lista' not in df.columns:
            return True
        
        df_filtrado = df[df['Lista'] != nome_lista]
        df_filtrado.to_parquet(caminho_bd, index=False)
        
        return True
    except Exception as e:
        st.error(f"Erro ao remover dados históricos da lista '{nome_lista}': {str(e)}")
        return False

# === INTERFACE PRINCIPAL ===

# Status da estratégia híbrida
st.header("🔥 Status da Estratégia Híbrida")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Yahoo Finance")
    st.write(f"**Período:** {ANOS_YFINANCE} anos de histórico")
    st.write(f"**Finalidade:** Dados históricos extensos")
    st.write("**Status:** ✅ Sempre disponível")

with col2:
    st.subheader("🎯 MetaTrader5")
    st.write(f"**Período:** {ANOS_MT5} anos recentes")
    st.write(f"**Finalidade:** Dados precisos e atualizados")
    
    # Testar conexão MT5
    conectado, msg_conexao = conectar_mt5()
    if conectado:
        st.write("**Status:** ✅ Conectado")
        st.success(msg_conexao)
        mt5.shutdown()
    else:
        st.write("**Status:** ❌ Desconectado")
        st.error(msg_conexao)

# Criar diretório se não existir
diretorio = criar_diretorio()

# Interface principal
st.header("📁 Upload e Processamento de Arquivo CSV")

uploaded_file = st.file_uploader("Selecione um arquivo CSV", type=['csv'])

if uploaded_file is not None:
    nome_sugerido = extrair_nome_arquivo(uploaded_file.name)
    novo_nome = st.text_input("Digite um nome para o arquivo (sem extensão):", value=nome_sugerido)
    
    if novo_nome:
        if st.button("Processar e Salvar"):
            sucesso, mensagem = processar_arquivo(uploaded_file, novo_nome, diretorio)
            if sucesso:
                st.success(mensagem)
            else:
                st.error(mensagem)

# Seção para gerenciar arquivos existentes
st.header("📋 Gerenciar Arquivos Existentes")

arquivos = listar_arquivos(diretorio)
if arquivos:
    st.write(f"Arquivos na pasta '{diretorio}':")
    
    for arquivo in arquivos:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(arquivo)
        with col2:
            if st.button("Excluir", key=f"del_{arquivo}"):
                nome_lista = extrair_nome_arquivo(arquivo)
                os.remove(os.path.join(diretorio, arquivo))
                if remover_dados_historicos_por_lista(nome_lista):
                    st.success(f"Arquivo '{arquivo}' e seus dados históricos foram excluídos com sucesso!")
                else:
                    st.error(f"Arquivo '{arquivo}' foi excluído, mas houve um problema ao remover os dados históricos.")
                st.rerun()
        with col3:
            if st.button("🔥 Atualizar Híbrido", key=f"upd_{arquivo}"):
                with st.spinner(f"Executando coleta híbrida para '{arquivo}'..."):
                    sucesso, mensagem = atualizar_lista(arquivo, diretorio)
                    if sucesso:
                        st.success(mensagem)
                    else:
                        st.error(mensagem)
    
    # Linha com botões para ações em massa
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Excluir Todos os Arquivos"):
            for arquivo in arquivos:
                os.remove(os.path.join(diretorio, arquivo))
            
            caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
            if os.path.exists(caminho_bd):
                try:
                    os.remove(caminho_bd)
                    st.success("Todos os arquivos e o banco de dados histórico foram excluídos!")
                except Exception as e:
                    st.error(f"Arquivos de lista foram excluídos, mas houve um problema ao remover o banco de dados histórico: {str(e)}")
            else:
                st.success("Todos os arquivos foram excluídos!")
            st.rerun()
    
    with col2:
        if st.button("🔥 Atualizar Todas - Híbrido"):
            with st.spinner("Executando coleta híbrida para todas as listas..."):
                sucesso, mensagem = atualizar_todas_listas(diretorio)
                if sucesso:
                    st.success(mensagem)
                else:
                    st.error(mensagem)
else:
    st.info("Nenhum arquivo encontrado no diretório.")

# Exibir informações sobre o banco de dados
st.header("📊 Informações do Banco de Dados Híbrido")
caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")

if os.path.exists(caminho_bd):
    try:
        if verificar_parquet(caminho_bd):
            df_info = pd.read_parquet(caminho_bd)
            
            st.write(f"**Total de registros:** {len(df_info):,}")
            
            # Informações por fonte de dados
            if 'Fonte' in df_info.columns:
                st.write("**Distribuição por fonte de dados:**")
                fonte_dist = df_info['Fonte'].value_counts()
                for fonte, count in fonte_dist.items():
                    percentage = (count / len(df_info)) * 100
                    if fonte == 'YFinance':
                        st.write(f"   📈 **{fonte}:** {count:,} registros ({percentage:.1f}%) - Dados históricos")
                    elif fonte == 'MT5':
                        st.write(f"   🎯 **{fonte}:** {count:,} registros ({percentage:.1f}%) - Dados precisos")
                    else:
                        st.write(f"   📋 **{fonte}:** {count:,} registros ({percentage:.1f}%)")
            
            # Informações por lista
            if 'Lista' in df_info.columns:
                st.write("**Dados por lista:**")
                resumo_listas = df_info.groupby('Lista').agg({
                    'Ticker': 'nunique',
                    'Date': ['min', 'max']
                }).round(2)
                
                resumo_listas.columns = ['Tickers', 'Data Início', 'Data Fim']
                st.dataframe(resumo_listas)
            
            # Intervalo de datas geral
            try:
                if 'Date' in df_info.columns:
                    df_info['Date'] = pd.to_datetime(df_info['Date'])
                    min_data = df_info['Date'].min().strftime('%d/%m/%Y')
                    max_data = df_info['Date'].max().strftime('%d/%m/%Y')
                    st.write(f"**Período total:** {min_data} até {max_data}")
                    
                    # Mostrar ponto de transição YFinance -> MT5
                    data_corte_str = DATA_CORTE_MT5.strftime('%d/%m/%Y')
                    st.info(f"🔄 **Ponto de transição:** Dados antes de {data_corte_str} predominantemente do Yahoo Finance, após essa data do MetaTrader5")
            except:
                st.warning("Não foi possível determinar o intervalo de datas.")
            
            # Tickers únicos
            if 'Ticker' in df_info.columns:
                tickers_unicos = df_info['Ticker'].nunique()
                st.write(f"**Total de tickers únicos:** {tickers_unicos}")
                
        else:
            st.error("Não foi possível acessar o banco de dados. O arquivo parquet pode estar corrompido.")
                
    except Exception as e:
        st.error(f"Erro ao carregar informações do banco de dados: {str(e)}")
else:
    st.info("Banco de dados de cotações ainda não foi criado.")

# Seção para visualizar os últimos registros
st.header("📋 Últimos Registros Atualizados")

if os.path.exists(caminho_bd):
    try:
        if verificar_parquet(caminho_bd):
            df_ultimos = pd.read_parquet(caminho_bd)
            
            # Ordenar por data decrescente
            if 'Date' in df_ultimos.columns:
                try:
                    df_ultimos['Date'] = pd.to_datetime(df_ultimos['Date'])
                    df_ultimos = df_ultimos.sort_values(by='Date', ascending=False)
                except:
                    st.warning("Não foi possível ordenar por data.")
            
            st.write(f"Exibindo os 50 últimos registros do banco híbrido (total: {len(df_ultimos):,}):")
            
            # Opções de filtro
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'Lista' in df_ultimos.columns:
                    listas_disponiveis = ['Todas'] + sorted(df_ultimos['Lista'].unique().tolist())
                    lista_selecionada = st.selectbox('Filtrar por lista:', listas_disponiveis)
            
            with col2:
                if 'Ticker' in df_ultimos.columns:
                    tickers_disponiveis = ['Todos'] + sorted(df_ultimos['Ticker'].unique().tolist())
                    ticker_selecionado = st.selectbox('Filtrar por ticker:', tickers_disponiveis)
            
            with col3:
                if 'Fonte' in df_ultimos.columns:
                    fontes_disponiveis = ['Todas'] + sorted(df_ultimos['Fonte'].unique().tolist())
                    fonte_selecionada = st.selectbox('Filtrar por fonte:', fontes_disponiveis)
            
            # Aplicar filtros
            df_filtrado = df_ultimos.copy()
            
            if 'Lista' in df_ultimos.columns and lista_selecionada != 'Todas':
                df_filtrado = df_filtrado[df_filtrado['Lista'] == lista_selecionada]
            
            if 'Ticker' in df_ultimos.columns and ticker_selecionado != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['Ticker'] == ticker_selecionado]
                
            if 'Fonte' in df_ultimos.columns and fonte_selecionada != 'Todas':
                df_filtrado = df_filtrado[df_filtrado['Fonte'] == fonte_selecionada]
            
            # Exibir dataframe com destaque para a fonte
            if not df_filtrado.empty:
                # Preparar dados para exibição
                df_display = df_filtrado.head(50).copy()
                
                # Formattar a coluna Fonte com emojis
                if 'Fonte' in df_display.columns:
                    df_display['Fonte'] = df_display['Fonte'].map({
                        'YFinance': '📈 YFinance',
                        'MT5': '🎯 MT5',
                        'Legacy': '📋 Legacy'
                    }).fillna(df_display['Fonte'])
                
                st.dataframe(df_display, use_container_width=True)
                
                # Opção para baixar os dados filtrados
                csv = df_filtrado.head(50).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar dados visualizados como CSV",
                    data=csv,
                    file_name=f"dados_hibridos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Nenhum registro encontrado com os filtros aplicados.")
                
        else:
            st.error("Não foi possível acessar o banco de dados.")
                
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")

else:
    st.info("Banco de dados ainda não foi criado.")
    
    if st.button("🔥 Criar banco híbrido agora"):
        with st.spinner("Criando banco de dados híbrido..."):
            sucesso, mensagem = atualizar_todas_listas(diretorio)
            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(f"Erro ao criar o banco de dados: {mensagem}")

# Opções avançadas
with st.expander("⚙️ Configurações Avançadas"):
    st.subheader("🔧 Parâmetros da Estratégia Híbrida")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📈 Yahoo Finance (Dados Históricos)**")
        st.write(f"• Período: {ANOS_YFINANCE} anos")
        st.write(f"• Coleta até: {DATA_CORTE_MT5.strftime('%d/%m/%Y')}")
        st.write("• Vantagem: Histórico extenso")
        st.write("• Desvantagem: Menos preciso")
    
    with col2:
        st.write("**🎯 MetaTrader5 (Dados Precisos)**")
        st.write(f"• Período: {ANOS_MT5} anos recentes")
        st.write(f"• Coleta a partir: {DATA_CORTE_MT5.strftime('%d/%m/%Y')}")
        st.write("• Vantagem: Dados precisos")
        st.write("• Desvantagem: Histórico limitado")
    
    st.write(f"**🔄 Overlap:** {DIAS_OVERLAP} dias de sobreposição para garantir continuidade")
    
    st.subheader("🧪 Testes de Conectividade")
    
    col_test1, col_test2 = st.columns(2)
    
    with col_test1:
        if st.button("🧪 Testar Yahoo Finance"):
            with st.spinner("Testando Yahoo Finance..."):
                try:
                    test_data = yf.download("VALE3.SA", period="5d", progress=False)
                    if not test_data.empty:
                        st.success(f"✅ Yahoo Finance OK - {len(test_data)} registros de teste")
                    else:
                        st.error("❌ Yahoo Finance retornou dados vazios")
                except Exception as e:
                    st.error(f"❌ Erro no Yahoo Finance: {str(e)}")
    
    with col_test2:
        if st.button("🧪 Testar MetaTrader5"):
            conectado, msg = conectar_mt5()
            if conectado:
                st.success(f"✅ {msg}")
                
                # Mostrar alguns símbolos como exemplo
                try:
                    symbols = mt5.symbols_get()
                    if symbols:
                        symbols_br = [s.name for s in symbols if any(s.name.endswith(suffix) for suffix in ['3', '4', '11', 'F']) and len(s.name) <= 6][:5]
                        if symbols_br:
                            st.write("**Símbolos de exemplo:**", ", ".join(symbols_br))
                except:
                    pass
                
                mt5.shutdown()
            else:
                st.error(f"❌ {msg}")
    
    st.subheader("🗃️ Gerenciamento do Banco")
    
    if st.button("🔄 Resetar banco de dados híbrido"):
        if os.path.exists(caminho_bd):
            try:
                os.remove(caminho_bd)
                st.success("✅ Banco de dados resetado com sucesso!")
                st.info("Execute 'Atualizar Todas - Híbrido' para recriar.")
            except Exception as e:
                st.error(f"❌ Erro ao resetar: {str(e)}")
        else:
            st.info("ℹ️ Não existe banco de dados para resetar.")

# Informações sobre a estratégia híbrida
with st.expander("ℹ️ Como Funciona a Estratégia Híbrida"):
    st.markdown("""
    ## 🔥 Estratégia Híbrida: O Melhor de Dois Mundos
    
    ### 📊 **Fluxo de Coleta:**
    
    1. **📈 FASE 1 - Yahoo Finance (Dados Históricos)**
       - Coleta dados de até **15 anos** atrás
       - Para até aproximadamente **2 anos** atrás
       - Garante histórico extenso para análises de longo prazo
    
    2. **🎯 FASE 2 - MetaTrader5 (Dados Precisos)**  
       - Coleta dados dos **últimos 5 anos**
       - Dados mais precisos e atualizados
       - Horários corretos do mercado brasileiro
       - Volume mais confiável
    
    3. **🔄 FASE 3 - Consolidação Inteligente**
       - Remove duplicatas priorizando MT5
       - Mantém continuidade temporal
       - Marca origem dos dados (fonte)
    
    ### 🎯 **Vantagens:**
    - ✅ **Histórico extenso** (15+ anos via Yahoo Finance)
    - ✅ **Dados precisos** (5 anos recentes via MT5)
    - ✅ **Sem lacunas** (overlap de 30 dias)
    - ✅ **Atualizações incrementais**
    - ✅ **Fallback automático** (se MT5 falhar, mantém YF)
    - ✅ **Rastreabilidade** (sabe origem de cada dado)
    
    ### 📋 **Cenários de Uso:**
    - **Backtesting longo prazo:** Usa dados históricos do YF (10+ anos atrás)
    - **Análises recentes:** Usa dados precisos do MT5 (últimos 5 anos)
    - **Relatórios:** Combina ambos com total transparência
    
    ### 🔧 **Configuração Atual:**
    - **Yahoo Finance:** 15 anos (dados até 5 anos atrás)
    - **MetaTrader5:** 5 anos recentes + overlap
    - **Overlap:** 30 dias para garantir continuidade
    - **Prioridade:** MT5 > YFinance em caso de duplicata
    """)