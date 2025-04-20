import streamlit as st
import pandas as pd
import os
import io
import re
import yfinance as yf
from datetime import datetime, timedelta
import time

# Título do aplicativo
st.title("Processador de Arquivos CSV e Atualização de Cotações")
st.markdown("[🔗 Link para baixar lista do Índice de ações com governança corporativa diferenciada (IGC B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-governanca/indice-de-acoes-com-governanca-corporativa-diferenciada-igcx-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice Brasil 100 (IBrX 100 B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-100-ibrx-100-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice Brasil Amplo BM&FBOVESPA (IBrA B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-amplo-ibra-composicao-da-carteira.htm)")
st.markdown("[🔗 Link para baixar lista do Índice de BDRs não patrocinado-Global (BDRX B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/indice-de-bdrs-nao-patrocinados-global-bdrx-composicao-da-carteira.htm)")

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

# Função para baixar dados históricos usando yfinance
def baixar_dados_historicos(tickers, nome_lista):
    # Verificar se há tickers para baixar
    if not tickers:
        return False, "Nenhum ticker encontrado para baixar."
    
    # Configurar período de download
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=5*365)  # 5 anos
    
    # Criar DataFrame vazio para armazenar todos os dados
    all_data = pd.DataFrame()
    
    # Progress bar para acompanhar o download
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Baixar dados para cada ticker individualmente
    for i, ticker in enumerate(tickers):
        # Atualizar status
        status_text.text(f"Baixando dados para {ticker}... ({i+1}/{len(tickers)})")
        progress_bar.progress((i+1)/len(tickers))
        
        try:
            # Adicionar sufixo .SA para tickers brasileiros
            ticker_yf = f"{ticker}.SA"
            
            # Baixar dados para um único ticker
            dados = yf.download(ticker_yf, 
                               start=data_inicio.strftime('%Y-%m-%d'), 
                               end=data_fim.strftime('%Y-%m-%d'), 
                               progress=False)
            
            if not dados.empty:
                # Resetar o índice para transformar a data em coluna
                dados.reset_index(inplace=True)
                
                # Em vez de renomear, apenas adicionar as colunas que precisamos
                dados_processados = pd.DataFrame()
                dados_processados['Date'] = dados['Date']
                
                # Adicionar colunas padrão se existirem, ou None se não existirem
                for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
                    if col in dados.columns:
                        dados_processados[col] = dados[col]
                    else:
                        dados_processados[col] = None
                
                # Adicionar informações do ticker e nome da lista
                dados_processados['Ticker'] = ticker
                dados_processados['Lista'] = nome_lista
                
                # Concatenar com os dados existentes
                all_data = pd.concat([all_data, dados_processados], ignore_index=True)
                
            # Pequena pausa para evitar sobrecarga na API
            time.sleep(0.1)
            
        except Exception as e:
            st.warning(f"Erro ao baixar dados para {ticker}: {str(e)}")
    
    # Limpar progress bar e status
    progress_bar.empty()
    status_text.empty()
    
    # Verificar se algum dado foi baixado
    if all_data.empty:
        return False, "Não foi possível baixar dados para nenhum ticker."
    
    # Caminho para o arquivo parquet
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
    
    # Verificar arquivo parquet corrompido
    if not verificar_parquet(caminho_bd):
        return False, "Erro ao tratar o arquivo parquet existente. Por favor, exclua manualmente o arquivo e tente novamente."
    
    # Verificar se o arquivo já existe
    if os.path.exists(caminho_bd):
        try:
            # Carregar dados existentes
            dados_existentes = pd.read_parquet(caminho_bd)
            
            # Remover registros antigos da mesma lista (para atualização)
            if 'Lista' in dados_existentes.columns:
                dados_existentes = dados_existentes[dados_existentes['Lista'] != nome_lista]
                
                # Garantir que todas as colunas necessárias existam
                colunas_necessarias = ['Lista', 'Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
                for col in colunas_necessarias:
                    if col not in dados_existentes.columns:
                        dados_existentes[col] = None
                
                # Concatenar com novos dados
                if not dados_existentes.empty:
                    # Primeiro garantir que ambos os DataFrames tenham as mesmas colunas
                    all_columns = set(list(dados_existentes.columns) + list(all_data.columns))
                    for col in all_columns:
                        if col not in dados_existentes.columns:
                            dados_existentes[col] = None
                        if col not in all_data.columns:
                            all_data[col] = None
                    
                    dados_finais = pd.concat([dados_existentes, all_data], ignore_index=True)
                else:
                    dados_finais = all_data
            else:
                dados_finais = all_data
                
        except Exception as e:
            # Se houver erro ao carregar o arquivo existente, usar apenas os novos dados
            st.warning(f"Não foi possível ler o arquivo existente: {str(e)}. Criando um novo banco de dados.")
            dados_finais = all_data
    else:
        dados_finais = all_data
    
    # Garantir que o diretório exista
    os.makedirs(os.path.dirname(caminho_bd), exist_ok=True)
    
    # Salvar os dados em formato parquet
    try:
        # Se o arquivo existir, removê-lo antes de salvar (sem backup)
        if os.path.exists(caminho_bd):
            os.remove(caminho_bd)

        # Antes de salvar, classificar os dados por Lista, Ticker e Date
        dados_finais = dados_finais.sort_values(by=['Lista', 'Ticker', 'Date'])    
        # Salvar o DataFrame em formato parquet
        dados_finais.to_parquet(caminho_bd, index=False)
        
        return True, f"Dados históricos de {len(tickers)} tickers da lista '{nome_lista}' foram atualizados com sucesso!"
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
    
    # Baixar dados históricos
    sucesso, mensagem = baixar_dados_historicos(tickers, nome_lista)
    
    return sucesso, mensagem

# Função para atualizar todas as listas
def atualizar_todas_listas(diretorio):
    arquivos = listar_arquivos(diretorio)
    
    if not arquivos:
        return False, "Nenhuma lista encontrada para atualizar."
    
    resultados = []
    
    for arquivo in arquivos:
        sucesso, mensagem = atualizar_lista(arquivo, diretorio)
        resultados.append(f"Lista '{extrair_nome_arquivo(arquivo)}': {'✓' if sucesso else '✗'}")
    
    return True, f"Processo de atualização concluído:\n" + "\n".join(resultados)

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
                os.remove(os.path.join(diretorio, arquivo))
                st.success(f"Arquivo '{arquivo}' excluído com sucesso!")
                st.rerun()
        with col3:
            if st.button("Atualizar", key=f"upd_{arquivo}"):
                with st.spinner(f"Atualizando lista '{arquivo}'..."):
                    sucesso, mensagem = atualizar_lista(arquivo, diretorio)
                    if sucesso:
                        st.success(mensagem)
                    else:
                        st.error(mensagem)
    
    # Linha com botões para ações em massa
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Excluir Todos os Arquivos"):
            for arquivo in arquivos:
                os.remove(os.path.join(diretorio, arquivo))
            st.success("Todos os arquivos foram excluídos!")
            st.rerun()
    with col2:
        if st.button("Atualizar Todas as Listas"):
            with st.spinner("Atualizando todas as listas..."):
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
        with st.spinner("Atualizando todas as listas para criar o banco de dados..."):
            sucesso, mensagem = atualizar_todas_listas(diretorio)
            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(f"Erro ao criar o banco de dados: {mensagem}")

# Botão para resetar o banco de dados se necessário
with st.expander("Opções avançadas"):
    if st.button("Resetar banco de dados de cotações"):
        if os.path.exists(caminho_bd):
            # Excluir o arquivo sem criar backup
            try:
                os.remove(caminho_bd)
                st.success("Banco de dados resetado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao excluir o banco de dados: {str(e)}")
        else:
            st.info("Não existe banco de dados para resetar.")