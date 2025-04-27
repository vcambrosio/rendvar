import streamlit as st
import pandas as pd
import os
import re
import yfinance as yf
from datetime import datetime, timedelta
import time
from PIL import Image
import logging

# ===============================
# Configuração Inicial
# ===============================

# Configuração do logging
logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,  # Altere para DEBUG para mais detalhes
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def configurar_sidebar():
    """
    Configura a barra lateral do Streamlit com logo e informações do desenvolvedor.
    """
    with st.sidebar:
        col_logo, col_texto = st.columns([1, 3])

        with col_logo:
            logo_path = os.path.join("02-imagens", "logo.png")
            if os.path.exists(logo_path):
                logo = Image.open(logo_path)
                base_width = 50
                w_percent = base_width / float(logo.size[0])
                h_size = int((float(logo.size[1]) * float(w_percent)))
                logo = logo.resize((base_width, h_size), Image.Resampling.LANCZOS)
                st.image(logo, use_container_width=False)

        with col_texto:
            st.markdown(
                """
            <div style='display: flex; align-items: center; height: 100%;'>
                <p style='margin: 0;'>Desenvolvido por Vladimir</p>
            </div>
            """,
                unsafe_allow_html=True,
            )


def configurar_pagina():
    """
    Configura o título e os links da página principal do Streamlit.
    """
    st.title("Gerar listas e coletar dados historicos")
    st.markdown(
        "[🔗 Link para baixar lista do Índice de ações com governança corporativa diferenciada (IGC B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-governanca/indice-de-acoes-com-governanca-corporativa-diferenciada-igcx-composicao-da-carteira.htm)"
    )
    st.markdown(
        "[🔗 Link para baixar lista do Índice Brasil 100 (IBrX 100 B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-100-ibrx-100-composicao-da-carteira.htm)"
    )
    st.markdown(
        "[🔗 Link para baixar lista do Índice Brasil Amplo BM&FBOVESPA (IBrA B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-brasil-amplo-ibra-composicao-da-carteira.htm)"
    )
    st.markdown(
        "[🔗 Link para baixar lista do Índice de BDRs não patrocinado-Global (BDRX B3)](https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/indice-de-bdrs-nao-patrocinados-global-bdrx-composicao-da-carteira.htm)"
    )


# ===============================
# Funções de Manipulação de Arquivos
# ===============================
def criar_diretorio(diretorio="01-dados/listas_csv"):
    """
    Cria o diretório especificado se ele não existir.

    Args:
        diretorio (str, opcional): O caminho do diretório a ser criado.
            Padrão é "01-dados/listas_csv".

    Returns:
        str: O caminho do diretório criado.
    """
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    return diretorio


def listar_arquivos(diretorio):
    """
    Lista todos os arquivos CSV no diretório especificado.

    Args:
        diretorio (str): O caminho do diretório a ser listado.

    Returns:
        list: Uma lista de nomes de arquivos CSV.
    """
    if os.path.exists(diretorio):
        return [f for f in os.listdir(diretorio) if f.endswith(".csv")]
    return []


def extrair_nome_arquivo(nome_arquivo):
    """
    Extrai o nome do arquivo sem a extensão.

    Args:
        nome_arquivo (str): O nome do arquivo completo.

    Returns:
        str: O nome do arquivo sem a extensão.
    """
    return os.path.splitext(nome_arquivo)[0]


def ler_tickers_do_arquivo(caminho_arquivo):
    """
    Lê os tickers de um arquivo CSV, ignorando linhas vazias.

    Args:
        caminho_arquivo (str): O caminho do arquivo CSV.

    Returns:
        list: Uma lista de tickers.
    """
    tickers = []
    try:
        with open(caminho_arquivo, "r") as file:
            for linha in file:
                ticker = linha.strip()
                if ticker:  # Verifica se a linha não está vazia
                    tickers.append(ticker)
    except FileNotFoundError:
        st.error(f"Arquivo não encontrado: {caminho_arquivo}")
        return []
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return []
    return tickers


# ===============================
# Funções de Processamento de Arquivos CSV
# ===============================


def detectar_arquivo_complexo(content_str):
    """
    Detecta se o arquivo CSV tem um formato complexo (múltiplas colunas e ';' como separador).

    Args:
        content_str (str): O conteúdo do arquivo CSV como string.

    Returns:
        bool: True se o arquivo for complexo, False caso contrário.
    """
    return ";" in content_str and re.search(r"[A-Z0-9]{4}[0-9]?;", content_str)


def processar_arquivo_simples(uploaded_file, novo_nome, diretorio):
    """
    Processa um arquivo CSV simples (uma coluna 'Código').

    Args:
        uploaded_file (UploadedFile): O arquivo CSV enviado pelo usuário.
        novo_nome (str): O novo nome para o arquivo processado.
        diretorio (str): O diretório onde o arquivo será salvo.

    Returns:
        tuple: (True, mensagem) em caso de sucesso, (False, mensagem) em caso de erro.
    """
    try:
        df = pd.read_csv(uploaded_file)
    except pd.errors.EmptyDataError:
        return False, "O arquivo está vazio."
    except Exception as e:
        return False, f"Erro ao ler o arquivo CSV: {e}"

    if "Código" not in df.columns:
        return False, "O arquivo deve conter uma coluna chamada 'Código'."

    codigos = df["Código"].tolist()
    caminho_completo = os.path.join(diretorio, f"{novo_nome}.csv")
    try:
        with open(caminho_completo, "w") as f:
            for codigo in codigos:
                f.write(f"{codigo}\n")
    except Exception as e:
        return False, f"Erro ao salvar o arquivo: {e}"

    return True, f"Arquivo '{novo_nome}.csv' salvo com sucesso!"


def processar_arquivo_complexo(content_str, novo_nome, diretorio):
    """
    Processa um arquivo CSV complexo (múltiplas colunas e ';' como separador).

    Args:
        content_str (str): O conteúdo do arquivo CSV como string.
        novo_nome (str): O novo nome para o arquivo processado.
        diretorio (str): O diretório onde o arquivo será salvo.

    Returns:
        tuple: (True, mensagem) em caso de sucesso, (False, mensagem) em caso de erro.
    """
    linhas = content_str.strip().split("\n")
    codigos = []
    padrao_ticker = (
        r"^[A-Z]{4}34$"
        if "BDR" in novo_nome.upper()
        else r"^[A-Z]{4}(3|4|11)$"
    )  # Padrão do Ticker

    for i, linha in enumerate(linhas):
        linha = linha.strip()
        if linha.startswith("Quantidade") or linha.startswith("Redutor"):
            continue  # Ignora rodapé
        if i < 2:
            continue  # Ignora cabeçalhos

        partes = linha.split(";")
        for parte in partes:
            parte = parte.replace('"', "").strip()
            if re.match(padrao_ticker, parte):
                codigos.append(parte)
                break  # Um ticker por linha

    caminho_completo = os.path.join(diretorio, f"{novo_nome}.csv")
    try:
        with open(caminho_completo, "w") as f:
            for codigo in codigos:
                f.write(f"{codigo}\n")
    except Exception as e:
        return False, f"Erro ao salvar arquivo: {e}"
    return (
        True,
        f"Arquivo complexo processado. '{novo_nome}.csv' salvo com {len(codigos)} tickers!",
    )


def processar_arquivo(uploaded_file, novo_nome, diretorio):
    """
    Processa o arquivo CSV enviado, detectando automaticamente o formato.

    Args:
        uploaded_file (UploadedFile): O arquivo CSV enviado pelo usuário.
        novo_nome (str): O novo nome para o arquivo processado.
        diretorio (str): O diretório onde o arquivo será salvo.

    Returns:
        tuple: (True, mensagem) em caso de sucesso, (False, mensagem) em caso de erro.
    """
    content = uploaded_file.read()
    content_str = content.decode("utf-8", errors="replace")
    uploaded_file.seek(0)  # Reseta o ponteiro do arquivo

    if detectar_arquivo_complexo(content_str):
        return processar_arquivo_complexo(content_str, novo_nome, diretorio)
    else:
        try:
            return processar_arquivo_simples(uploaded_file, novo_nome, diretorio)
        except Exception as e:
            return False, f"Erro ao processar o arquivo: {e}"


# ===============================
# Funções de Manipulação do Banco de Dados (Parquet)
# ===============================
def verificar_parquet(caminho_bd):
    """
    Verifica se um arquivo Parquet está corrompido.

    Args:
        caminho_bd (str): O caminho do arquivo Parquet.

    Returns:
        bool: True se o arquivo estiver OK ou não existir, False se estiver corrompido e não puder ser tratado.
    """
    if os.path.exists(caminho_bd):
        try:
            pd.read_parquet(caminho_bd)
            return True
        except Exception as e:
            st.warning(
                f"Arquivo parquet corrompido: {e}. Será criado um novo banco de dados."
            )
            try:
                os.remove(caminho_bd)
            except Exception as del_e:
                st.error(
                    f"Não foi possível remover o arquivo corrompido: {del_e}."
                )  # Mostra erro
                logging.error(
                    f"Não foi possível remover o arquivo corrompido: {del_e}."
                )  # Registra erro
                return False
            return True
    return True


def baixar_dados_historicos(tickers, nome_lista):
    """
    Baixa dados históricos de ações usando a biblioteca yfinance e salva no formato Parquet.

    Args:
        tickers (list): Uma lista de tickers de ações.
        nome_lista (str): O nome da lista de tickers (usado para identificação no banco de dados).

    Returns:
        tuple: (True, mensagem) em caso de sucesso, (False, mensagem) em caso de erro.
    """
    if not tickers:
        return False, "Nenhum ticker encontrado para baixar."

    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=10 * 365)  # 10 anos

    all_data = pd.DataFrame()
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(tickers):
        status_text.text(f"Baixando dados para {ticker}... ({i+1}/{len(tickers)})")
        progress_bar.progress((i + 1) / len(tickers))
        try:
            ticker_yf = f"{ticker}.SA"  # Adiciona sufixo para Brasil
            dados = yf.download(
                ticker_yf,
                start=data_inicio.strftime("%Y-%m-%d"),
                end=data_fim.strftime("%Y-%m-%d"),
                progress=False,
            )

            if not dados.empty:
                dados.reset_index(inplace=True)
                dados_processados = pd.DataFrame()
                dados_processados["Date"] = dados["Date"]

                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    if col in dados.columns:
                        dados_processados[col] = dados[col]
                    else:
                        dados_processados[col] = None

                dados_processados["Ticker"] = ticker
                dados_processados["Lista"] = nome_lista
                all_data = pd.concat([all_data, dados_processados], ignore_index=True)

            time.sleep(0.1)  # Pausa para evitar sobrecarga
        except yf.YFinanceError as yf_error:
            logging.error(f"Erro do yfinance ao baixar dados para {ticker}: {yf_error}")
            st.warning(f"Erro ao baixar dados para {ticker}: {yf_error}")
        except Exception as e:
            logging.error(f"Erro inesperado ao baixar dados para {ticker}: {e}")
            st.error(f"Erro ao baixar dados para {ticker}: {e}")

    progress_bar.empty()
    status_text.empty()

    if all_data.empty:
        return False, "Não foi possível baixar dados para nenhum ticker."

    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")

    if not verificar_parquet(caminho_bd):
        return (
            False,
            "Erro ao tratar o arquivo parquet existente. Por favor, exclua-o manualmente e tente novamente.",
        )

    try:
        if os.path.exists(caminho_bd):
            dados_existentes = pd.read_parquet(caminho_bd)
            if "Lista" in dados_existentes.columns:
                dados_existentes = dados_existentes[
                    dados_existentes["Lista"] != nome_lista
                ]

                colunas_necessarias = [
                    "Lista",
                    "Ticker",
                    "Date",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                ]
                for col in colunas_necessarias:
                    if col not in dados_existentes.columns:
                        dados_existentes[col] = None

                if not dados_existentes.empty:
                    all_columns = set(
                        list(dados_existentes.columns) + list(all_data.columns)
                    )
                    for col in all_columns:
                        if col not in dados_existentes.columns:
                            dados_existentes[col] = None
                        if col not in all_data.columns:
                            all_data[col] = None

                    dados_finais = pd.concat(
                        [dados_existentes, all_data], ignore_index=True
                    )
                else:
                    dados_finais = all_data
            else:
                dados_finais = all_data
        else:
            dados_finais = all_data
    except Exception as e:
        logging.error(f"Erro ao carregar/concatenar dados: {e}")
        st.warning(f"Erro ao carregar dados existentes: {e}. Criando novo banco de dados.")
        dados_finais = all_data

    os.makedirs(os.path.dirname(caminho_bd), exist_ok=True)

    try:
        if os.path.exists(caminho_bd):
            os.remove(caminho_bd)

        dados_finais = dados_finais.sort_values(
            by=["Lista", "Ticker", "Date"]
        )  # Ordena os dados
        dados_finais.to_parquet(caminho_bd, index=False)
        return (
            True,
            f"Dados históricos de {len(tickers)} tickers da lista '{nome_lista}' foram atualizados com sucesso!",
        )
    except Exception as e:
        logging.error(f"Erro ao salvar dados no arquivo Parquet: {e}")
        return False, f"Erro ao salvar o banco de dados: {e}"


def atualizar_lista(nome_arquivo, diretorio):
    """
    Atualiza os dados históricos para uma lista de tickers específica.

    Args:
        nome_arquivo (str): O nome do arquivo CSV contendo os tickers.
        diretorio (str): O diretório onde o arquivo CSV está localizado.

    Returns:
        tuple: (True, mensagem) em caso de sucesso, (False, mensagem) em caso de erro.
    """
    caminho_arquivo = os.path.join(diretorio, nome_arquivo)
    nome_lista = extrair_nome_arquivo(nome_arquivo)
    tickers = ler_tickers_do_arquivo(caminho_arquivo)
    return baixar_dados_historicos(tickers, nome_lista)


def atualizar_todas_listas(diretorio):
    """
    Atualiza os dados históricos para todas as listas de tickers encontradas no diretório.

    Args:
        diretorio (str): O diretório onde os arquivos CSV estão localizados.

    Returns:
        tuple: (True, mensagem) em caso de sucesso, (False, mensagem) em caso de erro.
    """
    arquivos = listar_arquivos(diretorio)
    if not arquivos:
        return False, "Nenhuma lista encontrada para atualizar."

    resultados = []
    for arquivo in arquivos:
        sucesso, mensagem = atualizar_lista(arquivo, diretorio)
        resultados.append(
            f"Lista '{extrair_nome_arquivo(arquivo)}': {'✓' if sucesso else '✗'}"
        )
    return True, "Processo de atualização concluído:\n" + "\n".join(resultados)


def remover_dados_historicos_por_lista(nome_lista):
    """
    Remove os dados históricos de uma lista específica do arquivo Parquet.

    Args:
        nome_lista (str): O nome da lista a ser removida.

    Returns:
        bool: True em caso de sucesso, False em caso de erro.
    """
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")

    if not os.path.exists(caminho_bd):
        return True  # Não há dados para remover

    try:
        df = pd.read_parquet(caminho_bd)
        if "Lista" not in df.columns:
            return True  # Não há dados associados a listas

        df_filtrado = df[df["Lista"] != nome_lista]
        df_filtrado.to_parquet(caminho_bd, index=False)
        return True
    except Exception as e:
        logging.error(
            f"Erro ao remover dados históricos da lista '{nome_lista}': {e}"
        )  # Registra o erro
        st.error(f"Erro ao remover dados históricos da lista '{nome_lista}': {e}")
        return False


# ===============================
# Funções da Interface do Streamlit
# ===============================
def exibir_informacoes_banco_de_dados():
    """
    Exibe informações sobre o banco de dados de cotações (arquivo Parquet).
    """
    st.header("Informações do Banco de Dados de Cotações")
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")

    if os.path.exists(caminho_bd):
        if verificar_parquet(caminho_bd):
            try:
                df_info = pd.read_parquet(caminho_bd)
                st.write(f"Total de registros: {len(df_info):,}")
                st.write("Colunas disponíveis no banco de dados:", df_info.columns.tolist())

                date_cols = [
                    col for col in df_info.columns if "date" in str(col).lower()
                ]
                if date_cols and "Date" not in df_info.columns:
                    df_info.rename(columns={date_cols[0]: "Date"}, inplace=True)

                ticker_cols = [
                    col for col in df_info.columns if "ticker" in str(col).lower()
                ]
                if ticker_cols and "Ticker" not in df_info.columns:
                    df_info.rename(columns={ticker_cols[0]: "Ticker"}, inplace=True)

                lista_cols = [
                    col for col in df_info.columns if "lista" in str(col).lower()
                ]
                if lista_cols and "Lista" not in df_info.columns:
                    df_info.rename(columns={lista_cols[0]: "Lista"}, inplace=True)

                colunas_esperadas = ["Date", "Lista", "Ticker"]
                colunas_faltantes = [
                    col for col in colunas_esperadas if col not in df_info.columns
                ]

                if colunas_faltantes:
                    st.warning(
                        f"As seguintes colunas estão faltando no banco de dados: {', '.join(colunas_faltantes)}"
                    )
                    for col in colunas_faltantes:
                        df_info[col] = "N/A"

                    st.info(
                        "Colunas faltantes foram criadas temporariamente com valores 'N/A' para permitir visualização."
                    )
                    st.info(
                        "Utilize a função 'Atualizar Todas as Listas' para reconstruir o banco de dados corretamente."
                    )

                st.write("Dados por lista:")
                resumo_listas = (
                    df_info.groupby("Lista")["Ticker"].nunique().reset_index()
                )
                resumo_listas.columns = ["Lista", "Quantidade de Tickers"]
                st.dataframe(resumo_listas)

                try:
                    min_data = pd.to_datetime(df_info["Date"]).min().strftime(
                        "%d/%m/%Y"
                    )
                    max_data = pd.to_datetime(df_info["Date"]).max().strftime(
                        "%d/%m/%Y"
                    )
                    st.write(f"Período: {min_data} até {max_data}")
                except:
                    st.warning("Não foi possível determinar o intervalo de datas.")

                tickers_unicos = df_info["Ticker"].nunique()
                st.write(f"Total de tickers únicos: {tickers_unicos}")
            else:
                st.error(
                    "Não foi possível acessar o banco de dados. O arquivo parquet pode estar corrompido."
                )
        else:
            st.error(
                "Não foi possível acessar o banco de dados. O arquivo parquet pode estar corrompido."
            )
    except Exception as e:
        logging.error(f"Erro ao carregar informações do banco de dados: {e}")
        st.error(f"Erro ao carregar informações do banco de dados: {e}")
    else:
        st.info("Banco de dados de cotações ainda não foi criado.")
        if st.button("Criar banco de dados agora"):
            with st.spinner(
                "Atualizando todas as listas para criar o banco de dados..."
            ):
                sucesso, mensagem = atualizar_todas_listas(diretorio)
                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(f"Erro ao criar o banco de dados: {mensagem}")


def exibir_ultimos_registros():
    """
    Exibe os últimos registros atualizados do banco de dados.
    """
    st.header("Últimos Registros Atualizados")
    caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")

    if os.path.exists(caminho_bd):
        if verificar_parquet(caminho_bd):
            try:
                df_ultimos = pd.read_parquet(caminho_bd)
                if "Date" in df_ultimos.columns:
                    try:
                        df_ultimos["Date"] = pd.to_datetime(df_ultimos["Date"])
                        df_ultimos = df_ultimos.sort_values(
                            by="Date", ascending=False
                        )  # Ordena
                    except:
                        st.warning(
                            "Não foi possível ordenar por data. Mostrando os últimos registros na ordem atual."
                        )

                st.write(
                    f"Exibindo os 50 últimos registros do banco de dados (total: {len(df_ultimos):,}):"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if "Lista" in df_ultimos.columns:
                        listas_disponiveis = ["Todas"] + sorted(
                            df_ultimos["Lista"].unique().tolist()
                        )
                        lista_selecionada = st.selectbox(
                            "Filtrar por lista:", listas_disponiveis
                        )

                with col2:
                    if "Ticker" in df_ultimos.columns:
                        tickers_disponiveis = ["Todos"] + sorted(
                            df_ultimos["Ticker"].unique().tolist()
                        )
                        ticker_selecionado = st.selectbox(
                            "Filtrar por ticker:", tickers_disponiveis
                        )

                df_filtrado = df_ultimos.copy()
                if (
                    "Lista" in df_ultimos.columns
                    and lista_selecionada != "Todas"
                ):
                    df_filtrado = df_filtrado[
                        df_filtrado["Lista"] == lista_selecionada
                    ]
                if (
                    "Ticker" in df_ultimos.columns
                    and ticker_selecionado != "Todos"
                ):
                    df_filtrado = df_filtrado[
                        df_filtrado["Ticker"] == ticker_selecionado
                    ]

                st.dataframe(df_filtrado.head(50))

                if not df_filtrado.empty:
                    csv = df_filtrado.head(50).to_csv(index=False).encode(
                        "utf-8"
                    )  # Gera CSV
                    st.download_button(
                        label="Baixar dados visualizados como CSV",
                        data=csv,
                        file_name=f"dados_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )
            else:
                st.error(
                    "Não foi possível acessar o banco de dados. O arquivo parquet pode estar corrompido."
                )
        else:
            st.error(
                "Não foi possível acessar o banco de dados. O arquivo parquet pode estar corrompido."
            )
    except Exception as e:
        logging.error(f"Erro ao carregar dados para visualização: {e}")
        st.error(f"Erro ao carregar dados do banco para visualização: {e}")
    else:
        st.info("Banco de dados de cotações ainda não foi criado.")
        if st.button("Criar banco de dados agora"):
            with st.spinner(
                "Atualizando todas as listas para criar o banco de dados..."
            ):
                sucesso, mensagem = atualizar_todas_listas(diretorio)
                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(f"Erro ao criar o banco de dados: {mensagem}")


def exibir_opcoes_avancadas():
    """
    Exibe opções avançadas para resetar o banco de dados.
    """
    with st.expander("Opções avançadas"):
        caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
        if st.button("Resetar banco de dados de cotações"):
            if os.path.exists(caminho_bd):
                try:
                    os.remove(caminho_bd)
                    st.success("Banco de dados resetado com sucesso!")
                except Exception as e:
                    logging.error(f"Erro ao excluir o banco de dados: {e}")
                    st.error(f"Erro ao excluir o banco de dados: {e}")
            else:
                st.info("Não existe banco de dados para resetar.")


def main():
    """
    Função principal que executa o aplicativo Streamlit.
    """
    configurar_sidebar()
    configurar_pagina()
    diretorio = criar_diretorio()

    # Upload de arquivo
    st.header("Upload e Processamento de Arquivo CSV")
    uploaded_file = st.file_uploader("Selecione um arquivo CSV", type=["csv"])

    if uploaded_file is not None:
        nome_sugerido = extrair_nome_arquivo(uploaded_file.name)
        novo_nome = st.text_input(
            "Digite um nome para o arquivo (sem extensão):", value=nome_sugerido
        )
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
        for arquivo in arquivos:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(arquivo)
            with col2:
                if st.button("Excluir", key=f"del_{arquivo}"):
                    nome_lista = extrair_nome_arquivo(arquivo)
                    os.remove(os.path.join(diretorio, arquivo))
                    if remover_dados_historicos_por_lista(nome_lista):
                        st.success(
                            f"Arquivo '{arquivo}' e seus dados históricos foram excluídos com sucesso!"
                        )
                    else:
                        st.error(
                            f"Arquivo '{arquivo}' foi excluído, mas houve um problema ao remover os dados históricos."
                        )
                    st.rerun()
            with col3:
                if st.button("Atualizar", key=f"upd_{arquivo}"):
                    with st.spinner(f"Atualizando lista '{arquivo}'..."):
                        sucesso, mensagem = atualizar_lista(arquivo, diretorio)
                        if sucesso:
                            st.success(mensagem)
                        else:
                            st.error(mensagem)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Excluir Todos os Arquivos"):
                for arquivo in arquivos:
                    os.remove(os.path.join(diretorio, arquivo))
                caminho_bd = os.path.join("01-dados", "ativos_historicos.parquet")
                if os.path.exists(caminho_bd):
                    try:
                        os.remove(caminho_bd)
                        st.success("Todos os arquivos e o banco de dados histórico foram excluídos!")
                    except Exception as e:
                        logging.error(
                            f"Erro ao excluir o banco de dados: {e}"
                        )  # Registra o erro
                        st.error(
                            f"Arquivos de lista foram excluídos, mas houve um problema ao remover o banco de dados histórico: {e}"
                        )
                else:
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

    exibir_informacoes_banco_de_dados()
    exibir_ultimos_registros()
    exibir_opcoes_avancadas()


if __name__ == "__main__":
    main()
