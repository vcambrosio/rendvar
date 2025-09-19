import streamlit as st
import pandas as pd
import os
from datetime import timedelta
from io import BytesIO
import base64

from PIL import Image

# Configuração
st.set_page_config(page_title="Ranking IFR - Índice LD", layout="wide")

parquet_path = "01-dados/ativos_historicos.parquet"

st.title("🏆 Ranking de Ativos pelo Índice LD Médio (Backtest Detalhado)")

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

# === Função de Backtest Detalhado (retorna LD, lucro %, drawdown % e número de trades) ===
def backtest_ativo(ativo, df_filtrado, data_inicial, data_final, 
                   periodo_ifr, intervalo_ifr, usar_media, media_periodos,
                   max_candles_saida, usar_timeout, max_hold_days,
                   usar_stop, stop_pct, capital_inicial):
    
    resultados = []
    
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
            resultados.append({
                'ld': indice_ld,
                'lucro_perc': resultado_perc,
                'dd_perc': dd_perc,
                'num_trades': len(trades)
            })
    
    if resultados:
        # Retorna o melhor resultado (maior LD)
        melhor = max(resultados, key=lambda x: x['ld'])
        return melhor['ld'], melhor['lucro_perc'], melhor['dd_perc'], melhor['num_trades']
    else:
        return 0, 0, 0, 0

# === Execução Ranking ===
if st.button("🚀 Calcular Ranking"):
    resultados = []
    progress_bar = st.progress(0)
    total = len(ativos_escolhidos)

    for idx, ativo in enumerate(ativos_escolhidos):
        df_atv = df_filtrado[df_filtrado["Ticker"] == ativo]
        if df_atv.empty:
            continue

        data_final = pd.to_datetime(df_atv["Date"]).max()

        # Calcular para cada período (retorna LD, Lucro%, DD%, Num_Trades)
        ld_10a, lucro_10a, dd_10a, trades_10a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*10), data_final,
                                                               2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)
        ld_5a, lucro_5a, dd_5a, trades_5a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*5), data_final,
                                                           2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)
        ld_3a, lucro_3a, dd_3a, trades_3a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*3), data_final,
                                                           2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)
        ld_2a, lucro_2a, dd_2a, trades_2a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*2), data_final,
                                                           2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)
        ld_1a, lucro_1a, dd_1a, trades_1a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*1), data_final,
                                                           2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)

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
            "Numero de trades em 5 anos": trades_5a,
            "Lucro em 5 anos": lucro_5a,
            "Drawdown em 5 anos": dd_5a,
            "Numero de trades em 3 anos": trades_3a,
            "Lucro em 3 anos": lucro_3a,
            "Drawdown em 3 anos": dd_3a,
            "Numero de trades em 2 anos": trades_2a,
            "Lucro em 2 anos": lucro_2a,
            "Drawdown em 2 anos": dd_2a,
            "Numero de trades em 1 ano": trades_1a,
            "Lucro em 1 ano": lucro_1a,
            "Drawdown em 1 ano": dd_1a,
            "Trades medio": trades_medio,
            "Lucro Médio": lucro_medio,
            "DD Médio": dd_medio,
            "LD Médio": ld_medio
        })

        progress_bar.progress((idx + 1) / total)

    df_resultados = pd.DataFrame(resultados)
    # Ordenar por LD Médio (decrescente)
    df_resultados = df_resultados.sort_values(by="LD Médio", ascending=False)

    st.subheader("📊 Ranking Final (por LD Médio)")
    
    # Mostrar apenas as colunas principais no display
    colunas_display = ["Ativo", "LD Médio", "Lucro Médio", "DD Médio", "Trades medio"]
    
    st.dataframe(
        df_resultados[colunas_display].style.format({
            "LD Médio": "{:.2f}",
            "Lucro Médio": "{:.2f}%",
            "DD Médio": "{:.2f}%",
            "Trades medio": "{:.1f}"
        })
    )

    # Mostrar detalhes completos na tabela principal
    st.subheader("📋 Tabela Detalhada")
    
    # Definir as colunas na ordem solicitada
    colunas_detalhadas = [
        "Ativo", 
        "Numero de trades em 10 anos", "Lucro em 10 anos", "Drawdown em 10 anos",
        "Numero de trades em 5 anos", "Lucro em 5 anos", "Drawdown em 5 anos", 
        "Numero de trades em 3 anos", "Lucro em 3 anos", "Drawdown em 3 anos",
        "Numero de trades em 2 anos", "Lucro em 2 anos", "Drawdown em 2 anos",
        "Numero de trades em 1 ano", "Lucro em 1 ano", "Drawdown em 1 ano",
        "Trades medio", "Lucro Médio", "DD Médio", "LD Médio"
    ]
    
    st.dataframe(
        df_resultados[colunas_detalhadas].style.format({
            "Numero de trades em 10 anos": "{:.0f}",
            "Lucro em 10 anos": "{:.2f}%",
            "Drawdown em 10 anos": "{:.2f}%",
            "Numero de trades em 5 anos": "{:.0f}",
            "Lucro em 5 anos": "{:.2f}%",
            "Drawdown em 5 anos": "{:.2f}%",
            "Numero de trades em 3 anos": "{:.0f}",
            "Lucro em 3 anos": "{:.2f}%",
            "Drawdown em 3 anos": "{:.2f}%",
            "Numero de trades em 2 anos": "{:.0f}",
            "Lucro em 2 anos": "{:.2f}%",
            "Drawdown em 2 anos": "{:.2f}%",
            "Numero de trades em 1 ano": "{:.0f}",
            "Lucro em 1 ano": "{:.2f}%",
            "Drawdown em 1 ano": "{:.2f}%",
            "Trades medio": "{:.1f}",
            "Lucro Médio": "{:.2f}%",
            "DD Médio": "{:.2f}%",
            "LD Médio": "{:.2f}"
        })
    )

    # Exportar para Excel
    output = BytesIO()
    df_resultados.to_excel(output, index=False, engine="xlsxwriter")
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="ranking_ld_corrigido.xlsx">📥 Baixar Ranking em Excel</a>'
    st.markdown(href, unsafe_allow_html=True)
    
    st.info("""
    **📋 Metodologia do LD Médio:**
    
    **Cálculos:**
    - **Trades Médio**: Média das razões (Número de trades de N anos ÷ N anos)
    - **Lucro Médio**: Média das razões (Lucro de N anos ÷ N anos)
    - **DD Médio**: Média das razões (Drawdown de N anos ÷ N anos)  
    - **LD Médio**: Lucro Médio ÷ DD Médio
    
    **⚙️ Parâmetros do Setup:**
    - **Períodos analisados**: 10, 5, 3, 2 e 1 anos
    - **IFR utilizado**: Período de 2, testando entradas de 5 a 29
    - **Média móvel**: 200 períodos (filtro de tendência)
    - **Condição de entrada**: IFR < valor_testado E preço > média 200
    - **Saída**: Máxima de 2 candles anteriores
    - **Stop Loss**: 5% (ativado)
    - **Timeout**: 5 dias (ativado)
    - **Capital inicial**: R$ 100.000
    - **Lote mínimo**: 100 ações
    
    **🎯 Lógica de entrada**: Compra quando IFR indica sobrevenda mas o ativo está em tendência de alta (acima da média 200)
    
    **📈 Lógica de saída**: Vende quando o preço supera a máxima dos 2 candles anteriores (breakout), ou por stop loss/timeout
    """)
    
    
else:
    st.info("Clique em 'Calcular Ranking' para gerar o ranking de Índice LD médio.")