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
data_inicial_padrao = data_final_padrao - timedelta(days=730)

st.sidebar.header("📅 Período do Backtest")
# Opções de período rápido
periodo_rapido = st.sidebar.selectbox(
    "Selecione o período:",
    ["Personalizado", "1 ano", "2 anos", "3 anos", "5 anos", "10 anos"],
    index=0
)

# Calcula datas conforme escolha
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

    st.sidebar.write(
        f"📅 Período: {data_inicial_calc.strftime('%d/%m/%Y')} a {data_final_padrao.strftime('%d/%m/%Y')}"
    )

    data_inicial = st.sidebar.date_input("Data inicial", value=data_inicial_calc)
    data_final = st.sidebar.date_input("Data final", value=data_final_padrao)
else:
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
        
        extra_ano = 365
        buffer_dias = max(media_periodos if usar_media else periodo_ifr, 10, extra_ano)
        
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
                "Perda Média": perda_media,
                "Índice LD": indice_ld
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
                "Perda Média": 0,
                "Índice LD": 0
            })
    
    df_result = pd.DataFrame(resultados)

    if not df_result.empty and "Lucro Total" in df_result.columns:
        df_result = df_result.sort_values(by="Lucro Total", ascending=False)
        melhor = df_result.iloc[0].to_dict()
        return melhor
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
            "Perda Média": 0,
            "Índice LD": 0
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
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    from io import BytesIO
    
    melhores_resultados = []
    total_ativos = len(ativos_escolhidos)
    
    for idx, ativo in enumerate(ativos_escolhidos):
        status_text.text(f"Processando {ativo} ({idx+1}/{total_ativos})")
        
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
        
        progress_bar.progress((idx + 1) / total_ativos)
    
    progress_bar.empty()
    status_text.empty()
    
    if not melhores_resultados:
        st.warning("⚠️ Nenhum resultado encontrado para os parâmetros selecionados.")
        st.stop()
    
    df_melhores = pd.DataFrame([{
        "Ativo": res["Ativo"],
        "IFR": res["IFR"],
        "Trades": res["Trades"],
        "Lucro Total (R$)": res["Lucro Total"],
        "% Trades Lucrativos": res["% Trades Lucrativos"],
        "Resultado (%)": res["Resultado %"],
        "Drawdown (%)": res["Drawdown %"],
        "Fator Lucro": res["Fator Lucro"],
        "Índice LD": res["Índice LD"],
        "Ganho Médio (R$)": res["Ganho Médio"],
        "Perda Média (R$)": res["Perda Média"],
        "Capital Final (R$)": res["Capital Final"]
    } for res in melhores_resultados])
    
    df_melhores = df_melhores.sort_values(by="Resultado (%)", ascending=False)
    
    st.session_state.backtest_executado = True
    st.session_state.df_melhores = df_melhores
    st.session_state.melhores_resultados = melhores_resultados
    
    st.rerun()

# === FILTROS PARA RESULTADOS DO BACKTEST ===
if st.session_state.backtest_executado:
    st.subheader("🔍 Filtrar Resultados do Backtest")
    
    col_reset, _ = st.columns([1, 5])
    with col_reset:
        if st.button("🔄 Resetar Filtros"):
            for key in list(st.session_state.keys()):
                if key.startswith("Filtro_"):
                    del st.session_state[key]
            st.rerun()

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
            min_value=0, 
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
        min_indice_ld = st.slider(
            "Índice LD Mínimo", 
            min_value=0.0, 
            max_value=50.0,
            value=st.session_state.get("Filtro_min_indice_ld", 2.0),
            step=0.5,
            key="Filtro_min_indice_ld"
        )

    opcoes_ordenacao = [
        "Resultado (%) ↓", 
        "Lucro Total (R$) ↓", 
        "% Trades Lucrativos ↓", 
        "Drawdown (%) ↑", 
        "Fator Lucro ↓",
        "Índice LD ↓",
        "Trades ↓"
    ]

    ordenacao_escolhida = st.selectbox(
        "Ordenar resultados por:", 
        opcoes_ordenacao,
        index=0,
        key="Filtro_ordenacao_escolhida"
    )

    mapeamento_ordenacao = {
        "Resultado (%) ↓": ("Resultado (%)", False),
        "Lucro Total (R$) ↓": ("Lucro Total (R$)", False),
        "% Trades Lucrativos ↓": ("% Trades Lucrativos", False),
        "Drawdown (%) ↑": ("Drawdown (%)", True),
        "Fator Lucro ↓": ("Fator Lucro", False),
        "Índice LD ↓": ("Índice LD", False),
        "Trades ↓": ("Trades", False)
    }
    
    df_filtrado_resultados = st.session_state.df_melhores[
        (st.session_state.df_melhores["% Trades Lucrativos"] >= min_perc_lucrativos) &
        (st.session_state.df_melhores["Drawdown (%)"] <= max_drawdown) &
        (st.session_state.df_melhores["Resultado (%)"] >= min_resultado) &
        (st.session_state.df_melhores["Trades"] >= min_trades) &
        (st.session_state.df_melhores["Fator Lucro"] >= min_fator_lucro) &
        (st.session_state.df_melhores["Índice LD"] >= min_indice_ld)
    ]
    
    col_ordenacao, ascendente = mapeamento_ordenacao[ordenacao_escolhida]
    df_filtrado_resultados = df_filtrado_resultados.sort_values(by=col_ordenacao, ascending=ascendente)
    
    st.subheader(f"📊 Resultados Filtrados - Lista: {lista_selecionada}")
    
    num_resultados = len(df_filtrado_resultados)
    num_total = len(st.session_state.df_melhores)
    st.markdown(f"**Exibindo {num_resultados} de {num_total} ativos que atendem aos critérios de filtro**")
    
    if df_filtrado_resultados.empty:
        st.warning("Nenhum ativo atende aos critérios de filtro selecionados. Tente relaxar alguns filtros.")
    else:
        st.dataframe(
            df_filtrado_resultados.style.format({
                "Lucro Total (R$)": "R$ {:.2f}",
                "% Trades Lucrativos": "{:.2f}%",
                "Resultado (%)": "{:.2f}%",
                "Drawdown (%)": "{:.2f}%",
                "Fator Lucro": "{:.2f}",
                "Índice LD": "{:.2f}",
                "Ganho Médio (R$)": "R$ {:.2f}",
                "Perda Média (R$)": "R$ {:.2f}",
                "Capital Final (R$)": "R$ {:.2f}"
            })
        )
