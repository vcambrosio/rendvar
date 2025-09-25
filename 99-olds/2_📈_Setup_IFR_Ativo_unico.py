import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from datetime import timedelta
from PIL import Image

# Caminho dos dados
parquet_path = "01-dados/ativos_historicos.parquet"

st.title("📈 Backtest - Setup IFR - Ativo único")

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
data_inicial_padrao = data_final_padrao - timedelta(days=1095)  # Alterado para 1095 dias como no Lista

st.sidebar.header("🎯 Parâmetros do Ativo")
ativo_escolhido = st.sidebar.selectbox("Escolha o ativo", ativos_disponiveis)

st.sidebar.header("📅 Período do Backtest")  # Título alterado para seguir o padrão do Lista
data_inicial = st.sidebar.date_input("Data inicial", value=data_inicial_padrao)
data_final = st.sidebar.date_input("Data final", value=data_final_padrao)

st.sidebar.header("💰 Capital Inicial")
capital_inicial = st.sidebar.number_input("Capital disponível (R$)", value=100000.0, step=10000.0)  # Alterado para 100k como no Lista

st.sidebar.header("📈 Parâmetros IFR")
periodo_ifr = st.sidebar.number_input("Período do IFR", min_value=2, max_value=30, value=2)
modo_otimizacao = st.sidebar.radio("Modo IFR:", ["Valor fixo", "Intervalo de valores"])
if modo_otimizacao == "Valor fixo":
    ifr_entrada = st.sidebar.slider(f"IFR({periodo_ifr}) abaixo de", min_value=1, max_value=50, value=10)
    intervalo_ifr = [ifr_entrada]
else:
    ifr_min = st.sidebar.slider(f"Valor mínimo do IFR({periodo_ifr})", min_value=1, max_value=49, value=5)
    ifr_max = st.sidebar.slider(f"Valor máximo do IFR({periodo_ifr})", min_value=2, max_value=50, value=30)  # Alterado max para 30 como no Lista
    intervalo_ifr = list(range(ifr_min, ifr_max + 1))

st.sidebar.header("🔥 Critérios de Entrada Adicionais")
usar_media = st.sidebar.checkbox("Usar Média Móvel como filtro adicional?", value=True)  # Alterado para True como padrão
if usar_media:
    media_periodos = st.sidebar.number_input("Períodos da Média Móvel", min_value=1, max_value=200, value=200)

st.sidebar.header("📤 Critérios de Saída")
max_candles_saida = st.sidebar.slider("Máxima dos últimos X candles", min_value=1, max_value=10, value=2)
usar_timeout = st.sidebar.checkbox("Forçar saída após X candles?", value=True)  # Alterado para True como padrão
if usar_timeout:
    max_hold_days = st.sidebar.number_input("Forçar saída após X candles", min_value=1, max_value=20, value=5)
else:
    max_hold_days = None

st.sidebar.header("⚠️ Stop Loss")
usar_stop = st.sidebar.checkbox("Usar Stop Loss?", value=True)  # Alterado para True como padrão
if usar_stop:
    stop_pct = st.sidebar.number_input("Stop Loss (% abaixo do preço de entrada)", min_value=0.1, max_value=50.0, value=5.0)
else:
    stop_pct = None

with st.sidebar:
    st.markdown("---")  # Linha separadora abaixo
    col_logo, col_texto = st.columns([1, 3])
    
    with col_logo:
        logo_path = os.path.join("02-imagens", "logo.png")
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            base_width = 50
            w_percent = (base_width / float(logo.size[0]))
            h_size = int((float(logo.size[1]) * float(w_percent)))
            logo = logo.resize((base_width, h_size), Image.Resampling.LANCZOS)
            st.image(logo, use_container_width=False)
    
    with col_texto:
        st.markdown("""
        <div style='display: flex; align-items: center; height: 100%;'>
            <p style='margin: 0;'>Desenvolvido por Vladimir</p>
        </div>
        """, unsafe_allow_html=True)

# === BACKTEST ===
if st.button("▶️ Executar Backtest"):
    resultados = []

    for ifr_entrada in intervalo_ifr:
        # Seleciona apenas o ativo escolhido
        df = df_filtrado[df_filtrado["Ticker"] == ativo_escolhido].copy()
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        
        # Seguindo a lógica do arquivo Lista com buffer expandido
        extra_ano = 365
        buffer_dias = max(media_periodos if usar_media else periodo_ifr, 10, extra_ano)
        
        data_inicial_expandida = pd.to_datetime(data_inicial) - timedelta(days=buffer_dias)
        df = df[(df["Date"] >= data_inicial_expandida) & (df["Date"] <= pd.to_datetime(data_final))]

        if df.empty:
            continue
            
        df.sort_values("Date", inplace=True)
        df.set_index("Date", inplace=True)

        # Calcula IFR usando EWM como no arquivo Lista
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.ewm(com=periodo_ifr - 1, min_periods=periodo_ifr).mean()
        avg_loss = loss.ewm(com=periodo_ifr - 1, min_periods=periodo_ifr).mean()

        rs = avg_gain / avg_loss
        df["IFR"] = 100 - (100 / (1 + rs))

        # Calcula a média móvel (se habilitado)
        if usar_media:
            df["Media"] = df["Close"].rolling(media_periodos).mean()
            df["compra"] = (df["IFR"] < ifr_entrada) & (df["Close"] > df["Media"])
        else:
            df["compra"] = df["IFR"] < ifr_entrada

        # Remove candles anteriores à data inicial real
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
                    trades.append({
                        "IFR": ifr_entrada,
                        "IFR Entrada": df.loc[data_entrada, "IFR"],
                        "Data Entrada": data_entrada,
                        "Preço Entrada": preco_entrada,
                        "Data Saída": df.index[i],
                        "Preço Saída": preco_saida,
                        "Lucro": lucro,
                        "Motivo": motivo,
                        "Quantidade": quantidade,
                        "Lista": lista_selecionada,
                        "Ativo": ativo_escolhido
                    })
                    posicao = False

        df_trades = pd.DataFrame(trades)
        if not df_trades.empty:
            df_trades["Retorno R$"] = df_trades["Lucro"]
            df_trades["Capital Acumulado"] = capital_inicial + df_trades["Retorno R$"].cumsum()
            lucro_total = df_trades["Retorno R$"].sum()
            
            # Calcula estatísticas como no arquivo Lista
            total_ops = len(df_trades)
            ganhos = df_trades[df_trades["Retorno R$"] > 0]["Retorno R$"]
            perdas = df_trades[df_trades["Retorno R$"] <= 0]["Retorno R$"]
            acertos = len(ganhos)
            perc_acertos = (acertos / total_ops * 100) if total_ops > 0 else 0
            resultado_perc = (df_trades["Capital Acumulado"].iloc[-1] - capital_inicial) / capital_inicial * 100
            ganho_medio = ganhos.mean() if not ganhos.empty else 0
            perda_media = perdas.mean() if not perdas.empty else 0
            capital = df_trades["Capital Acumulado"]
            dd = max([max(capital[:i+1]) - v for i, v in enumerate(capital)])
            dd_perc = dd / max(capital) * 100 if max(capital) != 0 else 0
            fator_lucro = -ganhos.sum() / perdas.sum() if not perdas.empty and perdas.sum() != 0 else 0
            indice_ld = resultado_perc / dd_perc if dd_perc != 0 else 0
            
        else:
            lucro_total = 0
            perc_acertos = 0
            resultado_perc = 0
            ganho_medio = 0
            perda_media = 0
            dd_perc = 0
            fator_lucro = 0
            indice_ld = 0

        resultados.append({
            "IFR": ifr_entrada,
            "Trades": len(df_trades),
            "Lucro Total": lucro_total,
            "% Trades Lucrativos": perc_acertos,
            "Capital Final": capital_inicial + lucro_total,
            "df_trades": df_trades,
            "Lista": lista_selecionada,
            "Resultado %": resultado_perc,
            "Drawdown %": dd_perc,
            "Fator Lucro": fator_lucro,
            "Ganho Médio": ganho_medio,
            "Perda Média": perda_media,
            "Índice LD": indice_ld
        })

    df_result = pd.DataFrame(resultados).sort_values(by="Lucro Total", ascending=False)

    st.subheader("📊 Resultado da Otimização IFR")
    st.dataframe(
        df_result.drop(columns=["df_trades"]).style.format({
            "Lucro Total": "R$ {:.2f}",
            "% Trades Lucrativos": "{:.2f}%",
            "Capital Final": "R$ {:.2f}",
            "Resultado %": "{:.2f}%",
            "Drawdown %": "{:.2f}%",
            "Fator Lucro": "{:.2f}",
            "Ganho Médio": "R$ {:.2f}",
            "Perda Média": "R$ {:.2f}",
            "Índice LD": "{:.2f}"
        })
    )

    melhor = df_result.iloc[0]
    st.success(f"Melhor IFR: {melhor['IFR']} | Lucro Total: R$ {melhor['Lucro Total']:.2f} | Lista: {melhor['Lista']}")

    st.subheader("📄 Trades do Melhor IFR")
    st.dataframe(
        melhor["df_trades"].style.format({
            "Preço Entrada": "R$ {:.2f}",
            "Preço Saída": "R$ {:.2f}",
            "Lucro": "R$ {:.2f}",
            "Retorno R$": "R$ {:.2f}",
            "Capital Acumulado": "R$ {:.2f}",
            "IFR Entrada": "{:.0f}",
            "Data Entrada": lambda x: x.strftime("%d-%m-%Y"),
            "Data Saída": lambda x: x.strftime("%d-%m-%Y")
        })
    )

    st.markdown("### 📋 Estatísticas do Resultado")
    df_trades_melhor = melhor["df_trades"]
    total_ops = len(df_trades_melhor)
    
    if total_ops > 0:
        ganhos = df_trades_melhor[df_trades_melhor["Retorno R$"] > 0]["Retorno R$"]
        perdas = df_trades_melhor[df_trades_melhor["Retorno R$"] <= 0]["Retorno R$"]
        acertos = len(ganhos)
        perc_acertos = (acertos / total_ops * 100)
        resultado_perc = melhor["Resultado %"]
        ganho_medio = melhor["Ganho Médio"]
        perda_media = melhor["Perda Média"]
        dd_perc = melhor["Drawdown %"]
        fator_lucro = melhor["Fator Lucro"]
        indice_ld = melhor["Índice LD"]
    else:
        perc_acertos = 0
        resultado_perc = 0
        ganho_medio = 0
        perda_media = 0
        dd_perc = 0
        fator_lucro = 0
        indice_ld = 0

    st.markdown(f"""
    - 📌 **Número de operações**: {total_ops}  
    - ✅ **Acertos**: {perc_acertos:.2f}% ({acertos if total_ops > 0 else 0})  
    - 💹 **Resultado**: {resultado_perc:.2f}%  
    - 💰 **Ganho médio**: R$ {ganho_medio:.2f}  
    - 📉 **Perda média**: R$ {perda_media:.2f}  
    - 📻 **Drawdown**: {dd_perc:.2f}%  
    - ⚖️ **Fator de Lucro**: {fator_lucro:.2f}
    - 📊 **Índice LD**: {indice_ld:.2f}
    """)

    if total_ops > 0:
        st.subheader("📈 Curva de Capital")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=melhor["df_trades"]["Data Saída"],
            y=melhor["df_trades"]["Capital Acumulado"],
            mode="lines+markers",
            name="Capital"
        ))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📆 Retorno Mensal (Não Acumulado)")
        df_trades_melhor["Data Saída"] = pd.to_datetime(df_trades_melhor["Data Saída"])
        df_trades_melhor["AnoMes"] = df_trades_melhor["Data Saída"].dt.to_period("M").astype(str)
        retorno_mensal = df_trades_melhor.groupby("AnoMes")["Retorno R$"].sum().reset_index()
        retorno_mensal["Retorno R$"] = pd.to_numeric(retorno_mensal["Retorno R$"], errors="coerce")

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

        with st.expander("🔍 Ver Tabela de Retornos Mensais"):
            st.dataframe(retorno_mensal.style.format({"Retorno R$": "R$ {:.2f}"}))
    else:
        st.warning("⚠️ Nenhum trade foi executado com os parâmetros selecionados.")