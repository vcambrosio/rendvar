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
    st.error("❌ Base de dados não encontrada. Atualize a base antes de continuar.")
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

# === Função de Backtest Detalhado (mesma lógica do código anterior) ===
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
            resultados.append(indice_ld)
    
    if resultados:
        return max(resultados)  # Melhor IFR para esse período
    else:
        return 0

# === Execução Ranking ===
if st.button("🏁 Calcular Ranking"):
    resultados = []
    progress_bar = st.progress(0)
    total = len(ativos_escolhidos)

    for idx, ativo in enumerate(ativos_escolhidos):
        df_atv = df_filtrado[df_filtrado["Ticker"] == ativo]
        if df_atv.empty:
            continue

        data_final = pd.to_datetime(df_atv["Date"]).max()

        ld_10a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*10), data_final,
                                2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)
        ld_5a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*5), data_final,
                               2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)
        ld_3a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*3), data_final,
                               2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)
        ld_2a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*2), data_final,
                               2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)
        ld_1a = backtest_ativo(ativo, df_filtrado, data_final - timedelta(days=365*1), data_final,
                               2, range(5, 30), True, 200, 2, True, 5, True, 5, 100000)

        ld_medio = (ld_10a + ld_5a + ld_3a + ld_2a + ld_1a) / 5

        resultados.append({
            "Ativo": ativo,
            "LD 10 anos": ld_10a,
            "LD 5 anos": ld_5a,
            "LD 3 anos": ld_3a,
            "LD 2 anos": ld_2a,
            "LD 1 ano": ld_1a,
            "LD Médio": ld_medio
        })

        progress_bar.progress((idx + 1) / total)

    df_resultados = pd.DataFrame(resultados)
    df_resultados = df_resultados.sort_values(by="LD Médio", ascending=False)

    st.subheader("📊 Ranking Final (por LD Médio)")
    st.dataframe(
        df_resultados.style.format({
            "LD 10 anos": "{:.2f}",
            "LD 5 anos": "{:.2f}",
            "LD 3 anos": "{:.2f}",
            "LD 2 anos": "{:.2f}",
            "LD 1 ano": "{:.2f}",
            "LD Médio": "{:.2f}"
        })
    )    

    # Exportar para Excel
    output = BytesIO()
    df_resultados.to_excel(output, index=False, engine="xlsxwriter")
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="ranking_ld.xlsx">📥 Baixar Ranking em Excel</a>'
    st.markdown(href, unsafe_allow_html=True)
else:
    st.info("Clique em 'Calcular Ranking' para gerar o ranking de Índice LD médio.")
