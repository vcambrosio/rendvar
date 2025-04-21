import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from datetime import timedelta
import base64
from io import BytesIO
from PIL import Image

# Configuração da página
st.set_page_config(page_title="Backtest IFR Múltiplo", layout="wide")

# Caminho dos dados
parquet_path = "01-dados/ativos_historicos.parquet"

st.title("📈 Backtest - Setup IFR - Múltiplos Ativos")

# Verifica se a base existe
if not os.path.exists(parquet_path):
    st.error("❌ Base de dados não encontrada. Atualize a base antes de continuar.")
    st.stop()

# Carrega dados
df_base = pd.read_parquet(parquet_path)

# === INTERFACE STREAMLIT ===
st.sidebar.header("📋 Filtros")

# Seleção de lista
listas_disponiveis = sorted(df_base["Lista"].unique().tolist())
lista_selecionada = st.sidebar.selectbox("Selecione a lista", listas_disponiveis)

# Filtrar ativos pela lista selecionada
df_filtrado = df_base[df_base["Lista"] == lista_selecionada]
ativos_disponiveis = sorted(df_filtrado["Ticker"].unique().tolist())

# Opção para selecionar todos os ativos
selecionar_todos = st.sidebar.checkbox("Selecionar todos os ativos da lista", value=True)

if selecionar_todos:
    ativos_escolhidos = ativos_disponiveis
else:
    ativos_escolhidos = st.sidebar.multiselect("Escolha os ativos", ativos_disponiveis, default=ativos_disponiveis[:5])

# Define datas padrão com base no banco
data_final_padrao = pd.to_datetime(df_filtrado["Date"].max()).normalize()
data_inicial_padrao = data_final_padrao - timedelta(days=1095)

st.sidebar.header("📅 Período do Backtest")
data_inicial = st.sidebar.date_input("Data inicial", value=data_inicial_padrao)
data_final = st.sidebar.date_input("Data final", value=data_final_padrao)

st.sidebar.header("💰 Capital Inicial")
capital_inicial = st.sidebar.number_input("Capital disponível (R$)", value=100000.0, step=10000.0)

st.sidebar.header("📈 Parâmetros IFR")
periodo_ifr = st.sidebar.number_input("Período do IFR", min_value=2, max_value=30, value=2)
ifr_min = st.sidebar.slider(f"Valor mínimo do IFR({periodo_ifr})", min_value=1, max_value=49, value=5)
ifr_max = st.sidebar.slider(f"Valor máximo do IFR({periodo_ifr})", min_value=2, max_value=50, value=30)
intervalo_ifr = list(range(ifr_min, ifr_max + 1))

st.sidebar.header("📥 Critérios de Entrada Adicionais")
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








# Função para criar um link de download para o DataFrame
def get_excel_download_link(df, filename="dados_backtest.xlsx"):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Resultados')
    writer.close()
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">📥 Baixar arquivo Excel</a>'
    return href

# Função para realizar o backtest em um ativo específico
def backtest_ativo(ativo, df_filtrado, data_inicial, data_final, 
                   periodo_ifr, intervalo_ifr, usar_media, media_periodos,
                   max_candles_saida, usar_timeout, max_hold_days,
                   usar_stop, stop_pct, capital_inicial):
    
    resultados = []
    
    for ifr_entrada in intervalo_ifr:
        df = df_filtrado[df_filtrado["Ticker"] == ativo].copy()
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        
        buffer_dias = max(media_periodos if usar_media else periodo_ifr, 10)
        data_inicial_expandida = pd.to_datetime(data_inicial) - timedelta(days=buffer_dias)
        df = df[(df["Date"] >= data_inicial_expandida) & (df["Date"] <= pd.to_datetime(data_final))]
        
        if df.empty:
            continue
            
        df.sort_values("Date", inplace=True)
        df.set_index("Date", inplace=True)
        
        # Cálculo do IFR
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
                        "Ativo": ativo
                    })
                    posicao = False
        
        df_trades = pd.DataFrame(trades)
        if not df_trades.empty:
            df_trades["Retorno R$"] = df_trades["Lucro"]
            df_trades["Capital Acumulado"] = capital_inicial + df_trades["Retorno R$"].cumsum()
            lucro_total = df_trades["Retorno R$"].sum()
            
            # Cálculo de métricas adicionais
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
            
            resultados.append({
                "Ativo": ativo,
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
                "Perda Média": perda_media
            })
        else:
            resultados.append({
                "Ativo": ativo,
                "IFR": ifr_entrada,
                "Trades": 0,
                "Lucro Total": 0,
                "% Trades Lucrativos": 0,
                "Capital Final": capital_inicial,
                "df_trades": pd.DataFrame(),
                "Lista": lista_selecionada,
                "Resultado %": 0,
                "Drawdown %": 0,
                "Fator Lucro": 0,
                "Ganho Médio": 0,
                "Perda Média": 0
            })
    
    # Ordena por lucro total para cada ativo
    df_result = pd.DataFrame(resultados).sort_values(by="Lucro Total", ascending=False)
    
    if not df_result.empty:
        return df_result.iloc[0]  # Retorna o melhor resultado
    else:
        return {
            "Ativo": ativo,
            "IFR": None,
            "Trades": 0,
            "Lucro Total": 0,
            "% Trades Lucrativos": 0,
            "Capital Final": capital_inicial,
            "df_trades": pd.DataFrame(),
            "Lista": lista_selecionada,
            "Resultado %": 0,
            "Drawdown %": 0,
            "Fator Lucro": 0,
            "Ganho Médio": 0,
            "Perda Média": 0
        }

# === EXECUÇÃO DO BACKTEST ===
if 'backtest_executado' not in st.session_state:
    st.session_state.backtest_executado = False
    st.session_state.df_melhores = None
    st.session_state.melhores_resultados = None

if st.button("▶️ Executar Backtest Múltiplo"):
    if not ativos_escolhidos:
        st.warning("⚠️ Selecione pelo menos um ativo para continuar.")
        st.stop()
    
    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Importar BytesIO para exportar Excel
    from io import BytesIO
    
    # Lista para armazenar os melhores resultados de cada ativo
    melhores_resultados = []
    
    # Total de ativos para calcular progresso
    total_ativos = len(ativos_escolhidos)
    
    # Executar backtest para cada ativo
    for idx, ativo in enumerate(ativos_escolhidos):
        status_text.text(f"Processando {ativo} ({idx+1}/{total_ativos})")
        
        # Executa o backtest para o ativo atual
        melhor_resultado = backtest_ativo(
            ativo, df_filtrado, data_inicial, data_final,
            periodo_ifr, intervalo_ifr, usar_media, 
            media_periodos if usar_media else 0,
            max_candles_saida, usar_timeout, 
            max_hold_days if usar_timeout else None,
            usar_stop, stop_pct if usar_stop else None,
            capital_inicial
        )
        
        if melhor_resultado["IFR"] is not None:
            melhores_resultados.append(melhor_resultado)
        
        # Atualizar barra de progresso
        progress_bar.progress((idx + 1) / total_ativos)
    
    # Remover a barra de progresso e o status
    progress_bar.empty()
    status_text.empty()
    
    if not melhores_resultados:
        st.warning("⚠️ Nenhum resultado encontrado para os parâmetros selecionados.")
        st.stop()
    
    # Criar DataFrame com os melhores resultados
    df_melhores = pd.DataFrame([{
        "Ativo": res["Ativo"],
        "IFR": res["IFR"],
        "Trades": res["Trades"],
        "Lucro Total (R$)": res["Lucro Total"],
        "% Trades Lucrativos": res["% Trades Lucrativos"],
        "Resultado (%)": res["Resultado %"],
        "Drawdown (%)": res["Drawdown %"],
        "Fator Lucro": res["Fator Lucro"],
        "Ganho Médio (R$)": res["Ganho Médio"],
        "Perda Média (R$)": res["Perda Média"],
        "Capital Final (R$)": res["Capital Final"]
    } for res in melhores_resultados])
    
    # Ordenar por resultado percentual
    df_melhores = df_melhores.sort_values(by="Resultado (%)", ascending=False)
    
    # Salvar os resultados na sessão
    st.session_state.backtest_executado = True
    st.session_state.df_melhores = df_melhores
    st.session_state.melhores_resultados = melhores_resultados
    
    # Forçar reexecução para mostrar os resultados
    st.rerun()

# === FILTROS PARA RESULTADOS DO BACKTEST ===
if st.session_state.backtest_executado:
    # Criar container para filtros
    st.subheader("🔍 Filtrar Resultados do Backtest")
    
# Botão para resetar filtros
    col_reset, _ = st.columns([1, 5])
    with col_reset:
        if st.button("🔄 Resetar Filtros"):
            for key in list(st.session_state.keys()):
                if key.startswith("Filtro_"):
                    del st.session_state[key]
            st.rerun()

    # Criando quatro colunas para os filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        min_perc_lucrativos = st.slider(
            "% Trades Lucrativos (Mínimo)", 
            min_value=0, 
            max_value=100,
            value=st.session_state.get("Filtro_min_perc_lucrativos", 75),
            step=1,
            key="Filtro_min_perc_lucrativos"
        )

    with col2:
        max_drawdown = st.slider(
            "Drawdown Máximo (%)", 
            min_value=0, 
            max_value=30,
            value=st.session_state.get("Filtro_max_drawdown", 6),
            step=1,
            key="Filtro_max_drawdown"
        )

    with col3:
        min_resultado = st.slider(
            "Resultado Mínimo (%)", 
            min_value=00, 
            max_value=100,
            value=st.session_state.get("Filtro_min_resultado", 36),
            step=1,
            key="Filtro_min_resultado"
        )

    with col4:
        min_trades = st.slider(
            "Número Mínimo de Trades", 
            min_value=0, 
            max_value=60,
            value=st.session_state.get("Filtro_min_trades", 18),
            step=1,
            key="Filtro_min_trades"

        )

    col1, col2 = st.columns(2)

    with col1:
        min_fator_lucro = st.slider(
            "Fator de Lucro Mínimo", 
            min_value=0.0, 
            max_value=100.0,
            value=st.session_state.get("Filtro_min_fator_lucro", 2.5),
            step=0.5,
            key="Filtro_min_fator_lucro"
        )

    with col2:
        opcoes_ordenacao = [
            "Resultado (%) ↓", 
            "Lucro Total (R$) ↓", 
            "% Trades Lucrativos ↓", 
            "Drawdown (%) ↑", 
            "Fator Lucro ↓",
            "Trades ↓"
        ]

        ordenacao_escolhida = st.selectbox(
            "Ordenar resultados por:", 
            opcoes_ordenacao,
            index=0,
            key="Filtro_ordenacao_escolhida"
        )














    
    # Mapear opção de ordenação para coluna e direção
    mapeamento_ordenacao = {
        "Resultado (%) ↓": ("Resultado (%)", False),
        "Lucro Total (R$) ↓": ("Lucro Total (R$)", False),
        "% Trades Lucrativos ↓": ("% Trades Lucrativos", False),
        "Drawdown (%) ↑": ("Drawdown (%)", True),  # Ascending (menor é melhor)
        "Fator Lucro ↓": ("Fator Lucro", False),
        "Trades ↓": ("Trades", False)
    }
    
    # Aplicar filtros ao DataFrame
    df_filtrado_resultados = st.session_state.df_melhores[
        (st.session_state.df_melhores["% Trades Lucrativos"] >= min_perc_lucrativos) &
        (st.session_state.df_melhores["Drawdown (%)"] <= max_drawdown) &
        (st.session_state.df_melhores["Resultado (%)"] >= min_resultado) &
        (st.session_state.df_melhores["Trades"] >= min_trades) &
        (st.session_state.df_melhores["Fator Lucro"] >= min_fator_lucro)
    ]
    
    # Ordenar DataFrame com base na seleção do usuário
    col_ordenacao, ascendente = mapeamento_ordenacao[ordenacao_escolhida]
    df_filtrado_resultados = df_filtrado_resultados.sort_values(by=col_ordenacao, ascending=ascendente)
    
    # Exibir resultados filtrados
    st.subheader(f"📊 Resultados Filtrados - Lista: {lista_selecionada}")
    
    # Indicar o número de resultados
    num_resultados = len(df_filtrado_resultados)
    num_total = len(st.session_state.df_melhores)
    st.markdown(f"**Exibindo {num_resultados} de {num_total} ativos que atendem aos critérios de filtro**")
    
    if df_filtrado_resultados.empty:
        st.warning("Nenhum ativo atende aos critérios de filtro selecionados. Tente relaxar alguns filtros.")
    else:
        # Formatação para exibição
        st.dataframe(
            df_filtrado_resultados.style.format({
                "Lucro Total (R$)": "R$ {:.2f}",
                "% Trades Lucrativos": "{:.2f}%",
                "Resultado (%)": "{:.2f}%",
                "Drawdown (%)": "{:.2f}%",
                "Fator Lucro": "{:.2f}",
                "Ganho Médio (R$)": "R$ {:.2f}",
                "Perda Média (R$)": "R$ {:.2f}",
                "Capital Final (R$)": "R$ {:.2f}"
            })
        )
    
        # Estatísticas gerais dos resultados filtrados
        st.subheader("📈 Estatísticas dos Resultados Filtrados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total de Ativos Após Filtro", len(df_filtrado_resultados))
            st.metric("Média de Lucro", f"R$ {df_filtrado_resultados['Lucro Total (R$)'].mean():.2f}")
            st.metric("Média de Trades", f"{df_filtrado_resultados['Trades'].mean():.1f}")
        
        with col2:
            st.metric("Média de % Lucrativos", f"{df_filtrado_resultados['% Trades Lucrativos'].mean():.2f}%")
            st.metric("Média do Fator Lucro", f"{df_filtrado_resultados['Fator Lucro'].mean():.2f}")
            st.metric("Maior Retorno", f"{df_filtrado_resultados['Resultado (%)'].max():.2f}%")
        
        # Gráfico de barras dos lucros por ativo
        st.subheader("💰 Lucro Total por Ativo (Resultados Filtrados)")
        
        fig = go.Figure()
        df_plot = df_filtrado_resultados.sort_values(by="Lucro Total (R$)", ascending=False).head(30)
        
        # Cores baseadas no lucro (positivo=verde, negativo=vermelho)
        cores = ["mediumseagreen" if val >= 0 else "indianred" for val in df_plot["Lucro Total (R$)"]]
        
        fig.add_trace(go.Bar(
            x=df_plot["Ativo"],
            y=df_plot["Lucro Total (R$)"],
            marker_color=cores,
            text=[f"R$ {v:,.2f}" for v in df_plot["Lucro Total (R$)"]],
            textposition="auto"
        ))
        
        fig.update_layout(
            title="Lucro Total por Ativo (Resultados Filtrados)",
            xaxis_title="Ativo",
            yaxis_title="Lucro Total (R$)",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Opção para visualizar detalhes de cada ativo
        st.subheader("🔍 Detalhes por Ativo")
        
        ativo_selecionado_detalhes = st.selectbox(
            "Selecione um ativo para ver os detalhes", 
            options=df_filtrado_resultados["Ativo"].tolist()
        )
        
        # Encontrar o resultado detalhado do ativo selecionado
        resultado_detalhado = next((res for res in st.session_state.melhores_resultados if res["Ativo"] == ativo_selecionado_detalhes), None)
            
        if resultado_detalhado is not None:
            df_trades_detalhado = resultado_detalhado["df_trades"]
            # Verificar se o DataFrame tem registros
            if isinstance(df_trades_detalhado, pd.DataFrame) and len(df_trades_detalhado) > 0:
                st.markdown(f"### Trades do ativo {ativo_selecionado_detalhes} - IFR {resultado_detalhado['IFR']}")
                
                # DataFrame com os trades
                st.dataframe(
                    df_trades_detalhado.style.format({
                        "Preço Entrada": "R$ {:.2f}",
                        "Preço Saída": "R$ {:.2f}",
                        "Lucro": "R$ {:.2f}",
                        "Retorno R$": "R$ {:.2f}",
                        "Capital Acumulado": "R$ {:.2f}",
                        "IFR Entrada": "{:.0f}",
                        "Data Entrada": lambda x: x.strftime("%d-%m-%Y") if pd.notnull(x) else "",
                        "Data Saída": lambda x: x.strftime("%d-%m-%Y") if pd.notnull(x) else ""
                    })
                )
                
                # Curva de Capital
                st.subheader("📈 Curva de Capital")
                fig_cap = go.Figure()
                fig_cap.add_trace(go.Scatter(
                    x=df_trades_detalhado["Data Saída"],
                    y=df_trades_detalhado["Capital Acumulado"],
                    mode="lines+markers",
                    name="Capital"
                ))
                st.plotly_chart(fig_cap, use_container_width=True)
                
                # Retorno Mensal
                st.subheader("📆 Retorno Mensal (Não Acumulado)")
                
                df_trades_detalhado["Data Saída"] = pd.to_datetime(df_trades_detalhado["Data Saída"])
                df_trades_detalhado["AnoMes"] = df_trades_detalhado["Data Saída"].dt.to_period("M").astype(str)
                
                retorno_mensal = df_trades_detalhado.groupby("AnoMes")["Retorno R$"].sum().reset_index()
                retorno_mensal["Retorno R$"] = pd.to_numeric(retorno_mensal["Retorno R$"], errors="coerce")
                
                cores_mensal = ["mediumseagreen" if val >= 0 else "indianred" for val in retorno_mensal["Retorno R$"]]
                
                fig_bar = go.Figure(data=[
                    go.Bar(
                        x=retorno_mensal["AnoMes"],
                        y=retorno_mensal["Retorno R$"],
                        marker_color=cores_mensal,
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
            else:
                st.info("Não há operações registradas para este ativo com os parâmetros selecionados.")
        else:
            st.info("Não foi possível encontrar detalhes para este ativo.")
        
        # Oferecer opção para download do Excel
        st.subheader("📥 Exportar Resultados Filtrados")
    
        # Copiar o DataFrame sem as informações detalhadas que não precisam ir para o Excel
        df_export = df_filtrado_resultados.copy()
        df_export["Lista_Azul"] = df_export["Ativo"].astype(str) + ";" + df_export["IFR"].astype(str)

        # Gerar link para download do arquivo compacto
        st.markdown("#### 📄 Arquivo Compacto – Melhores IFRs por Ativo (Filtrados)")
        st.caption("Contém apenas o resumo dos melhores IFRs por ativo que atendem aos critérios de filtro.")
        st.markdown(
            get_excel_download_link(df_export, f"backtest_ifr_{lista_selecionada}_filtrados.xlsx"), 
            unsafe_allow_html=True
        )
        st.markdown("---")
        
        # Exportar todos os trades detalhados para ativos filtrados
        ativos_filtrados = set(df_filtrado_resultados["Ativo"].tolist())
        filtered_trades = []
        for res in st.session_state.melhores_resultados:
            if res["Ativo"] in ativos_filtrados and isinstance(res["df_trades"], pd.DataFrame) and len(res["df_trades"]) > 0:
                df_trades = res["df_trades"].copy()
                df_trades["Melhor IFR"] = res["IFR"]
                df_trades["Lista_Azul"] = df_trades["Ativo"].astype(str) + ";" + df_trades["Melhor IFR"].astype(str)
                filtered_trades.append(df_trades)

        if filtered_trades:
            df_filtered_trades = pd.concat(filtered_trades)
            
            st.markdown("#### 📄 Arquivo Completo – Operações Detalhadas (Ativos Filtrados)")
            st.caption("Contém todas as operações (trades) feitas com o melhor IFR dos ativos filtrados.")
            st.markdown(
                get_excel_download_link(df_filtered_trades, f"backtest_ifr_{lista_selecionada}_trades_detalhados_filtrados.xlsx"), 
                unsafe_allow_html=True
            )

# Se não executou backtest ainda, mostrar mensagem informativa
else:
    st.info("Selecione os parâmetros desejados e clique em 'Executar Backtest Múltiplo' para iniciar a análise. Depois você poderá filtrar os resultados.")