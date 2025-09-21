import streamlit as st
import pandas as pd
import os
import io
import re
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
st.title("Gerar listas e coletar dados historicos (MetaTrader5)")
st.markdown("[🔗 Link para baixar lista do Índice Bovespa](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice de ações com governança corporativa diferenciada (IGC B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-governanca/indice-de-acoes-com-governanca-corporativa-diferenciada-igcx-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice Brasil 100 (IBrX 100 B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-100-ibrx-100-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice Brasil Amplo BM&FBOVESPA (IBrA B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-amplo-ibra-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice de BDRs não patrocinado-Global (BDRX B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/indice-de-bdrs-nao-patrocinados-global-bdrx-composicao-da-carteira.htm)")

# === CONFIGURAÇÕES MT5 ===
TIMEFRAME = mt5.TIMEFRAME_D1  # diário
ANOS = 10

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
    # Verificando se tem o padrão de arquivo complexo (várias colunas com ';' como separador)
    return ';' in content_str and re.search(r'[A-Z0-9]{4}[0-9]?;', content_str)

# Função para processar arquivo complexo
def processar_arquivo_complexo(content_str, novo_nome, diretorio):
    linhas = content_str.strip().split('\n')

    codigos = []

    # Definir padrão de ticker com base no nome do arquivo
    if "BDR" in novo_nome.upper():
        padrao_ticker = r'^[A-Z]{4}34$'  # BDRs como AAPL34, MSFT34
    else:
        padrao_ticker = r'^[A-Z]{4}(3|4|11)$'  # Ações como VALE3, ITUB4, BBSE11

    for i, linha in enumerate(linhas):
        linha = linha.strip()
        if linha.startswith('Quantidade') or linha.startswith('Redutor'):
            continue  # Ignorar rodapé
        if i < 2:
            continue  # Ignorar cabeçalhos

        partes = linha.split(';')
        for parte in partes:
            parte = parte.replace('"', '').strip()
            if re.match(padrao_ticker, parte):
                codigos.append(parte)
                break  # Um ticker por linha

    # Salvar em um novo arquivo
    caminho_completo = os.path.join(diretorio, f"{novo_nome}.csv")
    with open(caminho_completo, 'w') as f:
        for codigo in codigos:
            f.write(f"{codigo}\n")

    return True, f"Arquivo complexo processado. '{novo_nome}.csv' salvo com {len(codigos)} tickers!"

# Função principal de processamento que identifica o tipo de arquivo
def processar_arquivo(uploaded_file, novo_nome, diretorio):
    # Ler o conteúdo do arquivo
    content = uploaded_file.read()
    
    # Converter bytes para string e tentar detectar o tipo de arquivo
    content_str = content.decode('utf-8', errors='replace')
    
    # Reiniciar o ponteiro do arquivo para o início
    uploaded_file.seek(0)
    
    # Verificar se é um arquivo complexo
    if detectar_arquivo_complexo(content_str):
        return processar_arquivo_complexo(content_str, novo_nome, diretorio)
    else:
        # Tentar processar como arquivo simples
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
            if ticker:  # Verificar se não é linha vazia
                tickers.append(ticker)
    return tickers

# Função para verificar arquivo parquet corrompido
def verificar_parquet(caminho_bd):
    if os.path.exists(caminho_bd):
        try:
            # Tentar ler o arquivo para verificar se está corrompido
            _ = pd.read_parquet(caminho_bd)
            return True  # Arquivo está ok
        except Exception as e:
            st.warning(f"Arquivo parquet corrompido: {str(e)}. Será criado um novo banco de dados.")
            
            # Remover o arquivo corrompido
            try:
                os.remove(caminho_bd)
            except Exception as del_e:
                st.error(f"Não foi possível remover o arquivo corrompido: {str(del_e)}")
                return False  # Não foi possível resolver o problema
            
            return True  # Arquivo corrompido foi tratado
    return True  # Arquivo não existe, então não há problema

# === FUNÇÕES MT5 ===

def conectar_mt5():
    """Conecta ao MetaTrader5"""
    if not mt5.initialize():
        return False, f"Falha ao inicializar MetaTrader5: {mt5.last_error()}"
    
    # Verificar conexão
    account_info = mt5.account_info()
    if account_info is None:
        mt5.shutdown()
        return False, f"Não conectado ao servidor: {mt5.last_error()}"
    
    return True, f"Conectado à conta: {account_info.login} - Servidor: {account_info.server}"

def verificar_simbolo(ativo):
    """Verifica se o símbolo existe e está disponível"""
    symbols = mt5.symbols_get()
    if symbols is None:
        return False
    
    symbol_names = [s.name for s in symbols]
    return ativo in symbol_names

def obter_primeiro_dado_disponivel(ativo):
    """Obtém a data do primeiro dado disponível para o ativo"""
    try:
        # Tentar obter dados muito antigos (20 anos) para encontrar o início
        data_muito_antiga = datetime.now() - timedelta(days=365 * 20)
        rates = mt5.copy_rates_from(ativo, TIMEFRAME, datetime.now(), 365 * 20)
        
        if rates is not None and len(rates) > 0:
            primeiro_timestamp = rates[0]['time']
            primeira_data = datetime.fromtimestamp(primeiro_timestamp)
            return primeira_data
        
        return None
    except Exception as e:
        st.warning(f"Erro ao buscar primeiro dado de {ativo}: {e}")
        return None

def coletar_dados_ativo_mt5(ativo_original, base_existente, lista_nome):
    """
    Coleta dados do ativo via MT5, tentando variações se necessário
    Retorna: (dados_coletados, nome_ativo_usado, simbolo_encontrado)
    """
    # Lista de variações para tentar
    variantes = [ativo_original, ativo_original + "F"]
    simbolo_encontrado = False
    
    for ativo in variantes:
        # Verificar se símbolo existe
        if not verificar_simbolo(ativo):
            continue
            
        simbolo_encontrado = True
        
        # Descobrir data inicial baseada na base existente
        data_ini_desejada = None
        if not base_existente.empty and ativo_original in base_existente["Ticker"].unique():
            ultima_data = base_existente.loc[
                base_existente["Ticker"] == ativo_original, "Date"
            ].max()
            data_ini_desejada = ultima_data + timedelta(days=1)
        else:
            data_ini_desejada = datetime.now() - timedelta(days=365 * ANOS)
        
        # Descobrir qual é o primeiro dado disponível para este ativo
        primeira_data_disponivel = obter_primeiro_dado_disponivel(ativo)
        
        if primeira_data_disponivel is None:
            continue
        
        # Usar a data mais recente entre a desejada e a disponível
        data_ini = max(data_ini_desejada, primeira_data_disponivel)
        data_fim = datetime.now()
        
        # Tentar coletar dados
        rates = None
        
        try:
            # Primeira tentativa: range específico
            rates = mt5.copy_rates_range(ativo, TIMEFRAME, data_ini, data_fim)
            
            # Se falhar, tentar com copy_rates_from
            if rates is None:
                total_days = min((data_fim - data_ini).days, 365 * ANOS)
                rates = mt5.copy_rates_from(ativo, TIMEFRAME, data_fim, total_days)
                
            # Se ainda não conseguiu, tentar pegar o máximo disponível
            if rates is None:
                rates = mt5.copy_rates_from(ativo, TIMEFRAME, datetime.now(), 365 * ANOS)

        except Exception as e:
            continue

        if rates is None or len(rates) == 0:
            continue
            
        # Filtrar apenas dados novos se for atualização incremental
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        if not base_existente.empty and ativo_original in base_existente["Ticker"].unique():
            # Filtrar apenas dados posteriores à última data
            ultima_data = base_existente.loc[
                base_existente["Ticker"] == ativo_original, "Date"
            ].max()
            df = df[df['time'] > ultima_data]
            
        if len(df) == 0:
            continue

        # Formatar dados - SEMPRE usar o ticker original (sem F)
        df_fmt = pd.DataFrame({
            "Date": df['time'],
            "Open": df['open'],
            "High": df['high'],
            "Low": df['low'],
            "Close": df['close'],
            "Volume": df['tick_volume'].astype("int64"),
            "Ticker": ativo_original,  # SEMPRE o ticker original (sem F)
            "Lista": lista_nome
        })
        
        return df_fmt, ativo, simbolo_encontrado

    if not simbolo_encontrado:
        return None, None, False
    else:
        return None, None, True

# Função para baixar dados históricos usando MetaTrader5
def baixar_dados_historicos_mt5(tickers, nome_lista):
    """Baixa dados históricos via MT5 para uma lista de tickers"""
    
    # Verificar se há tickers para baixar
    if not tickers:
        return False, "Nenhum ticker encontrado para baixar."
    
    # Conectar ao MT5
    conectado, msg_conexao = conectar_mt5()
    if not conectado:
        return False, f"Erro de conexão MT5: {msg_conexao}"
    
    # Caminho para o arquivo parquet
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
    
    # Verificar arquivo parquet corrompido
    if not verificar_parquet(caminho_bd):
        mt5.shutdown()
        return False, "Erro ao tratar o arquivo parquet existente."
    
    # Carregar base existente (se houver)
    if os.path.exists(caminho_bd):
        try:
            base_existente = pd.read_parquet(caminho_bd)
        except:
            base_existente = pd.DataFrame(columns=[
                "Date","Open","High","Low","Close","Volume","Ticker","Lista"
            ])
    else:
        base_existente = pd.DataFrame(columns=[
            "Date","Open","High","Low","Close","Volume","Ticker","Lista"
        ])
    
    # Progress bar para acompanhar o download
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    dados_gerais = []
    ativos_sucesso = []
    ativos_erro = []
    ativos_nao_encontrados = []
    
    # Processar cada ticker
    for i, ticker in enumerate(tickers):
        # Atualizar status
        status_text.text(f"Processando {ticker}... ({i+1}/{len(tickers)})")
        progress_bar.progress((i+1)/len(tickers))
        
        try:
            df_dados, ativo_usado, simbolo_encontrado = coletar_dados_ativo_mt5(
                ticker, base_existente, nome_lista
            )
            
            if df_dados is not None:
                dados_gerais.append(df_dados)
                if ativo_usado != ticker:
                    ativos_sucesso.append(f"{ticker} (dados coletados de {ativo_usado})")
                else:
                    ativos_sucesso.append(f"{ticker}")
            elif not simbolo_encontrado:
                ativos_nao_encontrados.append(ticker)
            else:
                ativos_erro.append(ticker)

        except Exception as e:
            st.warning(f"Erro inesperado ao processar {ticker}: {e}")
            ativos_erro.append(ticker)
        
        # Pequena pausa para evitar sobrecarga
        time.sleep(0.1)
    
    # Limpar progress bar e status
    progress_bar.empty()
    status_text.empty()
    
    # Desconectar do MT5
    mt5.shutdown()
    
    # Verificar se algum dado foi baixado
    if not dados_gerais:
        mensagem_erro = f"Nenhum dado coletado para a lista '{nome_lista}'.\n"
        if ativos_nao_encontrados:
            mensagem_erro += f"Símbolos não encontrados: {len(ativos_nao_encontrados)}\n"
        if ativos_erro:
            mensagem_erro += f"Erros na coleta: {len(ativos_erro)}"
        return False, mensagem_erro
    
    # Consolidar dados
    novos_dados = pd.concat(dados_gerais, ignore_index=True)
    
    # Remover dados antigos da mesma lista (para atualização)
    if not base_existente.empty and 'Lista' in base_existente.columns:
        base_existente = base_existente[base_existente['Lista'] != nome_lista]
        
        # Concatenar com novos dados
        if not base_existente.empty:
            dados_finais = pd.concat([base_existente, novos_dados], ignore_index=True)
        else:
            dados_finais = novos_dados
    else:
        dados_finais = novos_dados
    
    # Garantir que o diretório exista
    os.makedirs(os.path.dirname(caminho_bd), exist_ok=True)
    
    # Salvar os dados em formato parquet
    try:
        # Classificar os dados por Lista, Ticker e Date
        dados_finais = dados_finais.sort_values(by=['Lista', 'Ticker', 'Date'])
        dados_finais = dados_finais.drop_duplicates(subset=["Date","Ticker"])
        
        # Salvar o DataFrame em formato parquet
        dados_finais.to_parquet(caminho_bd, index=False)
        
        # Criar mensagem de resumo
        mensagem_sucesso = f"Lista '{nome_lista}' atualizada!\n"
        mensagem_sucesso += f"✅ Sucessos: {len(ativos_sucesso)}\n"
        if ativos_erro:
            mensagem_sucesso += f"⚠️ Erros na coleta: {len(ativos_erro)}\n"
        if ativos_nao_encontrados:
            mensagem_sucesso += f"❌ Não encontrados: {len(ativos_nao_encontrados)}\n"
        mensagem_sucesso += f"📊 Novos registros: {len(novos_dados)}"
        
        return True, mensagem_sucesso
        
    except Exception as e:
        return False, f"Erro ao salvar o banco de dados: {str(e)}"

# Função para atualizar dados históricos de uma lista específica
def atualizar_lista(nome_arquivo, diretorio):
    # Caminho completo do arquivo
    caminho_arquivo = os.path.join(diretorio, nome_arquivo)
    
    # Nome da lista (sem extensão)
    nome_lista = extrair_nome_arquivo(nome_arquivo)
    
    # Ler tickers do arquivo
    tickers = ler_tickers_do_arquivo(caminho_arquivo)
    
    # Baixar dados históricos via MT5
    sucesso, mensagem = baixar_dados_historicos_mt5(tickers, nome_lista)
    
    return sucesso, mensagem

# Função para atualizar todas as listas
def atualizar_todas_listas(diretorio):
    arquivos = listar_arquivos(diretorio)
    
    if not arquivos:
        return False, "Nenhuma lista encontrada para atualizar."
    
    resultados = []
    
    for arquivo in arquivos:
        sucesso, mensagem = atualizar_lista(arquivo, diretorio)
        status = '✅' if sucesso else '❌'
        resultados.append(f"{status} Lista '{extrair_nome_arquivo(arquivo)}'")
        if not sucesso:
            st.error(f"Erro na lista {arquivo}: {mensagem}")
    
    return True, f"Processo de atualização concluído:\n" + "\n".join(resultados)

def remover_dados_historicos_por_lista(nome_lista):
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
    
    if not os.path.exists(caminho_bd):
        return True  # Não há dados para remover
    
    try:
        # Carregar o banco de dados existente
        df = pd.read_parquet(caminho_bd)
        
        # Verificar se a coluna 'Lista' existe
        if 'Lista' not in df.columns:
            return True  # Não há dados associados a listas
        
        # Filtrar para manter apenas os dados que NÃO pertencem à lista que está sendo excluída
        df_filtrado = df[df['Lista'] != nome_lista]
        
        # Salvar o DataFrame filtrado de volta ao arquivo parquet
        df_filtrado.to_parquet(caminho_bd, index=False)
        
        return True
    except Exception as e:
        st.error(f"Erro ao remover dados históricos da lista '{nome_lista}': {str(e)}")
        return False

# === INTERFACE PRINCIPAL ===

# Status de conexão MT5
st.header("Status da Conexão MetaTrader5")
conectado, msg_conexao = conectar_mt5()
if conectado:
    st.success(msg_conexao)
    mt5.shutdown()  # Desconectar após teste
else:
    st.error(msg_conexao)
    st.warning("⚠️ MetaTrader5 não está conectado. Verifique se o MT5 está aberto e conectado a um servidor.")

# Criar diretório se não existir
diretorio = criar_diretorio()

# Interface principal
st.header("Upload e Processamento de Arquivo CSV")

# Upload de arquivo
uploaded_file = st.file_uploader("Selecione um arquivo CSV", type=['csv'])

if uploaded_file is not None:
    # Sugerir nome baseado no arquivo original
    nome_sugerido = extrair_nome_arquivo(uploaded_file.name)
    
    # Entrada para o novo nome com valor sugerido
    novo_nome = st.text_input("Digite um nome para o arquivo (sem extensão):", value=nome_sugerido)
    
    if novo_nome:
        if st.button("Processar e Salvar"):
            sucesso, mensagem = processar_arquivo(uploaded_file, novo_nome, diretorio)
            if sucesso:
                st.success(mensagem)
            else:
                st.error(mensagem)

# Seção para gerenciar arquivos existentes
st.header("Gerenciar Arquivos Existentes")

arquivos = listar_arquivos(diretorio)
if arquivos:
    st.write(f"Arquivos na pasta '{diretorio}':")
    
    # Exibir lista de arquivos com opções de exclusão e atualização individual
    for arquivo in arquivos:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(arquivo)
        with col2:
            if st.button("Excluir", key=f"del_{arquivo}"):
                nome_lista = extrair_nome_arquivo(arquivo)
                # Primeiro remove o arquivo da lista
                os.remove(os.path.join(diretorio, arquivo))
                # Depois remove os dados históricos correspondentes
                if remover_dados_historicos_por_lista(nome_lista):
                    st.success(f"Arquivo '{arquivo}' e seus dados históricos foram excluídos com sucesso!")
                else:
                    st.error(f"Arquivo '{arquivo}' foi excluído, mas houve um problema ao remover os dados históricos.")
                st.rerun()
        with col3:
            if st.button("Atualizar", key=f"upd_{arquivo}"):
                with st.spinner(f"Atualizando lista '{arquivo}' via MT5..."):
                    sucesso, mensagem = atualizar_lista(arquivo, diretorio)
                    if sucesso:
                        st.success(mensagem)
                    else:
                        st.error(mensagem)
    
    # Linha com botões para ações em massa
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Excluir Todos os Arquivos"):
            # Primeiro remove todos os arquivos de lista
            for arquivo in arquivos:
                os.remove(os.path.join(diretorio, arquivo))
            
            # Depois remove o arquivo parquet completo
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
        if st.button("Atualizar Todas as Listas"):
            with st.spinner("Atualizando todas as listas via MT5..."):
                sucesso, mensagem = atualizar_todas_listas(diretorio)
                if sucesso:
                    st.success(mensagem)
                else:
                    st.error(mensagem)
else:
    st.info("Nenhum arquivo encontrado no diretório.")

# Exibir informações sobre o banco de dados de cotações
st.header("Informações do Banco de Dados de Cotações")
caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")

if os.path.exists(caminho_bd):
    try:
        # Verificar arquivo parquet antes de carregar
        if verificar_parquet(caminho_bd):
            # Carregar dados para exibir informações resumidas
            df_info = pd.read_parquet(caminho_bd)
            
            # Exibir informações básicas
            st.write(f"Total de registros: {len(df_info):,}")
            
            # Exibir todas as colunas disponíveis para depuração
            st.write("Colunas disponíveis no banco de dados:", df_info.columns.tolist())
            
            # Normalizar nomes das colunas
            date_cols = [col for col in df_info.columns if 'date' in str(col).lower()]
            if date_cols and 'Date' not in df_info.columns:
                df_info.rename(columns={date_cols[0]: 'Date'}, inplace=True)
                
            ticker_cols = [col for col in df_info.columns if 'ticker' in str(col).lower()]
            if ticker_cols and 'Ticker' not in df_info.columns:
                df_info.rename(columns={ticker_cols[0]: 'Ticker'}, inplace=True)
                
            lista_cols = [col for col in df_info.columns if 'lista' in str(col).lower()]
            if lista_cols and 'Lista' not in df_info.columns:
                df_info.rename(columns={lista_cols[0]: 'Lista'}, inplace=True)
            
            # Verificar todas as colunas necessárias
            colunas_esperadas = ['Date', 'Lista', 'Ticker']
            colunas_faltantes = [col for col in colunas_esperadas if col not in df_info.columns]
            
            if colunas_faltantes:
                st.warning(f"As seguintes colunas estão faltando no banco de dados: {', '.join(colunas_faltantes)}")
                
                # Criar colunas faltantes com valores padrão para permitir visualização
                for col in colunas_faltantes:
                    df_info[col] = "N/A"
                    
                st.info("Colunas faltantes foram criadas temporariamente com valores 'N/A' para permitir visualização.")
                st.info("Utilize a função 'Atualizar Todas as Listas' para reconstruir o banco de dados corretamente.")
            
            # Exibir informações por lista
            st.write("Dados por lista:")
            resumo_listas = df_info.groupby('Lista')['Ticker'].nunique().reset_index()
            resumo_listas.columns = ['Lista', 'Quantidade de Tickers']
            st.dataframe(resumo_listas)
            
            # Exibir intervalo de datas
            try:
                min_data = pd.to_datetime(df_info['Date']).min().strftime('%d/%m/%Y')
                max_data = pd.to_datetime(df_info['Date']).max().strftime('%d/%m/%Y')
                st.write(f"Período: {min_data} até {max_data}")
            except:
                st.warning("Não foi possível determinar o intervalo de datas.")
            
            # Exibir tickers únicos
            tickers_unicos = df_info['Ticker'].nunique()
            st.write(f"Total de tickers únicos: {tickers_unicos}")
        else:
            st.error("Não foi possível acessar o banco de dados. O arquivo parquet pode estar corrompido.")
                
    except Exception as e:
        st.error(f"Erro ao carregar informações do banco de dados: {str(e)}")
else:
    st.info("Banco de dados de cotações ainda não foi criado.")

# Seção para visualizar os últimos registros atualizados
st.header("Últimos Registros Atualizados")
caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")

if os.path.exists(caminho_bd):
    try:
        # Verificar arquivo parquet antes de carregar
        if verificar_parquet(caminho_bd):
            # Carregar dados para exibir últimos registros
            df_ultimos = pd.read_parquet(caminho_bd)
            
            # Ordenar por data decrescente para mostrar os mais recentes primeiro
            if 'Date' in df_ultimos.columns:
                try:
                    df_ultimos['Date'] = pd.to_datetime(df_ultimos['Date'])
                    df_ultimos = df_ultimos.sort_values(by='Date', ascending=False)
                except:
                    st.warning("Não foi possível ordenar por data. Mostrando os últimos registros na ordem atual.")
            
            # Mostrar os 50 últimos registros
            st.write(f"Exibindo os 50 últimos registros do banco de dados (total: {len(df_ultimos):,}):")
            
            # Opções de filtro
            col1, col2 = st.columns(2)
            with col1:
                if 'Lista' in df_ultimos.columns:
                    listas_disponiveis = ['Todas'] + sorted(df_ultimos['Lista'].unique().tolist())
                    lista_selecionada = st.selectbox('Filtrar por lista:', listas_disponiveis)
            
            with col2:
                if 'Ticker' in df_ultimos.columns:
                    tickers_disponiveis = ['Todos'] + sorted(df_ultimos['Ticker'].unique().tolist())
                    ticker_selecionado = st.selectbox('Filtrar por ticker:', tickers_disponiveis)
            
            # Aplicar filtros
            df_filtrado = df_ultimos.copy()
            if 'Lista' in df_ultimos.columns and lista_selecionada != 'Todas':
                df_filtrado = df_filtrado[df_filtrado['Lista'] == lista_selecionada]
            
            if 'Ticker' in df_ultimos.columns and ticker_selecionado != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['Ticker'] == ticker_selecionado]
            
            # Exibir dataframe filtrado
            st.dataframe(df_filtrado.head(50))
            
            # Opção para baixar os dados filtrados
            if not df_filtrado.empty:
                csv = df_filtrado.head(50).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Baixar dados visualizados como CSV",
                    data=csv,
                    file_name=f"dados_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.error("Não foi possível acessar o banco de dados. O arquivo parquet pode estar corrompido.")
                
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco para visualização: {str(e)}")

else:
    st.info("Banco de dados de cotações ainda não foi criado.")
    
    # Botão para criar banco de dados (em vez de criar automaticamente)
    if st.button("Criar banco de dados agora"):
        with st.spinner("Atualizando todas as listas para criar o banco de dados via MT5..."):
            sucesso, mensagem = atualizar_todas_listas(diretorio)
            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(f"Erro ao criar o banco de dados: {mensagem}")

# Botão para resetar o banco de dados se necessário
with st.expander("Opções avançadas"):
    st.subheader("Configurações MetaTrader5")
    
    # Mostrar configurações atuais
    st.write(f"**Timeframe:** {TIMEFRAME} (Diário)")
    st.write(f"**Período histórico:** {ANOS} anos")
    
    st.info("💡 **Dica:** Certifique-se de que o MetaTrader5 esteja aberto e conectado a um servidor antes de atualizar as listas.")
    
    # Teste de conexão manual
    if st.button("🔍 Testar Conexão MT5"):
        conectado, msg = conectar_mt5()
        if conectado:
            st.success(f"✅ {msg}")
            
            # Mostrar alguns símbolos disponíveis como exemplo
            try:
                symbols = mt5.symbols_get()
                if symbols:
                    symbols_br = [s.name for s in symbols if any(s.name.endswith(suffix) for suffix in ['3', '4', '11', 'F']) and len(s.name) <= 6][:10]
                    if symbols_br:
                        st.write("**Exemplos de símbolos brasileiros disponíveis:**")
                        st.write(", ".join(symbols_br))
            except:
                pass
            
            mt5.shutdown()
        else:
            st.error(f"❌ {msg}")
    
    st.subheader("Gerenciamento do Banco de Dados")
    
    if st.button("🔄 Resetar banco de dados de cotações"):
        if os.path.exists(caminho_bd):
            # Excluir o arquivo sem criar backup
            try:
                os.remove(caminho_bd)
                st.success("Banco de dados resetado com sucesso!")
                st.info("Execute 'Atualizar Todas as Listas' para recriar o banco de dados.")
            except Exception as e:
                st.error(f"Erro ao excluir o banco de dados: {str(e)}")
        else:
            st.info("Não existe banco de dados para resetar.")

# Seção de informações adicionais
with st.expander("ℹ️ Informações sobre MetaTrader5"):
    st.markdown("""
    ### Como usar este aplicativo com MetaTrader5:
    
    1. **Instale o MetaTrader5** em seu computador
    2. **Abra o MT5** e conecte-se a um servidor que tenha ações brasileiras (ex: XP Investimentos, Rico, etc.)
    3. **Mantenha o MT5 aberto** durante a coleta de dados
    4. **Faça upload dos arquivos CSV** com as listas de ativos
    5. **Clique em "Atualizar"** para coletar os dados históricos
    
    ### Vantagens do MT5 vs Yahoo Finance:
    - ✅ Dados mais precisos e atualizados
    - ✅ Horários de abertura e fechamento corretos para o mercado brasileiro
    - ✅ Dados de volume mais confiáveis
    - ✅ Menos limitações de API
    - ✅ Dados em tempo real (quando o mercado está aberto)
    
    ### Símbolos suportados:
    - **Ações:** VALE3, ITUB4, PETR4, etc.
    - **FIIs:** HGLG11, XPLG11, etc.
    - **BDRs:** AAPL34, MSFT34, etc.
    
    ### Notas importantes:
    - O aplicativo tentará automaticamente variações dos símbolos (ex: VALE3 e VALE3F)
    - Dados são coletados em timeframe diário
    - O período padrão é de 10 anos de histórico
    - Atualizações incrementais: apenas novos dados são baixados
    """)