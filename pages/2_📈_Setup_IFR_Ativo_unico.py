import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from datetime import timedelta
from PIL import Image

# Diagnóstico do caminho dos dados
st.title("📈 Backtest - Setup IFR - Ativo único")

# Verificar diretório atual e arquivos disponíveis
current_dir = os.getcwd()
st.info(f"📁 Diretório atual: {current_dir}")

# Possíveis localizações do arquivo
possible_paths = [
    "01-dados/ativos_historicos.parquet",
    "./01-dados/ativos_historicos.parquet", 
    os.path.join("01-dados", "ativos_historicos.parquet"),
    os.path.join(current_dir, "01-dados", "ativos_historicos.parquet")
]

parquet_path = None
for path in possible_paths:
    if os.path.exists(path):
        parquet_path = path
        st.success(f"✅ Base encontrada em: {path}")
        break

# Se não encontrou, listar estrutura de diretórios para debug
if not parquet_path:
    st.error("❌ Base de dados não encontrada em nenhum dos caminhos esperados:")
    for path in possible_paths:
        st.write(f"  - {path}: {'✅' if os.path.exists(path) else '❌'}")
    
    # Verificar se existe diretório 01-dados
    if os.path.exists("01-dados"):
        st.write("📂 Conteúdo do diretório '01-dados':")
        try:
            files = os.listdir("01-dados")
            for file in files:
                st.write(f"  - {file}")
        except Exception as e:
            st.write(f"  Erro ao listar: {e}")
    else:
        st.write("❌ Diretório '01-dados' não existe")
    
    # Listar arquivos no diretório atual
    st.write("📂 Arquivos no diretório atual:")
    try:
        files = [f for f in os.listdir(".") if f.endswith('.parquet')]
        if files:
            for file in files:
                st.write(f"  - {file}")
        else:
            st.write("  Nenhum arquivo .parquet encontrado")
    except Exception as e:
        st.write(f"  Erro ao listar: {e}")
    
    st.error("Execute primeiro o script '📥 Atualiza base YF MT' para criar a base de dados.")
    st.stop()

# Carrega dados
try:
    df_base = pd.read_parquet(parquet_path)
    st.success(f"📊 Base carregada com {len(df_base):,} registros")
except Exception as e:
    st.error(f"❌ Erro ao carregar a base: {str(e)}")
    st.stop()

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
data_inicial_padrao = data_final_padrao - timedelta(days=1095)

st.sidebar.header("🎯 Parâmetros do Ativo")
ativo_escolhido = st.sidebar.selectbox("Escolha o ativo", ativos_disponiveis)

st.sidebar.header("📅 Período do Backtest")

# Opções de período rápido
periodo_rapido = st.sidebar.selectbox(
    "Selecione o período:", 
    ["Personalizado", "1 ano", "2 anos", "3 anos", "5 anos", "10 anos"],
    index=0
)

# Calcula as datas baseadas na seleção
if periodo_rapido != "Personalizado":
    if periodo_rapido == "1 ano":
        data_inicial_calc = data_final_padrao - timedelta(days=365)
    elif periodo_rapido == "2 anos":
        data_inicial_calc = data_final_padrao - timedelta(days=730)
    elif periodo_rapido == "3 anos":
        data_inicial_calc = data_final_padrao - timedelta(days=1095)
    elif periodo_rapido == "5 anos":
        data_inicial_calc = data_final_padrao - timedelta(days=1825)
    elif periodo_rapido == "10 anos":
        data_inicial_calc = data_final_padrao - timedelta(days=3650)
    
    # Mostra as datas calculadas
    st.sidebar.write(f"📅 Período: {data_inicial_calc.strftime('%d/%m/%Y')} a {data_final_padrao.strftime('%d/%m/%Y')}")
    
    data_inicial = st.sidebar.date_input("Data inicial", value=data_inicial_calc)
    data_final = st.sidebar.date_input("Data final", value=data_final_padrao)
else:
    data_inicial = st.sidebar.date_input("Data inicial", value=data_inicial_padrao)
    data_final = st.sidebar.date_input("Data final", value=data_final_padrao)

st.sidebar.header("💰 Capital Inicial")
capital_inicial = st.sidebar.number_input("Capital disponível (R$)", value=100000.0, step=10000.0)

st.sidebar.header("📈 Parâmetros IFR")
periodo_ifr = st.sidebar.number_input("Período do IFR", min_value=2, max_value=30, value=2)
modo_otimizacao = st.sidebar.radio("Modo IFR:", ["Valor fixo", "Intervalo de valores"])
if modo_otimizacao == "Valor fixo":
    ifr_entrada = st.sidebar.slider(f"IFR({periodo_ifr}) abaixo de", min_value=1, max_value=50, value=10)
    intervalo_ifr = [ifr_entrada]
else:
    ifr_min = st.sidebar.slider(f"Valor mínimo do IFR({periodo_ifr})", min_value=1, max_value=49, value=5)
    ifr_max = st.sidebar.slider(f"Valor máximo do IFR({periodo_ifr})", min_value=2, max_value=50, value=30)
    intervalo_ifr = list(range(ifr_min, ifr_max + 1))

st.sidebar.header("🔥 Critérios de Entrada Adicionais")
usar_media = st.sidebar.checkbox("Usar Média Móvel como filtro adicional?", value=True)
if usar_media:
    media_periodos = st.sidebar.number_input("Períodos da Média Móvel", min_value=1, max_value=200, value=200)

st.sidebar.header("📤 Critérios de Saída")
max_candles_saida = st.sidebar.slider("Máxima dos últimos X candles", min_value=1, max_value=10, value=2)
usar_timeout = st.sidebar.checkbox("Forçar saída após X candles?", value=True)
if usar_timeout:
    max_hold_days = st.sidebar.number_input("Forçar saída após X candles", min_value=1, max_value=20, value=5)
else:
    max_hold_days = None

st.sidebar.header("⚠️ Stop Loss")
usar_stop = st.sidebar.checkbox("Usar Stop Loss?", value=True)
if usar_stop:
    stop_pct = st.sidebar.number_input("Stop Loss (% abaixo do preço de entrada)", min_value=0.1, max_value=50.0, value=5.0)
else:
    stop_pct = None

with st.sidebar:
    st.markdown("---")
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

    # Validação inicial dos dados
    df_ativo = df_filtrado[df_filtrado["Ticker"] == ativo_escolhido].copy()
    
    if df_ativo.empty:
        st.error(f"❌ Nenhum dado encontrado para o ativo {ativo_escolhido} na lista {lista_selecionada}")
        st.stop()
    
    # Verificar se há dados suficientes no período
    df_ativo["Date"] = pd.to_datetime(df_ativo["Date"]).dt.tz_localize(None)
    dados_no_periodo = df_ativo[(df_ativo["Date"] >= pd.to_datetime(data_inicial)) & 
                               (df_ativo["Date"] <= pd.to_datetime(data_final))]
    
    if dados_no_periodo.empty:
        st.error(f"❌ Nenhum dado encontrado para {ativo_escolhido} no período de {data_inicial} a {data_final}")
        st.stop()
    
    st.info(f"📊 Processando {ativo_escolhido} com {len(dados_no_periodo)} registros no período...")

    for ifr_entrada in intervalo_ifr:
        # Seleciona apenas o ativo escolhido
        df = df_ativo.copy()
        
        # Buffer expandido para cálculos
        extra_ano = 365
        buffer_dias = max(media_periodos if usar_media else periodo_ifr, 10, extra_ano)
        
        data_inicial_expandida = pd.to_datetime(data_inicial) - timedelta(days=buffer_dias)
        df = df[(df["Date"] >= data_inicial_expandida) & (df["Date"] <= pd.to_datetime(data_final))]

        if df.empty:
            st.warning(f"⚠️ Dados insuficientes para IFR {ifr_entrada}")
            continue
            
        df.sort_values("Date", inplace=True)
        df.set_index("Date", inplace=True)

        # Verifica se há dados suficientes para os cálculos
        if len(df) < max(periodo_ifr, media_periodos if usar_media else 0, max_candles_saida):
            st.warning(f"⚠️ Dados insuficientes para cálculos técnicos (IFR {ifr_entrada})")
            continue

        # Calcula IFR usando EWM
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.ewm(com=periodo_ifr - 1, min_periods=periodo_ifr).mean()
        avg_loss = loss.ewm(com=periodo_ifr - 1, min_periods=periodo_ifr).mean()

        # Evita divisão por zero
        rs = avg_gain / avg_loss.replace(0, np.inf)
        df["IFR"] = 100 - (100 / (1 + rs))

        # Calcula a média móvel (se habilitado)
        if usar_media:
            df["Media"] = df["Close"].rolling(media_periodos).mean()
            df["compra"] = (df["IFR"] < ifr_entrada) & (df["Close"] > df["Media"])
        else:
            df["compra"] = df["IFR"] < ifr_entrada

        # Remove candles anteriores à data inicial real
        df_analise = df[df.index >= pd.to_datetime(data_inicial)]
        
        # Guarda informações sobre o período efetivamente considerado
        if not df_analise.empty:
            data_inicial_efetiva = df_analise.index.min()
            data_final_efetiva = df_analise.index.max()
            total_dias_efetivos = (data_final_efetiva - data_inicial_efetiva).days
        else:
            data_inicial_efetiva = pd.to_datetime(data_inicial)
            data_final_efetiva = pd.to_datetime(data_final)
            total_dias_efetivos = 0
        
        if len(df_analise) <= max_candles_saida:
            st.warning(f"⚠️ Período muito curto para análise (IFR {ifr_entrada})")
            # Ainda adiciona aos resultados, mas com valores zerados
            resultados.append({
                "IFR": ifr_entrada,
                "Trades": 0,
                "Lucro Total": 0.0,
                "% Trades Lucrativos": 0.0,
                "Capital Final": capital_inicial,
                "df_trades": pd.DataFrame(),
                "Lista": lista_selecionada,
                "Resultado %": 0.0,
                "Drawdown %": 0.0,
                "Fator Lucro": 0.0,
                "Ganho Médio": 0.0,
                "Perda Média": 0.0,
                "Índice LD": 0.0,
                "Data Inicial Efetiva": data_inicial_efetiva,
                "Data Final Efetiva": data_final_efetiva,
                "Dias Efetivos": total_dias_efetivos
            })
            continue
            
        posicao = False
        preco_entrada = 0
        data_entrada = None
        trades = []

        for i in range(max_candles_saida, len(df)):
            if df.index[i] < pd.to_datetime(data_inicial):
                continue
                
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

                # Janela para máxima dos últimos candles
                inicio_janela = max(0, i - max_candles_saida)
                janela_max = df["High"].iloc[inicio_janela:i + 1]
                
                if len(janela_max) > 1:
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

                # Verificações adicionais de saída
                if not sair and usar_timeout and max_hold_days and dias_hold >= max_hold_days:
                    sair = True
                    preco_saida = preco_abertura
                    motivo = "Saída forçada após x candles"
                elif not sair and usar_stop and preco_stop and preco_minimo <= preco_stop:
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
        
        # Calcula estatísticas
        if not df_trades.empty:
            df_trades["Retorno R$"] = df_trades["Lucro"]
            df_trades["Capital Acumulado"] = capital_inicial + df_trades["Retorno R$"].cumsum()
            lucro_total = df_trades["Retorno R$"].sum()
            
            total_ops = len(df_trades)
            ganhos = df_trades[df_trades["Retorno R$"] > 0]["Retorno R$"]
            perdas = df_trades[df_trades["Retorno R$"] <= 0]["Retorno R$"]
            acertos = len(ganhos)
            perc_acertos = (acertos / total_ops * 100) if total_ops > 0 else 0
            resultado_perc = (df_trades["Capital Acumulado"].iloc[-1] - capital_inicial) / capital_inicial * 100
            ganho_medio = ganhos.mean() if not ganhos.empty else 0
            perda_media = perdas.mean() if not perdas.empty else 0
            capital = df_trades["Capital Acumulado"]
            dd = max([max(capital[:i+1]) - v for i, v in enumerate(capital)]) if len(capital) > 0 else 0
            dd_perc = dd / max(capital) * 100 if len(capital) > 0 and max(capital) != 0 else 0
            fator_lucro = -ganhos.sum() / perdas.sum() if not perdas.empty and perdas.sum() != 0 else 0
            indice_ld = resultado_perc / dd_perc if dd_perc != 0 else 0
            
        else:
            lucro_total = 0.0
            perc_acertos = 0.0
            resultado_perc = 0.0
            ganho_medio = 0.0
            perda_media = 0.0
            dd_perc = 0.0
            fator_lucro = 0.0
            indice_ld = 0.0

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
            "Índice LD": indice_ld,
            "Data Inicial Efetiva": data_inicial_efetiva,
            "Data Final Efetiva": data_final_efetiva,
            "Dias Efetivos": total_dias_efetivos
        })

    # Verifica se temos resultados antes de tentar criar o DataFrame
    if not resultados:
        st.error("❌ Nenhum resultado foi gerado. Verifique os parâmetros e dados disponíveis.")
        st.stop()

    df_result = pd.DataFrame(resultados).sort_values(by="Lucro Total", ascending=False)

    # Exibe informações sobre o período considerado
    if not df_result.empty:
        melhor = df_result.iloc[0]
        st.info(f"""
        📅 **Período Efetivamente Considerado**:
        - Data inicial solicitada: {data_inicial.strftime('%d/%m/%Y')}
        - Data final solicitada: {data_final.strftime('%d/%m/%Y')}
        - Data inicial efetiva: {melhor['Data Inicial Efetiva'].strftime('%d/%m/%Y') if melhor['Data Inicial Efetiva'] else 'N/A'}
        - Data final efetiva: {melhor['Data Final Efetiva'].strftime('%d/%m/%Y') if melhor['Data Final Efetiva'] else 'N/A'}
        - Total de dias considerados: {melhor['Dias Efetivos']} dias
        - Ativo: {ativo_escolhido}
        """)

    st.subheader("📊 Resultado da Otimização IFR")
    st.dataframe(
        df_result.drop(columns=["df_trades", "Data Inicial Efetiva", "Data Final Efetiva"]).style.format({
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

    if not df_result.empty:
        melhor = df_result.iloc[0]
        st.success(f"Melhor IFR: {melhor['IFR']} | Lucro Total: R$ {melhor['Lucro Total']:.2f} | Lista: {melhor['Lista']}")

        if not melhor["df_trades"].empty:
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
                df_trades_melhor_copy = melhor["df_trades"].copy()
                df_trades_melhor_copy["Data Saída"] = pd.to_datetime(df_trades_melhor_copy["Data Saída"])
                df_trades_melhor_copy["AnoMes"] = df_trades_melhor_copy["Data Saída"].dt.to_period("M").astype(str)
                retorno_mensal = df_trades_melhor_copy.groupby("AnoMes")["Retorno R$"].sum().reset_index()
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
        else:
            st.warning("⚠️ O melhor resultado não gerou trades. Considere ajustar os parâmetros.")
    else:
        st.warning("⚠️ Não foi possível executar o backtest. Verifique se o ativo possui dados no período selecionado.")