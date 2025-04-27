import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from datetime import timedelta
from PIL import Image

# Caminho dos dados
parquet_path = "01-dados/ativos_historicos.parquet"

st.title("📈 Backtest - Setup Máximas/Mínimas - Ativo único")

# Verifica se a base existe
if not os.path.exists(parquet_path):
    st.error("❌ Base de dados não encontrada. Atualize a base antes de continuar.")
    st.stop()

# Carrega dados
df_base = pd.read_parquet(parquet_path)

# === INTERFACE STREAMLIT ===
st.sidebar.header("📋 Filtros")
# Primeiro selecionar a lista
listas_disponiveis = sorted(df_base["Lista"].unique().tolist())
lista_selecionada = st.sidebar.selectbox("Selecione a lista", listas_disponiveis)

# Filtrar ativos pela lista selecionada
df_filtrado = df_base[df_base["Lista"] == lista_selecionada]
ativos_disponiveis = sorted(df_filtrado["Ticker"].unique().tolist())

# Define datas padrão com base no banco
data_final_padrao = pd.to_datetime(df_filtrado["Date"].max()).normalize()
data_inicial_padrao = data_final_padrao - timedelta(days=730)

st.sidebar.header("🎯 Parâmetros do Ativo")
ativo_escolhido = st.sidebar.selectbox("Escolha o ativo", ativos_disponiveis)
data_inicial = st.sidebar.date_input("Data inicial", value=data_inicial_padrao)
data_final = st.sidebar.date_input("Data final", value=data_final_padrao)

st.sidebar.header("💰 Capital Inicial")
capital_inicial = st.sidebar.number_input("Capital disponível (R$)", value=10000.0, step=100.0)

st.sidebar.header("📥 Critérios de Entrada")
candles_minima = st.sidebar.number_input("Mínima dos últimos X candles", min_value=1, max_value=30, value=10)

st.sidebar.header("📊 Filtro Keltner")
usar_keltner = st.sidebar.checkbox("Usar filtro de Bandas de Keltner", value=True)
if usar_keltner:
    periodo_keltner = st.sidebar.number_input("Período da EMA para Keltner", min_value=2, max_value=50, value=20)
    desvio_keltner = st.sidebar.number_input("Desvio para bandas Keltner", min_value=0.01, max_value=5.0, value=2.0, step=0.01, format="%.2f")

st.sidebar.header("📤 Critérios de Saída")
candles_maxima = st.sidebar.number_input("Máxima dos últimos X candles para saída", min_value=1, max_value=30, value=2)
timeout_candles = st.sidebar.number_input("Forçar saída após X candles", min_value=1, max_value=50, value=10)

st.sidebar.header("⚠️ Stop Loss")
usar_stop = st.sidebar.checkbox("Usar Stop Loss?")
if usar_stop:
    stop_pct = st.sidebar.number_input("Stop Loss (% abaixo do preço de entrada)", min_value=0.1, max_value=50.0, value=5.0)
else:
    stop_pct = None


with st.sidebar:
    # Cria duas colunas (ajuste a proporção conforme necessário)
    st.markdown("---")  # Linha separadora abaixo
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


# === FUNÇÃO PARA CALCULAR BANDAS DE KELTNER ===
def calcular_keltner(df, periodo=20, desvio=2.0):
    df_keltner = df.copy()
    
    # Média Móvel Exponencial (EMA) usando o fechamento
    df_keltner['EMA'] = df_keltner['Close'].ewm(span=periodo, adjust=False).mean()
    
    # Bandas de Keltner com desvio fixo
    df_keltner['Keltner_Superior'] = df_keltner['EMA'] + (df_keltner['EMA'] * desvio / 100)
    df_keltner['Keltner_Inferior'] = df_keltner['EMA'] - (df_keltner['EMA'] * desvio / 100)
    
    return df_keltner

# === BACKTEST ===
if st.button("▶️ Executar Backtest"):
    df = df_filtrado[df_filtrado["Ticker"] == ativo_escolhido].copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)

    # Expandir período para cálculos
    buffer_dias = max(candles_minima, candles_maxima, periodo_keltner if usar_keltner else 0, 50)
    data_inicial_expandida = pd.to_datetime(data_inicial) - timedelta(days=buffer_dias*2)
    df = df[(df["Date"] >= data_inicial_expandida) & (df["Date"] <= pd.to_datetime(data_final))]
    df.sort_values("Date", inplace=True)
    df.set_index("Date", inplace=True)
    
    # Calcular Keltner se necessário
    if usar_keltner:
        df = calcular_keltner(df, periodo=periodo_keltner, desvio=desvio_keltner)
    
    # Filtrando para o período solicitado
    df = df[df.index >= pd.to_datetime(data_inicial)]
    
    # Iniciar o backtest
    posicao = False
    preco_entrada = 0
    data_entrada = None
    trades = []
    dias_hold = 0
    
    for i in range(candles_minima, len(df)):
        hoje = df.iloc[i]
        
        # Verificação para entrada
        if not posicao:
            # Verifica mínima dos últimos X candles
            janela_min = df["Low"].iloc[i-candles_minima:i]
            min_anteriores = janela_min.min()
            
            # Condição de entrada: preço está na mínima dos últimos X candles
            if hoje["Low"] <= min_anteriores:
                # Se usando Keltner, verifica se fechamento está acima da banda superior
                if (not usar_keltner) or (hoje["Close"] > hoje["Keltner_Superior"]):
                    preco_entrada = hoje["Close"]
                    quantidade = int((capital_inicial // preco_entrada) // 100) * 100
                    if quantidade == 0:
                        continue
                    preco_stop = preco_entrada * (1 - stop_pct / 100) if stop_pct else None
                    data_entrada = df.index[i]
                    posicao = True
                    dias_hold = 0
                    continue
        
        # Gerenciamento da posição
        if posicao:
            dias_hold += 1
            preco_abertura = hoje["Open"]
            preco_fechamento = hoje["Close"]
            preco_minimo = hoje["Low"]
            
            sair = False
            preco_saida = None
            motivo = ""
            
            # Verificação para saída na máxima
            janela_max = df["High"].iloc[i-candles_maxima:i+1]
            max_anteriores = janela_max.iloc[:-1].max()
            
            if hoje["High"] >= max_anteriores:
                sair = True
                preco_saida = max_anteriores  # Saída na máxima dos últimos X candles
                motivo = f"Saída na máxima de {candles_maxima} candles"
            elif dias_hold >= timeout_candles:
                sair = True
                preco_saida = preco_fechamento
                motivo = f"Timeout após {timeout_candles} candles"
            elif usar_stop and preco_minimo <= preco_stop:
                sair = True
                preco_saida = min(preco_abertura, preco_stop)
                motivo = "Stop Loss"
            
            if sair:
                lucro = (preco_saida - preco_entrada) * quantidade
                trades.append({
                    "Data Entrada": data_entrada,
                    "Preço Entrada": preco_entrada,
                    "Data Saída": df.index[i],
                    "Preço Saída": preco_saida,
                    "Lucro": lucro,
                    "Motivo": motivo,
                    "Quantidade": quantidade,
                    "Dias Hold": dias_hold,
                    "Lista": lista_selecionada
                })
                posicao = False
    
    # Resultados
    df_trades = pd.DataFrame(trades)
    
    if not df_trades.empty:
        df_trades["Retorno R$"] = df_trades["Lucro"]
        df_trades["Capital Acumulado"] = capital_inicial + df_trades["Retorno R$"].cumsum()
        lucro_total = df_trades["Retorno R$"].sum()
        capital_final = capital_inicial + lucro_total
    else:
        lucro_total = 0
        capital_final = capital_inicial
        st.warning("Não foram encontrados trades com os parâmetros selecionados.")
    
    # Exibindo resultados
    st.subheader("📊 Resultado do Backtest")
    stats = {
        "Qtd Trades": len(df_trades) if not df_trades.empty else 0,
        "Lucro Total": lucro_total,
        "Capital Final": capital_final,
        "% Trades Lucrativos": (df_trades["Retorno R$"] > 0).sum() / len(df_trades) * 100 if not df_trades.empty else 0,
        "Retorno %": ((capital_final / capital_inicial) - 1) * 100 if capital_inicial > 0 else 0
    }
    
    st.dataframe(
        pd.DataFrame([stats]).style.format({
            "Lucro Total": "R$ {:.2f}",
            "Capital Final": "R$ {:.2f}",
            "% Trades Lucrativos": "{:.2f}%",
            "Retorno %": "{:.2f}%"
        })
    )
    
    if not df_trades.empty:
        st.subheader("📄 Trades Realizados")
        st.dataframe(
            df_trades.style.format({
                "Preço Entrada": "R$ {:.2f}",
                "Preço Saída": "R$ {:.2f}",
                "Lucro": "R$ {:.2f}",
                "Retorno R$": "R$ {:.2f}",
                "Capital Acumulado": "R$ {:.2f}",
                "Data Entrada": lambda x: x.strftime("%d-%m-%Y"),
                "Data Saída": lambda x: x.strftime("%d-%m-%Y")
            })
        )

        # Quadro de estatísticas detalhadas
        st.markdown("### 📋 Estatísticas do Resultado")
        total_ops = len(df_trades)
        ganhos = df_trades[df_trades["Retorno R$"] > 0]["Retorno R$"]
        perdas = df_trades[df_trades["Retorno R$"] <= 0]["Retorno R$"]
        acertos = len(ganhos)
        perc_acertos = (acertos / total_ops * 100) if total_ops > 0 else 0
        resultado_perc = (df_trades["Capital Acumulado"].iloc[-1] - capital_inicial) / capital_inicial * 100 if total_ops > 0 else 0
        ganho_medio = ganhos.mean() if not ganhos.empty else 0
        perda_media = perdas.mean() if not perdas.empty else 0
        capital = df_trades["Capital Acumulado"]
        dd = max([max(capital[:i+1]) - v for i, v in enumerate(capital)]) if total_ops > 0 else 0
        dd_perc = dd / max(capital) * 100 if max(capital) != 0 else 0
        fator_lucro = -ganhos.sum() / perdas.sum() if not perdas.empty and perdas.sum() != 0 else 0

        st.markdown(f"""
        - 📌 **Número de operações**: {total_ops}  
        - ✅ **Acertos**: {perc_acertos:.2f}% ({acertos})  
        - 💹 **Resultado**: {resultado_perc:.2f}%  
        - 💰 **Ganho médio**: R$ {ganho_medio:.2f}  
        - 📉 **Perda média**: R$ {perda_media:.2f}  
        - 🔻 **Drawdown**: {dd_perc:.2f}%  
        - ⚖️ **Fator de Lucro**: {fator_lucro:.2f}
        """)

        st.subheader("📈 Curva de Capital")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_trades["Data Saída"],
            y=df_trades["Capital Acumulado"],
            mode="lines+markers",
            name="Capital"
        ))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📆 Retorno Mensal (Não Acumulado)")

        # Garantir tipo datetime e valores numéricos
        df_trades["Data Saída"] = pd.to_datetime(df_trades["Data Saída"])
        df_trades["AnoMes"] = df_trades["Data Saída"].dt.to_period("M").astype(str)

        # Agrupar por mês
        retorno_mensal = df_trades.groupby("AnoMes")["Retorno R$"].sum().reset_index()
        retorno_mensal["Retorno R$"] = pd.to_numeric(retorno_mensal["Retorno R$"], errors="coerce")

        # Gráfico com cores condicionais
        cores = ["mediumseagreen" if val >= 0 else "indianred" for val in retorno_mensal["Retorno R$"]]

        fig_bar = go.Figure(data=[
            go.Bar(
                x=retorno_mensal["AnoMes"],
                y=retorno_mensal["Retorno R$"],
                marker_color=cores,
                text=[f"R$ {v:,.2f}" for v in retorno_mensal["Retorno R$"]],
                textposition="outside",
            )
        ])

        fig_bar.update_layout(
            xaxis_title="Mês",
            yaxis_title="Retorno (R$)",
            yaxis=dict(zeroline=True),
            showlegend=False,
            bargap=0.2,
            height=400
        )

        st.plotly_chart(fig_bar, use_container_width=True)

        # Tabela opcional com os dados mensais
        with st.expander("🔍 Ver Tabela de Retornos Mensais"):
            st.dataframe(retorno_mensal.style.format({"Retorno R$": "R$ {:.2f}"}))