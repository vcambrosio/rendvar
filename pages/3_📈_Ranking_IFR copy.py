import streamlit as st
import pandas as pd
import os
from datetime import timedelta, datetime
from io import BytesIO
import base64
import random

from PIL import Image

# Configuração
st.set_page_config(page_title="Ranking IFR - Índice LD", layout="wide")

parquet_path = "01-dados/ativos_historicos.parquet"

st.title("🏆 Ranking de Ativos Setup IFR pelo Índice LD Médio")

if not os.path.exists(parquet_path):
    st.error("⚠ Base de dados não encontrada. Atualize a base antes de continuar.")
    st.stop()

# Carregar base
df_base = pd.read_parquet(parquet_path)

# Seleção de lista
listas_disponiveis = sorted(df_base["Lista"].unique().tolist())
lista_selecionada = st.sidebar.selectbox("Selecione a lista", listas_disponiveis)

df_filtrado = df_base[df_base["Lista"] == lista_selecionada]
ativos_disponiveis = sorted(df_filtrado["Ticker"].unique().tolist())

selecionar_todos = st.sidebar.checkbox("Selecionar todos os ativos da lista", value=True)
if selecionar_todos:
    ativos_escolhidos = ativos_disponiveis
else:
    ativos_escolhidos = st.sidebar.multiselect("Escolha os ativos", ativos_disponiveis, default=ativos_disponiveis[:5])

# Parâmetros configuráveis
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parâmetros do Setup")

# Parâmetros de IFR
st.sidebar.markdown("#### Parâmetros de IFR")
periodo_ifr = st.sidebar.slider("Período do IFR", min_value=2, max_value=14, value=2, step=1)
ifr_min = st.sidebar.slider("IFR Mínimo", min_value=5, max_value=30, value=10, step=1)
ifr_max = st.sidebar.slider("IFR Máximo", min_value=ifr_min, max_value=30, value=ifr_min, step=1)

# Parâmetros de Média Móvel
st.sidebar.markdown("#### Parâmetros de Média Móvel")
usar_media = st.sidebar.checkbox("Usar Média Móvel como filtro", value=True)
media_periodos = st.sidebar.slider("Períodos da Média Móvel", min_value=20, max_value=200, value=200, step=10, disabled=not usar_media)

# Filtro de LD Médio
st.sidebar.markdown("#### Filtro de Resultados")
filtro_ld_ativo = st.sidebar.checkbox("Filtrar por LD Médio", value=False)
ld_minimo = st.sidebar.slider(
    "Valor mínimo de LD Médio:", 
    min_value=0.0,
    max_value=10.0,
    value=1.0,
    step=0.1,
    format="%.1f",
    disabled=not filtro_ld_ativo
)

# Parâmetros de Saída
st.sidebar.markdown("#### Parâmetros de Saída")
max_candles_saida = st.sidebar.slider("Máxima de candles para saída", min_value=1, max_value=10, value=2, step=1)
usar_timeout = st.sidebar.checkbox("Usar timeout (saída forçada)", value=True)
max_hold_days = st.sidebar.slider("Dias máximos de permanência", min_value=1, max_value=20, value=5, step=1, disabled=not usar_timeout)
usar_stop = st.sidebar.checkbox("Usar stop loss", value=True)
stop_pct = st.sidebar.slider("Percentual de stop loss", min_value=1, max_value=10, value=5, step=1, disabled=not usar_stop)

# Parâmetros de Capital
st.sidebar.markdown("#### Parâmetros de Capital")
capital_inicial = st.sidebar.number_input("Capital inicial (R$)", min_value=10000, max_value=1000000, value=100000, step=10000)

def gerar_arquivos_exportacao(df_resultados):
    """
    Gera os arquivos ifr_dados.txt, lista_azul.set e ranking_rsi.txt com os dados dos ativos
    e retorna os links de download
    """
    # Criar diretório de saída se não existir
    output_dir = "03-outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Gerar timestamp no formato YYYYMMDDHHMMSS
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Gerar arquivo ifr_dados.txt
    ifr_dados_path = os.path.join(output_dir, "ifr_dados.txt")
    with open(ifr_dados_path, "w") as f:
        for _, row in df_resultados.iterrows():
            f.write(f"{row['Ativo']};{int(row['Melhor IFR'])}\n")
    
    # Gerar arquivo lista_azul.set com prefixo de timestamp
    lista_azul_filename = f"{timestamp}-lista_azul.set"
    lista_azul_path = os.path.join(output_dir, lista_azul_filename)
    with open(lista_azul_path, "w") as f:
        # Primeira linha: número aleatório de 1 a 1000
        f.write(f"{random.randint(1, 1000)}\n")
        # Linhas seguintes: lista de ativos
        for _, row in df_resultados.iterrows():
            f.write(f"{row['Ativo']}\n")
    
    # Gerar arquivo ranking_rsi.txt
    ranking_rsi_path = os.path.join(output_dir, "ranking_rsi.txt")
    with open(ranking_rsi_path, "w") as f:
        for _, row in df_resultados.iterrows():
            # Formato: ATIVO;IFR_2ANOS;LD_MEDIO
            # Usar vírgula como separador decimal para o LD Médio
            ld_formatado = f"{row['LD Médio']:.2f}".replace('.', ',')
            f.write(f"{row['Ativo']};{int(row['IFR em 2 anos'])};{ld_formatado}\n")
    
    # Criar links de download para os arquivos
    ifr_dados_link = criar_link_download(ifr_dados_path, "ifr_dados.txt")
    lista_azul_link = criar_link_download(lista_azul_path, lista_azul_filename)
    ranking_rsi_link = criar_link_download(ranking_rsi_path, "ranking_rsi.txt")
    
    return ifr_dados_path, lista_azul_path, ranking_rsi_path, ifr_dados_link, lista_azul_link, ranking_rsi_link

def criar_link_download(file_path, filename):
    """
    Cria um link de download para um arquivo
    """
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    return f'<a href="data:text/plain;base64,{b64}" download="{filename}">📥 Baixar {filename}</a>'

# === Função de Backtest Detalhado (retorna LD, lucro %, drawdown % e número de trades) ===
def backtest_ativo(ativo, df_filtrado, data_inicial, data_final, 
                   periodo_ifr, ifr_min, ifr_max, usar_media, media_periodos,
                   max_candles_saida, usar_timeout, max_hold_days,
                   usar_stop, stop_pct, capital_inicial):
    
    resultados = []
    melhor_ld = -float('inf')
    melhor_ifr = None
    melhor_lucro = 0
    melhor_dd = 0
    melhor_trades = 0
    
    # Criar intervalo de IFR para teste
    intervalo_ifr = range(ifr_min, ifr_max + 1)
    
    for ifr_entrada in intervalo_ifr:
        df = df_filtrado[df_filtrado["Ticker"] == ativo].copy()
        if df.empty:
            continue

        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)

        extra_ano = 365
        buffer_dias = max(media_periodos if usar_media else periodo_ifr, 10, extra_ano)
        data_inicial_expandida = pd.to_datetime(data_inicial) - timedelta(days=buffer_dias)
        df = df[(df["Date"] >= data_inicial_expandida) & (df["Date"] <= pd.to_datetime(data_final))]
        
        if df.empty:
            continue
            
        df.sort_values("Date", inplace=True)
        df.set_index("Date", inplace=True)
        
        # IFR
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(com=periodo_ifr - 1, min_periods=periodo_ifr).mean()
        avg_loss = loss.ewm(com=periodo_ifr - 1, min_periods=periodo_ifr).mean()
        rs = avg_gain / avg_loss
        df["IFR"] = 100 - (100 / (1 + rs))
        
        if usar_media:
            df["Media"] = df["Close"].rolling(media_periodos).mean()
            df["compra"] = (df["IFR"] < ifr_entrada) & (df["Close"] > df["Media"])
        else:
            df["compra"] = df["IFR"] < ifr_entrada
        
        df = df[df.index >= pd.to_datetime(data_inicial)]
        
        if len(df) <= max_candles_saida:
            continue
            
        posicao = False
        preco_entrada = 0
        data_entrada = None
        trades = []
        
        for i in range(max_candles_saida, len(df)):
            hoje = df.iloc[i]
            
            if not posicao and df.iloc[i]["compra"]:
                preco_entrada = hoje["Close"]
                quantidade = int((capital_inicial // preco_entrada) // 100) * 100
                if quantidade == 0:
                    continue
                preco_stop = preco_entrada * (1 - stop_pct / 100) if stop_pct else None
                data_entrada = df.index[i]
                posicao = True
                dias_hold = 0
                continue
            
            if posicao:
                dias_hold += 1
                preco_abertura = hoje["Open"]
                preco_fechamento = hoje["Close"]
                preco_minimo = hoje["Low"]
                
                sair = False
                preco_saida = None
                motivo = ""
                
                janela_max = df["High"].iloc[i - max_candles_saida:i + 1]
                max_anteriores = janela_max.iloc[:-1].max()
                max_total = janela_max.max()
                
                if hoje["High"] >= max_anteriores:
                    sair = True
                    preco_saida = max_total
                    motivo = f"Saída na máxima de {max_candles_saida} candles"
                elif preco_abertura > max_anteriores:
                    sair = True
                    preco_saida = preco_abertura
                    motivo = "Gap de Alta"
                elif preco_fechamento > max_anteriores:
                    sair = True
                    preco_saida = preco_fechamento
                    motivo = "Breakout"
                elif usar_timeout and dias_hold >= max_hold_days:
                    sair = True
                    preco_saida = preco_abertura
                    motivo = "Saida forçada após x candles"
                elif usar_stop and preco_minimo <= preco_stop:
                    sair = True
                    preco_saida = min(preco_abertura, preco_stop)
                    motivo = "Stop Loss"
                
                if sair:
                    lucro = (preco_saida - preco_entrada) * quantidade
                    trades.append(lucro)
                    posicao = False
        
        if trades:
            capital = [capital_inicial]
            for lucro in trades:
                capital.append(capital[-1] + lucro)
            resultado_perc = (capital[-1] - capital_inicial) / capital_inicial * 100
            dd = max([max(capital[:i+1]) - v for i, v in enumerate(capital)])
            dd_perc = dd / max(capital) * 100 if max(capital) != 0 else 0
            indice_ld = resultado_perc / dd_perc if dd_perc != 0 else 0
            
            # Verificar se este IFR é melhor que o anterior
            if indice_ld > melhor_ld:
                melhor_ld = indice_ld
                melhor_ifr = ifr_entrada
                melhor_lucro = resultado_perc
                melhor_dd = dd_perc
                melhor_trades = len(trades)
                
            resultados.append({
                'ld': indice_ld,
                'lucro_perc': resultado_perc,
                'dd_perc': dd_perc,
                'num_trades': len(trades),
                'ifr': ifr_entrada
            })
    
    if resultados:
        # Retorna o melhor resultado (maior LD) e o melhor valor de IFR
        melhor = max(resultados, key=lambda x: x['ld'])
        return melhor['ld'], melhor['lucro_perc'], melhor['dd_perc'], melhor['num_trades'], melhor_ifr
    else:
        return 0, 0, 0, 0, None

# === Execução Ranking ===
if st.button("🚀 Calcular Ranking"):
    resultados = []
    ativos_excluidos = []
    progress_bar = st.progress(0)
    total = len(ativos_escolhidos)

    for idx, ativo in enumerate(ativos_escolhidos):
        df_atv = df_filtrado[df_filtrado["Ticker"] == ativo]
        if df_atv.empty:
            ativos_excluidos.append({"Ativo": ativo, "Motivo": "Sem dados disponíveis"})
            progress_bar.progress((idx + 1) / total)
            continue

        data_final = pd.to_datetime(df_atv["Date"]).max()

        # Calcular para cada período (retorna LD, Lucro%, DD%, Num_Trades, Melhor IFR)
        ld_10a, lucro_10a, dd_10a, trades_10a, ifr_10a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*10), data_final,
                                                               periodo_ifr, ifr_min, ifr_max, usar_media, media_periodos, 
                                                               max_candles_saida, usar_timeout, max_hold_days, 
                                                               usar_stop, stop_pct, capital_inicial)
        ld_5a, lucro_5a, dd_5a, trades_5a, ifr_5a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*5), data_final,
                                                           periodo_ifr, ifr_min, ifr_max, usar_media, media_periodos, 
                                                           max_candles_saida, usar_timeout, max_hold_days, 
                                                           usar_stop, stop_pct, capital_inicial)
        ld_3a, lucro_3a, dd_3a, trades_3a, ifr_3a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*3), data_final,
                                                           periodo_ifr, ifr_min, ifr_max, usar_media, media_periodos, 
                                                           max_candles_saida, usar_timeout, max_hold_days, 
                                                           usar_stop, stop_pct, capital_inicial)
        ld_2a, lucro_2a, dd_2a, trades_2a, ifr_2a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*2), data_final,
                                                           periodo_ifr, ifr_min, ifr_max, usar_media, media_periodos, 
                                                           max_candles_saida, usar_timeout, max_hold_days, 
                                                           usar_stop, stop_pct, capital_inicial)
        ld_1a, lucro_1a, dd_1a, trades_1a, ifr_1a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*1), data_final,
                                                           periodo_ifr, ifr_min, ifr_max, usar_media, media_periodos, 
                                                           max_candles_saida, usar_timeout, max_hold_days, 
                                                           usar_stop, stop_pct, capital_inicial)

        # Verificar se há dados problemáticos
        dados_problematicos = False
        motivo_exclusao = ""

        # Verificar trades - excluir se houver zero trades em qualquer período
        if trades_10a <= 0 or trades_5a <= 0 or trades_3a <= 0 or trades_2a <= 0 or trades_1a <= 0:
            dados_problematicos = True
            motivo_exclusao = "Sem trades em pelo menos um período"
        
        # Verificar valores negativos ou nulos em dados críticos
        if dd_10a < 0 or dd_5a < 0 or dd_3a < 0 or dd_2a < 0 or dd_1a < 0:
            dados_problematicos = True
            motivo_exclusao = "Drawdown negativo detectado"
            
        # Verificar lucro negativo em todos os períodos
        if lucro_10a <= 0 and lucro_5a <= 0 and lucro_3a <= 0 and lucro_2a <= 0 and lucro_1a <= 0:
            dados_problematicos = True
            motivo_exclusao = "Lucro negativo ou zero em todos os períodos"
        
        # Se encontrou problemas, adiciona à lista de excluídos e pula
        if dados_problematicos:
            ativos_excluidos.append({"Ativo": ativo, "Motivo": motivo_exclusao})
            progress_bar.progress((idx + 1) / total)
            continue

        # Calcular Lucro Médio: média das razões (lucro/anos)
        lucros_anualizados = []
        if lucro_10a != 0: lucros_anualizados.append(lucro_10a / 10)
        if lucro_5a != 0: lucros_anualizados.append(lucro_5a / 5)
        if lucro_3a != 0: lucros_anualizados.append(lucro_3a / 3)
        if lucro_2a != 0: lucros_anualizados.append(lucro_2a / 2)
        if lucro_1a != 0: lucros_anualizados.append(lucro_1a / 1)
        
        lucro_medio = sum(lucros_anualizados) / len(lucros_anualizados) if lucros_anualizados else 0

        # Calcular Drawdown Médio: média das razões (drawdown/anos)
        dds_anualizados = []
        if dd_10a != 0: dds_anualizados.append(dd_10a / 10)
        if dd_5a != 0: dds_anualizados.append(dd_5a / 5)
        if dd_3a != 0: dds_anualizados.append(dd_3a / 3)
        if dd_2a != 0: dds_anualizados.append(dd_2a / 2)
        if dd_1a != 0: dds_anualizados.append(dd_1a / 1)
        
        dd_medio = sum(dds_anualizados) / len(dds_anualizados) if dds_anualizados else 0

        # Calcular Trades Médio: média das razões (trades/anos)
        trades_anualizados = []
        if trades_10a != 0: trades_anualizados.append(trades_10a / 10)
        if trades_5a != 0: trades_anualizados.append(trades_5a / 5)
        if trades_3a != 0: trades_anualizados.append(trades_3a / 3)
        if trades_2a != 0: trades_anualizados.append(trades_2a / 2)
        if trades_1a != 0: trades_anualizados.append(trades_1a / 1)
        
        trades_medio = sum(trades_anualizados) / len(trades_anualizados) if trades_anualizados else 0

        # Calcular LD Médio: razão entre lucro médio e drawdown médio
        ld_medio = lucro_medio / dd_medio if dd_medio != 0 else 0

        resultados.append({
            "Ativo": ativo,
            "Numero de trades em 10 anos": trades_10a,
            "Lucro em 10 anos": lucro_10a,
            "Drawdown em 10 anos": dd_10a,
            "IFR em 10 anos": ifr_10a,
            "Numero de trades em 5 anos": trades_5a,
            "Lucro em 5 anos": lucro_5a,
            "Drawdown em 5 anos": dd_5a,
            "IFR em 5 anos": ifr_5a,
            "Numero de trades em 3 anos": trades_3a,
            "Lucro em 3 anos": lucro_3a,
            "Drawdown em 3 anos": dd_3a,
            "IFR em 3 anos": ifr_3a,
            "Numero de trades em 2 anos": trades_2a,
            "Lucro em 2 anos": lucro_2a,
            "Drawdown em 2 anos": dd_2a,
            "IFR em 2 anos": ifr_2a,
            "Numero de trades em 1 ano": trades_1a,
            "Lucro em 1 ano": lucro_1a,
            "Drawdown em 1 ano": dd_1a,
            "IFR em 1 ano": ifr_1a,
            "Trades medio": trades_medio,
            "Lucro Médio": lucro_medio,
            "DD Médio": dd_medio,
            "LD Médio": ld_medio,
            "Melhor IFR": ifr_1a  # Usando o IFR mais recente como referência
        })

        progress_bar.progress((idx + 1) / total)

    df_resultados = pd.DataFrame(resultados)
    
    # Verificar se há resultados válidos
    if df_resultados.empty:
        st.warning("⚠️ Nenhum ativo válido encontrado com os parâmetros selecionados.")
    else:
        # Ordenar por LD Médio (decrescente)
        df_resultados = df_resultados.sort_values(by="LD Médio", ascending=False)
        
        # Aplicar filtro de LD Médio se estiver ativo
        if filtro_ld_ativo:
            df_display = df_resultados[df_resultados["LD Médio"] >= ld_minimo]
            # Mostrar quantos ativos foram filtrados
            st.info(f"Exibindo {len(df_display)} de {len(df_resultados)} ativos com LD Médio >= {ld_minimo:.1f}")
        else:
            df_display = df_resultados

        st.subheader("📊 Ranking Final (por LD Médio)")
        
        # Mostrar apenas as colunas principais no display
        colunas_display = ["Ativo", "LD Médio", "Lucro Médio", "DD Médio", "Trades medio", "Melhor IFR"]
        
        st.dataframe(
            df_display[colunas_display].style.format({
                "LD Médio": "{:.2f}",
                "Lucro Médio": "{:.2f}%",
                "DD Médio": "{:.2f}%",
                "Trades medio": "{:.1f}",
                "Melhor IFR": "{:.0f}"
            })
        )

        # Mostrar detalhes completos na tabela principal
        st.subheader("📋 Tabela Detalhada")
        
        # Definir as colunas na ordem solicitada
        colunas_detalhadas = [
            "Ativo", 
            "Numero de trades em 10 anos", "Lucro em 10 anos", "Drawdown em 10 anos", "IFR em 10 anos",
            "Numero de trades em 5 anos", "Lucro em 5 anos", "Drawdown em 5 anos", "IFR em 5 anos",
            "Numero de trades em 3 anos", "Lucro em 3 anos", "Drawdown em 3 anos", "IFR em 3 anos",
            "Numero de trades em 2 anos", "Lucro em 2 anos", "Drawdown em 2 anos", "IFR em 2 anos",
            "Numero de trades em 1 ano", "Lucro em 1 ano", "Drawdown em 1 ano", "IFR em 1 ano",
            "Trades medio", "Lucro Médio", "DD Médio", "LD Médio", "Melhor IFR"
        ]
        
        st.dataframe(
            df_display[colunas_detalhadas].style.format({
                "Numero de trades em 10 anos": "{:.0f}",
                "Lucro em 10 anos": "{:.2f}%",
                "Drawdown em 10 anos": "{:.2f}%",
                "IFR em 10 anos": "{:.0f}",
                "Numero de trades em 5 anos": "{:.0f}",
                "Lucro em 5 anos": "{:.2f}%",
                "Drawdown em 5 anos": "{:.2f}%",
                "IFR em 5 anos": "{:.0f}",
                "Numero de trades em 3 anos": "{:.0f}",
                "Lucro em 3 anos": "{:.2f}%",
                "Drawdown em 3 anos": "{:.2f}%",
                "IFR em 3 anos": "{:.0f}",
                "Numero de trades em 2 anos": "{:.0f}",
                "Lucro em 2 anos": "{:.2f}%",
                "Drawdown em 2 anos": "{:.2f}%",
                "IFR em 2 anos": "{:.0f}",
                "Numero de trades em 1 ano": "{:.0f}",
                "Lucro em 1 ano": "{:.2f}%",
                "Drawdown em 1 ano": "{:.2f}%",
                "IFR em 1 ano": "{:.0f}",
                "Trades medio": "{:.1f}",
                "Lucro Médio": "{:.2f}%",
                "DD Médio": "{:.2f}%",
                "LD Médio": "{:.2f}",
                "Melhor IFR": "{:.0f}"
            })
        )
        
        # Gerar arquivos automaticamente após o cálculo
        ifr_dados_path, lista_azul_path, ranking_rsi_path, ifr_dados_link, lista_azul_link, ranking_rsi_link = gerar_arquivos_exportacao(df_display)
        
        # Exibir links de download
        st.subheader("📥 Arquivos de Exportação")
        st.markdown("Os arquivos foram gerados automaticamente e estão disponíveis para download:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(ifr_dados_link, unsafe_allow_html=True)
        with col2:
            st.markdown(lista_azul_link, unsafe_allow_html=True)
        with col3:
            st.markdown(ranking_rsi_link, unsafe_allow_html=True)
        
    # Exibir ativos excluídos do ranking
    if ativos_excluidos:
        st.subheader("⚠️ Ativos Excluídos do Ranking")
        st.markdown("Os seguintes ativos foram excluídos por apresentarem dados problemáticos:")
        
        df_excluidos = pd.DataFrame(ativos_excluidos)
        st.dataframe(df_excluidos)

    # Exportar para Excel
    output = BytesIO()
    df_resultados.to_excel(output, index=False, engine="xlsxwriter")
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="ranking_ld_corrigido.xlsx">📥 Baixar Ranking em Excel</a>'
    st.markdown(href, unsafe_allow_html=True)
    
    st.info(f"""
    **📋 Metodologia do LD Médio:**
    
    **Cálculos:**
    - **Trades Médio**: Média das razões (Número de trades de N anos ÷ N anos)
    - **Lucro Médio**: Média das razões (Lucro de N anos ÷ N anos)
    - **DD Médio**: Média das razões (Drawdown de N anos ÷ N anos)  
    - **LD Médio**: Lucro Médio ÷ DD Médio
    
    **⚙️ Parâmetros do Setup:**
    - **Períodos analisados**: 10, 5, 3, 2 e 1 anos
    - **IFR utilizado**: Período de {periodo_ifr}, testando entradas de {ifr_min} a {ifr_max}
    - **Média móvel**: {media_periodos if usar_media else "Não utilizada"} períodos {f"(filtro de tendência)" if usar_media else ""}
    - **Condição de entrada**: IFR < valor_testado {f"E preço > média {media_periodos}" if usar_media else ""}
    - **Saída**: Máxima de {max_candles_saida} candles anteriores
    - **Stop Loss**: {f"{stop_pct}% (ativado)" if usar_stop else "Desativado"}
    - **Timeout**: {f"{max_hold_days} dias (ativado)" if usar_timeout else "Desativado"}
    - **Capital inicial**: R$ {capital_inicial:,}
    - **Lote mínimo**: 100 ações
    
    **🎯 Lógica de entrada**: Compra quando IFR indica sobrevenda {f"mas o ativo está em tendência de alta (acima da média {media_periodos})" if usar_media else ""}
    
    **📈 Lógica de saída**: Vende quando o preço supera a máxima dos {max_candles_saida} candles anteriores (breakout){f", ou por stop loss" if usar_stop else ""}{f"/timeout" if usar_timeout else ""}
    
    **📄 Arquivos gerados:**
    - **ifr_dados.txt**: Lista de ativos com seus melhores valores de IFR
    - **lista_azul.set**: Arquivo de configuração com timestamp e lista de ativos
    - **ranking_rsi.txt**: Ranking com ativo, IFR de 2 anos e LD Médio (formato: ATIVO;IFR;LD)
    
    
else:
    st.info("Clique em 'Calcular Ranking' para gerar o ranking de índice LD médio.")
    