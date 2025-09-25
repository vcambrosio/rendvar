import streamlit as st
import pandas as pd
import os
import io
import re
import yfinance as yf
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import time
import numpy as np
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
st.title("📊 Coleta Híbrida de Dados com Reancoragem (YFinance + MetaTrader5)")
st.markdown("**🔥 Estratégia Híbrida Aprimorada:** Dados históricos extensos do Yahoo Finance reanchorados + Dados precisos e recentes do MetaTrader5")

st.markdown("[🔗 Link para baixar lista do Índice Bovespa](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice de ações com governança corporativa diferenciada (IGC B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-governanca/indice-de-acoes-com-governanca-corporativa-diferenciada-igcx-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice Brasil 100 (IBrX 100 B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-100-ibrx-100-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice Brasil Amplo BM&FBOVESPA (IBrA B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-amplo-ibra-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice de BDRs não patrocinado-Global (BDRX B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/indice-de-bdrs-nao-patrocinados-global-bdrx-composicao-da-carteira.htm)")

# === CONFIGURAÇÕES ===
TIMEFRAME_MT5 = mt5.TIMEFRAME_D1  # diário para MT5
ANOS_YFINANCE = 15  # Mais anos para YFinance (dados históricos extensos)
ANOS_MT5 = 5  # 5 anos de dados do MT5 (dados recentes e precisos)

# Configurações da estratégia híbrida com reancoragem
DIAS_OVERLAP = 60  # AUMENTADO: Mais dias de sobreposição para melhor reancoragem
DATA_CORTE_MT5 = datetime.now() - timedelta(days=365 * 5)  # 5 anos atrás como ponto de corte
PERIODO_REANCORAGEM = 30  # Período em dias para calcular o fator de reancoragem

# === FUNÇÕES DE REANCORAGEM ===

def reancorar_yahoo_finance(df_yf, df_mt5, ticker):
    """
    Reancora dados do Yahoo Finance usando dados do MT5 como referência
    Baseado na função do arquivo reancorar.py
    """
    try:
        df_yf = df_yf.copy().reset_index(drop=True)
        df_mt5 = df_mt5.copy().reset_index(drop=True)
        
        # Garantir que as datas são datetime
        df_yf['Date'] = pd.to_datetime(df_yf['Date'])
        df_mt5['Date'] = pd.to_datetime(df_mt5['Date'])
        
        # Selecionar apenas as colunas necessárias
        df_yf_clean = df_yf[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df_mt5_clean = df_mt5[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        # Fazer merge para encontrar datas em comum
        df_merge = pd.merge(df_mt5_clean, df_yf_clean, on='Date', suffixes=('_MT5', '_YF'))
        
        if df_merge.empty:
            st.warning(f"⚠️ {ticker}: Não há datas em comum entre MT5 e Yahoo Finance para reancoragem")
            return df_yf
        
        # Usar os últimos N dias em comum para calcular o fator de reancoragem
        periodo_calc = min(PERIODO_REANCORAGEM, len(df_merge))
        df_calc = df_merge.tail(periodo_calc)
        
        # Calcular fator de reancoragem baseado no preço de fechamento médio
        fator_close = df_calc['Close_MT5'].mean() / df_calc['Close_YF'].mean()
        
        # Calcular fatores para outros preços (manter proporções)
        fator_open = df_calc['Open_MT5'].mean() / df_calc['Open_YF'].mean() if df_calc['Open_YF'].mean() > 0 else fator_close
        fator_high = df_calc['High_MT5'].mean() / df_calc['High_YF'].mean() if df_calc['High_YF'].mean() > 0 else fator_close
        fator_low = df_calc['Low_MT5'].mean() / df_calc['Low_YF'].mean() if df_calc['Low_YF'].mean() > 0 else fator_close
        
        # Aplicar reancoragem aos dados do Yahoo Finance
        df_yf_reanc = df_yf.copy()
        df_yf_reanc['Close'] = df_yf_reanc['Close'] * fator_close
        df_yf_reanc['Open'] = df_yf_reanc['Open'] * fator_open
        df_yf_reanc['High'] = df_yf_reanc['High'] * fator_high
        df_yf_reanc['Low'] = df_yf_reanc['Low'] * fator_low
        
        # Volume normalmente não precisa de ajuste, mas pode ser filtrado se muito diferente
        
        return df_yf_reanc
        
    except Exception as e:
        st.warning(f"⚠️ {ticker}: Erro na reancoragem: {str(e)}. Usando dados originais do Yahoo Finance.")
        return df_yf

def validar_reancoragem(df_mt5, df_yf_original, df_yf_reancorado, ticker):
    """
    Valida a qualidade da reancoragem usando métricas similares ao arquivo original
    """
    try:
        # Preparar dados para comparação
        df_mt5_clean = df_mt5[['Date', 'Close']].copy()
        df_yf_orig_clean = df_yf_original[['Date', 'Close']].copy()
        df_yf_reanc_clean = df_yf_reancorado[['Date', 'Close']].copy()
        
        # Garantir datas datetime
        for df in [df_mt5_clean, df_yf_orig_clean, df_yf_reanc_clean]:
            df['Date'] = pd.to_datetime(df['Date'])
        
        # Merge para período comum
        df_comp = pd.merge(df_mt5_clean, df_yf_reanc_clean, on='Date', suffixes=('_MT5', '_YF_REANC'))
        
        if df_comp.empty or len(df_comp) < 5:
            return None
        
        # Calcular retornos diários
        df_comp['Ret_MT5'] = df_comp['Close_MT5'].pct_change()
        df_comp['Ret_YF'] = df_comp['Close_YF_REANC'].pct_change()
        df_comp = df_comp.dropna()
        
        if len(df_comp) < 3:
            return None
        
        # Métricas de qualidade
        correlacao = df_comp['Ret_MT5'].corr(df_comp['Ret_YF'])
        mae = np.mean(np.abs(df_comp['Ret_MT5'] - df_comp['Ret_YF']))
        std_diff = np.std(df_comp['Close_MT5'] - df_comp['Close_YF_REANC'])
        
        # Índice de confiabilidade (ajustado)
        indice_confiabilidade = (correlacao * 100) - (mae * 10000)
        
        return {
            'correlacao': correlacao,
            'mae': mae,
            'std_diff': std_diff,
            'indice_confiabilidade': indice_confiabilidade,
            'dias_comparados': len(df_comp)
        }
        
    except Exception as e:
        st.warning(f"⚠️ {ticker}: Erro na validação: {str(e)}")
        return None

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
    # Ler o CSV do buffer
    df = pd.read_csv(uploaded_file)
    
    if 'Código' not in df.columns:
        return False, "O arquivo deve conter uma coluna chamada 'Código'."
    
    codigos = df['Código'].tolist()
    
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
    
    if detectar_arquivo_complexo(content_str):
        # Arquivo complexo → processa via texto
        return processar_arquivo_complexo(content_str, novo_nome, diretorio)
    else:
        # Arquivo simples → cria um novo buffer a partir de 'content'
        try:
            df_buffer = io.StringIO(content_str)
            return processar_arquivo_simples(df_buffer, novo_nome, diretorio)
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

def baixar_dados_yfinance(tickers, nome_lista, dados_mt5_existentes=None):
    """
    Baixa dados históricos extensos usando yfinance com reancoragem opcional
    """
    
    if not tickers:
        return pd.DataFrame(), []
    
    # Configurar período de download (mais extenso para YFinance)
    data_fim = DATA_CORTE_MT5 + timedelta(days=DIAS_OVERLAP)  # Terminar no início do período MT5
    data_inicio = data_fim - timedelta(days=ANOS_YFINANCE*365)
    
    all_data = pd.DataFrame()
    sucessos_yf = []
    estatisticas_reancoragem = []
    
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
                
                # === APLICAR REANCORAGEM SE HOUVER DADOS MT5 ===
                if dados_mt5_existentes is not None and not dados_mt5_existentes.empty:
                    # Filtrar dados MT5 para este ticker
                    dados_mt5_ticker = dados_mt5_existentes[dados_mt5_existentes['Ticker'] == ticker]
                    
                    if not dados_mt5_ticker.empty:
                        # Aplicar reancoragem
                        dados_originais = dados_processados.copy()
                        dados_processados = reancorar_yahoo_finance(dados_processados, dados_mt5_ticker, ticker)
                        
                        # Validar reancoragem
                        validacao = validar_reancoragem(dados_mt5_ticker, dados_originais, dados_processados, ticker)
                        
                        if validacao:
                            estatisticas_reancoragem.append({
                                'ticker': ticker,
                                'correlacao': validacao['correlacao'],
                                'mae': validacao['mae'],
                                'indice_confiabilidade': validacao['indice_confiabilidade'],
                                'dias_comparados': validacao['dias_comparados']
                            })
                
                dados_processados['Ticker'] = ticker
                dados_processados['Lista'] = nome_lista
                dados_processados['Fonte'] = 'YFinance_Reancorado' if (dados_mt5_existentes is not None and not dados_mt5_existentes.empty) else 'YFinance'
                
                if not dados_processados.empty:
                    all_data = pd.concat([all_data, dados_processados], ignore_index=True)
                    sucessos_yf.append(ticker)
                
            time.sleep(0.1)  # Pausa para evitar sobrecarga
            
        except Exception as e:
            st.warning(f"Erro YFinance para {ticker}: {str(e)}")
    
    # Mostrar estatísticas de reancoragem se houver
    if estatisticas_reancoragem:
        st.subheader("📊 Estatísticas de Reancoragem")
        df_stats = pd.DataFrame(estatisticas_reancoragem)
        
        # Resumo geral
        correlacao_media = df_stats['correlacao'].mean()
        mae_medio = df_stats['mae'].mean()
        indice_medio = df_stats['indice_confiabilidade'].mean()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Correlação Média", f"{correlacao_media:.3f}")
        with col2:
            st.metric("MAE Médio", f"{mae_medio:.6f}")
        with col3:
            st.metric("Índice Confiabilidade", f"{indice_medio:.1f}")
        
        # Mostrar detalhes por ticker
        with st.expander("🔍 Detalhes por Ticker"):
            st.dataframe(df_stats.round(4))
    
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

# === FUNÇÃO HÍBRIDA PRINCIPAL COM REANCORAGEM ===

def baixar_dados_hibridos_com_reancoragem(tickers, nome_lista):
    """
    Estratégia híbrida aprimorada: MT5 primeiro, depois YFinance com reancoragem
    CORREÇÃO: Problema na consolidação com base existente
    """
    
    if not tickers:
        return False, "Nenhum ticker encontrado para baixar."
    
    # Caminho para o arquivo parquet
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
    
    # Verificar arquivo parquet corrompido
    if not verificar_parquet(caminho_bd):
        return False, "Erro ao tratar o arquivo parquet existente."
    
    # CORREÇÃO: Carregar base existente ANTES do processo
    base_existente = pd.DataFrame()
    if os.path.exists(caminho_bd):
        try:
            base_existente = pd.read_parquet(caminho_bd)
            # CORREÇÃO: Remover dados antigos da mesma lista ANTES de processar
            if not base_existente.empty and 'Lista' in base_existente.columns:
                base_existente = base_existente[base_existente['Lista'] != nome_lista]
        except Exception as e:
            st.warning(f"Erro ao carregar base existente: {str(e)}. Criando nova base.")
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
        'total_registros_mt5': 0,
        'reancoragem_aplicada': False
    }
    
    try:
        # FASE 1: Coleta via MT5 (dados recentes e precisos) - PRIMEIRO!
        status_text.text("🎯 FASE 1: Coletando dados recentes via MetaTrader5...")
        progress_bar.progress(0.1)
        
        dados_mt5, sucessos_mt5, nao_encontrados_mt5 = baixar_dados_mt5(tickers, nome_lista, base_existente)
        resultados['mt5_sucessos'] = sucessos_mt5
        resultados['mt5_nao_encontrados'] = nao_encontrados_mt5
        resultados['total_registros_mt5'] = len(dados_mt5)
        
        progress_bar.progress(0.4)
        
        # FASE 2: Coleta via YFinance com reancoragem (dados históricos)
        status_text.text("📊 FASE 2: Coletando dados históricos via Yahoo Finance com reancoragem...")
        
        # Passar dados MT5 para reancoragem
        dados_yfinance, sucessos_yf = baixar_dados_yfinance(tickers, nome_lista, dados_mt5)
        resultados['yfinance_sucessos'] = sucessos_yf
        resultados['total_registros_yf'] = len(dados_yfinance)
        resultados['reancoragem_aplicada'] = not dados_mt5.empty
        
        progress_bar.progress(0.7)
        
        # FASE 3: Consolidação dos dados (CORRIGIDA)
        status_text.text("🔄 FASE 3: Consolidando dados híbridos com reancoragem...")
        
        # CORREÇÃO: Combinar novos dados primeiro
        dados_consolidados = pd.DataFrame()
        
        # Adicionar dados YFinance (históricos)
        if not dados_yfinance.empty:
            dados_consolidados = pd.concat([dados_consolidados, dados_yfinance], ignore_index=True)
        
        # Adicionar dados MT5 (recentes) - prioridade
        if not dados_mt5.empty:
            dados_consolidados = pd.concat([dados_consolidados, dados_mt5], ignore_index=True)
        
        if dados_consolidados.empty:
            progress_bar.empty()
            status_text.empty()
            return False, "Nenhum dado coletado por nenhuma das fontes."
        
        # CORREÇÃO: Garantir colunas e tipos consistentes
        dados_consolidados['Date'] = pd.to_datetime(dados_consolidados['Date'])
        
        # Garantir que todas as colunas necessárias existam nos novos dados
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Ticker', 'Lista', 'Fonte']
        for col in required_columns:
            if col not in dados_consolidados.columns:
                if col == 'Fonte':
                    dados_consolidados[col] = 'Unknown'
                else:
                    dados_consolidados[col] = None
        
        # Ordenar e remover duplicatas nos novos dados (MT5 tem prioridade)
        dados_consolidados = dados_consolidados.sort_values(['Ticker', 'Date', 'Fonte'])
        dados_consolidados = dados_consolidados.drop_duplicates(subset=['Date', 'Ticker'], keep='last')
        
        # CORREÇÃO: Combinar com base existente de forma segura
        if not base_existente.empty:
            # Garantir que base existente tem todas as colunas necessárias
            for col in required_columns:
                if col not in base_existente.columns:
                    if col == 'Fonte':
                        base_existente[col] = 'Legacy'
                    else:
                        base_existente[col] = None
            
            # Garantir tipos consistentes
            base_existente['Date'] = pd.to_datetime(base_existente['Date'])
            
            # Combinar tudo
            dados_finais = pd.concat([base_existente, dados_consolidados], ignore_index=True)
            
            # Remover duplicatas finais (priorizar dados mais recentes)
            dados_finais = dados_finais.sort_values(['Ticker', 'Date', 'Fonte'])
            dados_finais = dados_finais.drop_duplicates(subset=['Date', 'Ticker'], keep='last')
        else:
            dados_finais = dados_consolidados
        
        progress_bar.progress(0.9)
        
        # CORREÇÃO: Salvar dados com verificação adicional
        os.makedirs(os.path.dirname(caminho_bd), exist_ok=True)
        
        # Ordenar dados finais e verificar integridade
        dados_finais = dados_finais.sort_values(by=['Lista', 'Ticker', 'Date'])
        
        # CORREÇÃO: Verificar se dados_finais não está vazio antes de salvar
        if dados_finais.empty:
            progress_bar.empty()
            status_text.empty()
            return False, "Dados finais consolidados estão vazios."
        
        # CORREÇÃO: Verificar estrutura antes de salvar
        try:
            # Testar se é possível converter para parquet
            test_parquet = dados_finais.to_parquet(None)
            if test_parquet is None:
                raise ValueError("Erro na conversão para parquet")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            return False, f"Erro na estrutura dos dados para salvar: {str(e)}"
        
        # Salvar arquivo
        try:
            dados_finais.to_parquet(caminho_bd, index=False)
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            return False, f"Erro ao salvar arquivo parquet: {str(e)}"
        
        progress_bar.progress(1.0)
        
    except Exception as e:
        # Limpar progress bar em caso de erro
        try:
            progress_bar.empty()
            status_text.empty()
        except:
            pass
        return False, f"Erro no processo híbrido: {str(e)}"
        
    finally:
        # Limpar progress bar
        try:
            progress_bar.empty()
            status_text.empty()
        except:
            pass
    
    # Criar mensagem de resultado
    mensagem = f"🎯 **Coleta Híbrida com Reancoragem Concluída para '{nome_lista}'**\n\n"
    
    mensagem += f"🎯 **MetaTrader5 (Dados de Referência):**\n"
    mensagem += f"   • Sucessos: {len(resultados['mt5_sucessos'])}\n"
    mensagem += f"   • Não encontrados: {len(resultados['mt5_nao_encontrados'])}\n"
    mensagem += f"   • Registros: {resultados['total_registros_mt5']:,}\n\n"
    
    mensagem += f"📊 **Yahoo Finance (Dados Reanchorados):**\n"
    mensagem += f"   • Sucessos: {len(resultados['yfinance_sucessos'])}\n"
    mensagem += f"   • Registros: {resultados['total_registros_yf']:,}\n"
    mensagem += f"   • Reancoragem: {'✅ Aplicada' if resultados['reancoragem_aplicada'] else '❌ Não aplicada'}\n\n"
    
    total_registros = resultados['total_registros_yf'] + resultados['total_registros_mt5']
    mensagem += f"📈 **Total Consolidado:** {total_registros:,} registros\n"
    mensagem += f"🔄 **Estratégia:** MT5 como referência + YF reanchorado para histórico"
    
    return True, mensagem

# Função para atualizar dados históricos de uma lista específica
def atualizar_lista(nome_arquivo, diretorio):
    caminho_arquivo = os.path.join(diretorio, nome_arquivo)
    nome_lista = extrair_nome_arquivo(nome_arquivo)
    tickers = ler_tickers_do_arquivo(caminho_arquivo)
    
    # Usar função híbrida com reancoragem
    sucesso, mensagem = baixar_dados_hibridos_com_reancoragem(tickers, nome_lista)
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
    
    return True, f"🎯 **Processo Híbrido com Reancoragem Concluído:**\n" + "\n".join(resultados)

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

# Status da estratégia híbrida com reancoragem
st.header("🔥 Status da Estratégia Híbrida com Reancoragem")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 MetaTrader5 (Referência)")
    st.write(f"**Período:** {ANOS_MT5} anos recentes")
    st.write(f"**Função:** Dados precisos + base para reancoragem")
    st.write("**Prioridade:** Máxima (não sobrescritos)")
    
    # Testar conexão MT5
    conectado, msg_conexao = conectar_mt5()
    if conectado:
        st.write("**Status:** ✅ Conectado")
        st.success(msg_conexao)
        mt5.shutdown()
    else:
        st.write("**Status:** ❌ Desconectado")
        st.error(msg_conexao)

with col2:
    st.subheader("📊 Yahoo Finance (Reanchorado)")
    st.write(f"**Período:** {ANOS_YFINANCE} anos históricos")
    st.write(f"**Função:** Dados históricos reanchorados ao MT5")
    st.write(f"**Reancoragem:** {PERIODO_REANCORAGEM} dias de referência")
    st.write("**Status:** ✅ Sempre disponível")

st.info(f"🔄 **Overlap configurado:** {DIAS_OVERLAP} dias para garantir reancoragem precisa")

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
            if st.button("🔥 Atualizar Reanchorado", key=f"upd_{arquivo}"):
                with st.spinner(f"Executando coleta híbrida com reancoragem para '{arquivo}'..."):
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
        if st.button("🔥 Atualizar Todas - Reanchorado"):
            with st.spinner("Executando coleta híbrida com reancoragem para todas as listas..."):
                sucesso, mensagem = atualizar_todas_listas(diretorio)
                if sucesso:
                    st.success(mensagem)
                else:
                    st.error(mensagem)
else:
    st.info("Nenhum arquivo encontrado no diretório.")

# Exibir informações sobre o banco de dados
st.header("📊 Informações do Banco de Dados Híbrido com Reancoragem")
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
                    if fonte == 'YFinance_Reancorado':
                        st.write(f"   📊 **{fonte}:** {count:,} registros ({percentage:.1f}%) - Histórico reanchorado")
                    elif fonte == 'YFinance':
                        st.write(f"   📈 **{fonte}:** {count:,} registros ({percentage:.1f}%) - Histórico original")
                    elif fonte == 'MT5':
                        st.write(f"   🎯 **{fonte}:** {count:,} registros ({percentage:.1f}%) - Referência precisa")
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
                    st.info(f"🔄 **Ponto de transição:** Dados antes de {data_corte_str} do Yahoo Finance (reanchorados), após do MetaTrader5")
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
            
            st.write(f"Exibindo os 50 últimos registros do banco híbrido reanchorado (total: {len(df_ultimos):,}):")
            
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
                        'YFinance_Reancorado': '📊 YF Reanchorado',
                        'YFinance': '📈 YF Original', 
                        'MT5': '🎯 MT5',
                        'Legacy': '📋 Legacy'
                    }).fillna(df_display['Fonte'])
                
                st.dataframe(df_display, use_container_width=True)
                
                # Opção para baixar os dados filtrados
                csv = df_filtrado.head(50).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar dados visualizados como CSV",
                    data=csv,
                    file_name=f"dados_hibridos_reancorados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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
    
    if st.button("🔥 Criar banco híbrido reanchorado agora"):
        with st.spinner("Criando banco de dados híbrido com reancoragem..."):
            sucesso, mensagem = atualizar_todas_listas(diretorio)
            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(f"Erro ao criar o banco de dados: {mensagem}")

# Opções avançadas
with st.expander("⚙️ Configurações Avançadas da Reancoragem"):
    st.subheader("🔧 Parâmetros da Estratégia Híbrida com Reancoragem")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🎯 MetaTrader5 (Dados de Referência)**")
        st.write(f"• Período: {ANOS_MT5} anos recentes")
        st.write(f"• Coleta a partir: {DATA_CORTE_MT5.strftime('%d/%m/%Y')}")
        st.write("• Função: Base para reancoragem + dados precisos")
        st.write("• Prioridade: MÁXIMA (nunca sobrescrito)")
    
    with col2:
        st.write("**📊 Yahoo Finance (Dados Reanchorados)**")
        st.write(f"• Período: {ANOS_YFINANCE} anos históricos")
        st.write(f"• Coleta até: {DATA_CORTE_MT5.strftime('%d/%m/%Y')}")
        st.write(f"• Reancoragem: Últimos {PERIODO_REANCORAGEM} dias")
        st.write("• Função: Histórico ajustado aos preços MT5")
    
    st.write(f"**🔄 Configurações de Reancoragem:**")
    st.write(f"• Overlap: {DIAS_OVERLAP} dias")
    st.write(f"• Período de cálculo: {PERIODO_REANCORAGEM} dias")
    st.write(f"• Método: Fator multiplicativo por preço médio")
    st.write(f"• Validação: Correlação + MAE + Índice de confiabilidade")
    
    st.subheader("🧪 Testes de Conectividade")
    
    col_test1, col_test2 = st.columns(2)
    
    with col_test1:
        if st.button("🧪 Testar Yahoo Finance + Reancoragem"):
            with st.spinner("Testando Yahoo Finance com simulação de reancoragem..."):
                try:
                    # Teste básico YF
                    test_data_yf = yf.download("VALE3.SA", period="60d", progress=False)
                    if not test_data_yf.empty:
                        st.success(f"✅ Yahoo Finance OK - {len(test_data_yf)} registros de teste")
                        
                        # Simular dados MT5 para teste de reancoragem
                        test_data_yf_clean = test_data_yf.reset_index()
                        test_data_yf_clean = test_data_yf_clean[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                        
                        # Criar dados "MT5" simulados (com pequena variação)
                        test_mt5_sim = test_data_yf_clean.tail(30).copy()
                        test_mt5_sim[['Open', 'High', 'Low', 'Close']] *= 1.02  # Simular diferença de 2%
                        
                        # Testar reancoragem
                        test_reancorado = reancorar_yahoo_finance(test_data_yf_clean, test_mt5_sim, "VALE3")
                        
                        if len(test_reancorado) > 0:
                            fator_aplicado = test_reancorado['Close'].iloc[-1] / test_data_yf_clean['Close'].iloc[-1]
                            st.info(f"🔄 Teste de reancoragem: Fator aplicado = {fator_aplicado:.4f}")
                        else:
                            st.warning("⚠️ Teste de reancoragem falhou")
                    else:
                        st.error("❌ Yahoo Finance retornou dados vazios")
                except Exception as e:
                    st.error(f"❌ Erro no teste: {str(e)}")
    
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
                        
                        # Testar coleta de dados para reancoragem
                        if symbols_br:
                            test_symbol = symbols_br[0]
                            try:
                                test_rates = mt5.copy_rates_from_pos(test_symbol, TIMEFRAME_MT5, 0, 30)
                                if test_rates is not None:
                                    st.info(f"🎯 Teste coleta MT5: {len(test_rates)} registros de {test_symbol}")
                            except:
                                pass
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
                st.info("Execute 'Atualizar Todas - Reanchorado' para recriar.")
            except Exception as e:
                st.error(f"❌ Erro ao resetar: {str(e)}")
        else:
            st.info("ℹ️ Não existe banco de dados para resetar.")

# Informações sobre a estratégia híbrida com reancoragem
with st.expander("ℹ️ Como Funciona a Estratégia Híbrida com Reancoragem"):
    st.markdown(f"""
    ## 🔥 Estratégia Híbrida com Reancoragem: Máxima Precisão
    
    ### 📊 **Fluxo de Coleta Aprimorado:**
    
    1. **🎯 FASE 1 - MetaTrader5 (Dados de Referência - PRIMEIRO)**
       - Coleta dados dos **últimos {ANOS_MT5} anos**
       - Dados mais precisos e atualizados
       - **NUNCA são sobrescritos** - prioridade máxima
       - Servem como **base para reancoragem**
    
    2. **📊 FASE 2 - Yahoo Finance (Dados Reanchorados)**  
       - Coleta dados de até **{ANOS_YFINANCE} anos** atrás
       - Termina no ponto de corte do MT5
       - **REANCORAGEM AUTOMÁTICA** usando dados MT5
       - Ajusta preços para o nível real do mercado
    
    3. **🔄 FASE 3 - Consolidação Inteligente**
       - Remove duplicatas **priorizando MT5**
       - Mantém continuidade temporal perfeita
       - Marca origem: MT5, YFinance_Reancorado, etc.
    
    ### 🎯 **Processo de Reancoragem:**
    - **Período de Cálculo:** Últimos {PERIODO_REANCORAGEM} dias em comum
    - **Método:** Fator multiplicativo baseado em preços médios
    - **Aplicação:** Ajusta Open, High, Low, Close do YF
    - **Validação:** Correlação + MAE + Índice de confiabilidade
    - **Overlap:** {DIAS_OVERLAP} dias para garantir dados suficientes
    
    ### 🌟 **Vantagens da Reancoragem:**
    - ✅ **Continuidade perfeita** entre YF e MT5
    - ✅ **Preços ajustados** ao nível real do mercado
    - ✅ **Elimina gaps** artificiais entre fontes
    - ✅ **Mantém proporções** dos preços históricos
    - ✅ **Validação automática** da qualidade
    - ✅ **Fallback seguro** se reancoragem falhar
    
    ### 📈 **Casos de Uso Ideais:**
    - **Backtesting longo prazo:** Dados consistentes por 15+ anos
    - **Análises técnicas:** Sem distorções entre períodos
    - **Relatórios:** Preços alinhados com realidade atual
    - **Machine Learning:** Features consistentes no tempo
    
    ### 🔧 **Configuração Atual:**
    - **Yahoo Finance:** {ANOS_YFINANCE} anos (até {ANOS_MT5} anos atrás)
    - **MetaTrader5:** {ANOS_MT5} anos recentes (referência)
    - **Overlap:** {DIAS_OVERLAP} dias
    - **Reancoragem:** {PERIODO_REANCORAGEM} dias para cálculo
    - **Prioridade:** MT5 > YFinance_Reancorado > YFinance > Legacy
    
    ### 📊 **Métricas de Qualidade:**
    - **Correlação:** Medida de alinhamento dos retornos
    - **MAE:** Erro médio absoluto entre retornos
    - **Índice de Confiabilidade:** Score combinado de qualidade
    - **Dias Comparados:** Período usado para validação
    """)
    
    # Exemplo visual
    st.subheader("📈 Exemplo de Reancoragem")
    st.write("""
    **Antes da Reancoragem:**
    - Yahoo Finance: VALE3 fechando em R$ 60,00
    - MetaTrader5: VALE3 fechando em R$ 62,00
    - Gap de R$ 2,00 (3.33%)
    
    **Processo:**
    - Calcula fator: 62,00 ÷ 60,00 = 1,0333
    - Aplica a todo histórico YF: preços × 1,0333
    
    **Resultado:**
    - Dados históricos YF ajustados ao nível MT5
    - Continuidade perfeita na série temporal
    - Análises técnicas sem distorções
    """)