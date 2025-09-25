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
st.set_page_config(page_title="Backtest Setup IFR Múltiplo", layout="wide")

# Caminho dos dados
parquet_path = "01-dados/ativos_historicos.parquet"

st.title("📈 Backtest - Setup IFR - Múltiplos Ativos")

# Verifica se a base existe
if not os.path.exists(parquet_path):
    st.error("⚠ Base de dados não encontrada. Atualize a base antes de continuar.")
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
data_inicial_padrao = data_final_padrao - timedelta(days=1095)  # 3 anos como padrão

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
modo_otimizacao = st.sidebar.radio("Modo IFR:", ["Valor fixo", "Intervalo de valores"])
if modo_otimizacao == "Valor fixo":
    ifr_entrada = st.sidebar.slider(f"IFR({periodo_ifr}) abaixo de", min_value=1, max_value=50, value=10)
    intervalo_ifr = [ifr_entrada]
else:
    ifr_min = st.sidebar.slider(f"Valor mínimo do IFR({periodo_ifr})", min_value=1, max_value=49, value=5)
    ifr_max = st.sidebar.slider(f"Valor máximo do IFR({periodo_ifr})", min_value=2, max_value=50, value=30)
    intervalo_ifr = list(range(ifr_min, ifr_max + 1))
    st.sidebar.info(f"Testará {len(intervalo_ifr)} valores de IFR para cada ativo")

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

st.sidebar.header("🔧 Filtros Adicionais")
usar_filtro_volume = st.sidebar.checkbox("Filtrar por volume mínimo")
if usar_filtro_volume:
    volume_minimo = st.sidebar.number_input("Volume mínimo diário", value=1000000, step=100000)
else:
    volume_minimo = 0

# Logo na sidebar
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
            st.image(logo, width=50)
    
    with col_texto:
        st.markdown("""
        <div style='display: flex; align-items: center; height: 100%;'>
            <p style='margin: 0;'>Desenvolvido por Vladimir</p>
        </div>
        """, unsafe_allow_html=True)

# Função para criar um link de download para o DataFrame
def get_excel_download_link(df, filename="dados_backtest.xlsx"):
    try:
        output = BytesIO()
        # Tenta usar xlsxwriter primeiro
        try:
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
        except ImportError:
            # Se xlsxwriter não estiver disponível, usa openpyxl
            try:
                writer = pd.ExcelWriter(output, engine='openpyxl')
            except ImportError:
                # Se nenhum estiver disponível, retorna CSV
                csv_data = df.to_csv(index=False, encoding='utf-8')
                b64 = base64.b64encode(csv_data.encode()).decode()
                href = f'<a href="data:text/csv;base64,{b64}" download="{filename.replace(".xlsx", ".csv")}">📥 Baixar arquivo CSV</a>'
                return href
        
        df.to_excel(writer, sheet_name='Resultados', index=False)
        writer.close()
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">📥 Baixar arquivo Excel</a>'
        return href
    except Exception as e:
        # Em caso de erro, oferece download em CSV
        csv_data = df.to_csv(index=False, encoding='utf-8')
        b64 = base64.b64encode(csv_data.encode()).decode()
        href = f'<a href="data:text/csv;base64,{b64}" download="{filename.replace(".xlsx", ".csv")}">📥 Baixar arquivo CSV (Excel indisponível)</a>'
        return href

# Função para realizar o backtest em um ativo específico (OTIMIZAÇÃO IFR)
def backtest_ativo_ifr_otimizado(ativo, df_filtrado, data_inicial, data_final, 
                       periodo_ifr, intervalo_ifr, usar_media, media_periodos,
                       max_candles_saida, usar_timeout, max_hold_days, 
                       usar_stop, stop_pct, usar_filtro_volume, volume_minimo,
                       capital_inicial):
    
    melhores_resultados = []
    
    # Testa cada valor de IFR do intervalo
    for ifr_entrada in intervalo_ifr:
        # Filtra os dados do ativo escolhido
        df = df_filtrado[df_filtrado["Ticker"] == ativo].copy()
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        
        # Buffer expandido seguindo a lógica do arquivo original
        extra_ano = 365
        buffer_dias = max(media_periodos if usar_media else periodo_ifr, 10, extra_ano)
        
        data_inicial_expandida = pd.to_datetime(data_inicial) - timedelta(days=buffer_dias)
        df = df[(df["Date"] >= data_inicial_expandida) & (df["Date"] <= pd.to_datetime(data_final))]

        if df.empty or len(df) < buffer_dias:
            continue
                
        df.sort_values("Date", inplace=True)
        df.set_index("Date", inplace=True)

        # Calcula IFR usando EWM como no arquivo original
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
        df_analise = df[df.index >= pd.to_datetime(data_inicial)]
        
        if len(df_analise) <= max_candles_saida:
            continue
            
        posicao = False
        preco_entrada = 0
        data_entrada = None
        trades = []

        for i in range(max_candles_saida, len(df)):
            if df.index[i] < pd.to_datetime(data_inicial):
                continue
                
            hoje = df.iloc[i]

            # Filtro de volume se habilitado
            if usar_filtro_volume and hoje["Volume"] < volume_minimo:
                continue

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
                        "Ativo": ativo,
                        "Dias Hold": dias_hold
                    })
                    posicao = False

        # Calcula métricas para este valor de IFR
        if trades:
            df_trades = pd.DataFrame(trades)
            df_trades["Retorno R$"] = df_trades["Lucro"]
            df_trades["Capital Acumulado"] = capital_inicial + df_trades["Retorno R$"].cumsum()
            lucro_total = df_trades["Retorno R$"].sum()
            
            # Calcula estatísticas
            total_ops = len(df_trades)
            ganhos = df_trades[df_trades["Retorno R$"] > 0]["Retorno R$"]
            perdas = df_trades[df_trades["Retorno R$"] <= 0]["Retorno R$"]
            acertos = len(ganhos)
            perc_acertos = (acertos / total_ops * 100) if total_ops > 0 else 0
            resultado_perc = (df_trades["Capital Acumulado"].iloc[-1] - capital_inicial) / capital_inicial * 100
            ganho_medio = ganhos.mean() if not ganhos.empty else 0
            perda_media = perdas.mean() if not perdas.empty else 0
            capital = df_trades["Capital Acumulado"]
            
            # Drawdown
            running_max = capital.expanding().max()
            drawdown = capital - running_max
            max_drawdown = abs(drawdown.min())
            dd_perc = max_drawdown / running_max.max() * 100 if running_max.max() != 0 else 0
            
            fator_lucro = -ganhos.sum() / perdas.sum() if not perdas.empty and perdas.sum() != 0 else 0
            indice_ld = resultado_perc / dd_perc if dd_perc != 0 else 0
            
            # IFR médio de entrada
            ifr_medio_entrada = df_trades["IFR Entrada"].mean()
        else:
            lucro_total = 0
            perc_acertos = 0
            resultado_perc = 0
            ganho_medio = 0
            perda_media = 0
            dd_perc = 0
            fator_lucro = 0
            indice_ld = 0
            ifr_medio_entrada = 0
            df_trades = pd.DataFrame()

        melhores_resultados.append({
            "IFR": ifr_entrada,
            "Trades": len(trades),
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
            "IFR Médio Entrada": ifr_medio_entrada,
            "Ativo": ativo
        })
    
    # Retorna o melhor resultado baseado no Resultado %
    if melhores_resultados:
        melhor = max(melhores_resultados, key=lambda x: x["Resultado %"])
        return melhor
    else:
        return {
            "Ativo": ativo,
            "IFR": intervalo_ifr[0] if intervalo_ifr else 10,
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
            "Índice LD": 0,
            "IFR Médio Entrada": 0
        }

# === EXECUÇÃO DO BACKTEST ===
if 'backtest_ifr_executado' not in st.session_state:
    st.session_state.backtest_ifr_executado = False
    st.session_state.df_melhores_ifr = None
    st.session_state.melhores_resultados_ifr = None

if st.button("▶️ Executar Backtest Múltiplo Setup IFR"):
    if not ativos_escolhidos:
        st.warning("⚠️ Selecione pelo menos um ativo para continuar.")
        st.stop()
    
    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Lista para armazenar os resultados de cada ativo
    resultados = []
    
    # Total de ativos para calcular progresso
    total_ativos = len(ativos_escolhidos)
    
    # Executar backtest para cada ativo
    for idx, ativo in enumerate(ativos_escolhidos):
        status_text.text(f"Processando {ativo} ({idx+1}/{total_ativos})")
        
        # Executa o backtest para o ativo atual
        resultado = backtest_ativo_ifr_otimizado(
            ativo, df_filtrado, data_inicial, data_final,
            periodo_ifr, intervalo_ifr, usar_media, media_periodos,
            max_candles_saida, usar_timeout, max_hold_days,
            usar_stop, stop_pct, usar_filtro_volume, volume_minimo,
            capital_inicial
        )
        
        resultados.append(resultado)
        
        # Atualizar barra de progresso
        progress_bar.progress((idx + 1) / total_ativos)
    
    # Remover a barra de progresso e o status
    progress_bar.empty()
    status_text.empty()
    
    if not resultados:
        st.warning("⚠️ Nenhum resultado encontrado para os parâmetros selecionados.")
        st.stop()
    
    # Criar DataFrame com os resultados (incluindo IFR otimizado)
    df_melhores = pd.DataFrame([{
        "Ativo": res["Ativo"],
        "Melhor IFR": res["IFR"],
        "Trades": res["Trades"],
        "Lucro Total (R$)": res["Lucro Total"],
        "% Trades Lucrativos": res["% Trades Lucrativos"],
        "Resultado (%)": res["Resultado %"],
        "Drawdown (%)": res["Drawdown %"],
        "Fator Lucro": res["Fator Lucro"],
        "Ganho Médio (R$)": res["Ganho Médio"],
        "Perda Média (R$)": res["Perda Média"],
        "Índice LD": res["Índice LD"],
        "IFR Médio Entrada": res["IFR Médio Entrada"],
        "Capital Final (R$)": res["Capital Final"]
    } for res in resultados])
    
    # Ordenar por resultado percentual
    df_melhores = df_melhores.sort_values(by="Resultado (%)", ascending=False)
    
    # Salvar os resultados na sessão
    st.session_state.backtest_ifr_executado = True
    st.session_state.df_melhores_ifr = df_melhores
    st.session_state.melhores_resultados_ifr = resultados
    
    # Forçar reexecução para mostrar os resultados
    st.rerun()

# === FILTROS PARA RESULTADOS DO BACKTEST ===
if st.session_state.backtest_ifr_executado:
    # Criar container para filtros
    st.subheader("🔍 Filtrar Resultados do Backtest IFR")
    
    # Botão para resetar filtros
    col_reset, _ = st.columns([1, 5])
    with col_reset:
        if st.button("🔄 Resetar Filtros"):
            for key in list(st.session_state.keys()):
                if key.startswith("Filtro_IFR_"):
                    del st.session_state[key]
            st.rerun()

    # Criando quatro colunas para os filtros
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        min_perc_lucrativos = st.slider(
            "% Trades Lucrativos (Mínimo)", 
            min_value=0, 
            max_value=100,
            value=st.session_state.get("Filtro_IFR_min_perc_lucrativos", 60),
            step=1,
            key="Filtro_IFR_min_perc_lucrativos"
        )

    with col2:
        max_drawdown = st.slider(
            "Drawdown Máximo (%)", 
            min_value=0, 
            max_value=50,
            value=st.session_state.get("Filtro_IFR_max_drawdown", 20),
            step=1,
            key="Filtro_IFR_max_drawdown"
        )

    with col3:
        min_resultado = st.slider(
            "Resultado Mínimo (%)", 
            min_value=-50, 
            max_value=200,
            value=st.session_state.get("Filtro_IFR_min_resultado", 10),
            step=1,
            key="Filtro_IFR_min_resultado"
        )

    with col4:
        min_trades = st.slider(
            "Número Mínimo de Trades", 
            min_value=0, 
            max_value=50,
            value=st.session_state.get("Filtro_IFR_min_trades", 5),
            step=1,
            key="Filtro_IFR_min_trades"
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        min_fator_lucro = st.slider(
            "Fator de Lucro Mínimo", 
            min_value=0.0, 
            max_value=10.0,
            value=st.session_state.get("Filtro_IFR_min_fator_lucro", 1.2),
            step=0.1,
            key="Filtro_IFR_min_fator_lucro"
        )

    with col2:
        min_indice_ld = st.slider(
            "Índice LD Mínimo", 
            min_value=0.0, 
            max_value=10.0,
            value=st.session_state.get("Filtro_IFR_min_indice_ld", 0.5),
            step=0.1,
            key="Filtro_IFR_min_indice_ld"
        )

    with col3:
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
            key="Filtro_IFR_ordenacao_escolhida"
        )
    
    # Mapear opção de ordenação para coluna e direção
    mapeamento_ordenacao = {
        "Resultado (%) ↓": ("Resultado (%)", False),
        "Lucro Total (R$) ↓": ("Lucro Total (R$)", False),
        "% Trades Lucrativos ↓": ("% Trades Lucrativos", False),
        "Drawdown (%) ↑": ("Drawdown (%)", True),  # Ascending (menor é melhor)
        "Fator Lucro ↓": ("Fator Lucro", False),
        "Índice LD ↓": ("Índice LD", False),
        "Trades ↓": ("Trades", False)
    }
    
    # Aplicar filtros ao DataFrame
    df_filtrado_resultados = st.session_state.df_melhores_ifr[
        (st.session_state.df_melhores_ifr["% Trades Lucrativos"] >= min_perc_lucrativos) &
        (st.session_state.df_melhores_ifr["Drawdown (%)"] <= max_drawdown) &
        (st.session_state.df_melhores_ifr["Resultado (%)"] >= min_resultado) &
        (st.session_state.df_melhores_ifr["Trades"] >= min_trades) &
        (st.session_state.df_melhores_ifr["Fator Lucro"] >= min_fator_lucro) &
        (st.session_state.df_melhores_ifr["Índice LD"] >= min_indice_ld)
    ]
    
    # Ordenar DataFrame com base na seleção do usuário
    col_ordenacao, ascendente = mapeamento_ordenacao[ordenacao_escolhida]
    df_filtrado_resultados = df_filtrado_resultados.sort_values(by=col_ordenacao, ascending=ascendente)
    
    # Exibir resultados filtrados
    st.subheader(f"📊 Resultados Filtrados - Setup IFR - Lista: {lista_selecionada}")
    
    # Indicar o número de resultados
    num_resultados = len(df_filtrado_resultados)
    num_total = len(st.session_state.df_melhores_ifr)
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
                "Índice LD": "{:.2f}",
                "IFR Médio Entrada": "{:.1f}",
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
            st.metric("IFR Médio de Entrada", f"{df_filtrado_resultados['IFR Médio Entrada'].mean():.1f}")
        
        with col2:
            st.metric("Média de % Lucrativos", f"{df_filtrado_resultados['% Trades Lucrativos'].mean():.2f}%")
            st.metric("Média do Fator Lucro", f"{df_filtrado_resultados['Fator Lucro'].mean():.2f}")
            st.metric("Maior Retorno", f"{df_filtrado_resultados['Resultado (%)'].max():.2f}%")
            st.metric("Média Índice LD", f"{df_filtrado_resultados['Índice LD'].mean():.2f}")
        
        # Estatística específica do Setup IFR
        st.subheader("🎯 Estatísticas Setup IFR")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if modo_otimizacao == "Valor fixo":
                st.metric(f"IFR Configurado", ifr_entrada)
            else:
                ifr_medio_otimo = df_filtrado_resultados['Melhor IFR'].mean()
                st.metric(f"IFR Médio Otimizado", f"{ifr_medio_otimo:.1f}")
        
        with col2:
            media_status = "Ativo" if usar_media else "Inativo"
            st.metric(f"Filtro Média Móvel ({media_status})", f"MM{media_periodos}" if usar_media else "N/A")
        
        with col3:
            stop_status = f"{stop_pct}%" if usar_stop else "Inativo"
            st.metric("Stop Loss", stop_status)
        
        # Gráfico adicional: Distribuição dos IFRs otimizados (apenas se for modo intervalo)
        if modo_otimizacao == "Intervalo de valores" and not df_filtrado_resultados.empty:
            st.subheader("🎯 Distribuição dos IFRs Otimizados por Ativo")
            
            fig_ifr_dist = go.Figure()
            fig_ifr_dist.add_trace(go.Histogram(
                x=df_filtrado_resultados["Melhor IFR"],
                nbinsx=min(20, len(intervalo_ifr)),
                name="Frequência",
                opacity=0.7,
                marker_color="skyblue"
            ))
            
            fig_ifr_dist.update_layout(
                title="Distribuição dos Valores de IFR Otimizados",
                xaxis_title="Melhor IFR por Ativo",
                yaxis_title="Frequência",
                height=400
            )
            
            st.plotly_chart(fig_ifr_dist, use_container_width=True)
        
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
        
        # Gráfico de dispersão: Trades vs Resultado % (colorido por IFR otimizado)
        st.subheader("📊 Relação Trades x Resultado %")
        
        fig_scatter = go.Figure()
        
        # Usar cor baseada no IFR otimizado se modo intervalo, senão usar IFR médio de entrada
        if modo_otimizacao == "Intervalo de valores":
            color_column = df_filtrado_resultados["Melhor IFR"]
            color_title = "Melhor IFR<br>Otimizado"
            hover_ifr = "Melhor IFR: %{marker.color}<br>"
        else:
            color_column = df_filtrado_resultados["IFR Médio Entrada"]
            color_title = "IFR Médio<br>Entrada"
            hover_ifr = "IFR Médio: %{marker.color:.1f}<br>"
        
        fig_scatter.add_trace(go.Scatter(
            x=df_filtrado_resultados["Trades"],
            y=df_filtrado_resultados["Resultado (%)"],
            mode="markers",
            marker=dict(
                size=10,
                color=color_column,
                colorscale="RdYlBu_r",
                showscale=True,
                colorbar=dict(title=color_title)
            ),
            text=df_filtrado_resultados["Ativo"],
            hovertemplate="<b>%{text}</b><br>" +
                         "Trades: %{x}<br>" +
                         "Resultado: %{y:.2f}%<br>" +
                         hover_ifr + "<extra></extra>"
        ))
        
        fig_scatter.update_layout(
            title="Relação entre Número de Trades e Resultado %",
            xaxis_title="Número de Trades",
            yaxis_title="Resultado (%)",
            height=500
        )
        
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Gráfico do IFR médio de entrada
        st.subheader("📉 Distribuição do IFR Médio de Entrada")
        
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=df_filtrado_resultados["IFR Médio Entrada"],
            nbinsx=20,
            name="Frequência",
            opacity=0.7,
            marker_color="lightblue"
        ))
        
        # Adicionar linha vertical no IFR configurado (se modo fixo)
        if modo_otimizacao == "Valor fixo":
            fig_hist.add_vline(
                x=ifr_entrada, 
                line_dash="dash", 
                line_color="red",
                annotation_text=f"IFR Limite: {ifr_entrada}"
            )
        
        fig_hist.update_layout(
            title="Distribuição do IFR Médio de Entrada dos Trades",
            xaxis_title="IFR Médio de Entrada",
            yaxis_title="Frequência",
            height=400
        )
        
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Opção para visualizar detalhes de cada ativo
        st.subheader("🔍 Detalhes por Ativo")
        
        ativo_selecionado_detalhes = st.selectbox(
            "Selecione um ativo para ver os detalhes", 
            options=df_filtrado_resultados["Ativo"].tolist()
        )
        
        # Encontrar o resultado detalhado do ativo selecionado
        resultado_detalhado = next((res for res in st.session_state.melhores_resultados_ifr if res["Ativo"] == ativo_selecionado_detalhes), None)
            
        if resultado_detalhado is not None:
            df_trades_raw = resultado_detalhado["df_trades"]
            
            if isinstance(df_trades_raw, pd.DataFrame) and len(df_trades_raw) > 0:
                df_trades = df_trades_raw.copy()

                st.markdown(f"### Trades do ativo - {ativo_selecionado_detalhes}")
                
                # Informações gerais do ativo (incluindo IFR otimizado)
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Trades Executados", len(df_trades))
                with col2:
                    lucro_total_ativo = df_trades["Lucro"].sum()
                    st.metric("Lucro Total", f"R$ {lucro_total_ativo:.2f}")
                with col3:
                    ops_lucrativas = (df_trades["Lucro"] > 0).sum()
                    perc_lucrativos = (ops_lucrativas / len(df_trades)) * 100
                    st.metric("% Lucrativos", f"{perc_lucrativos:.1f}%")
                with col4:
                    melhor_ifr = resultado_detalhado["IFR"]
                    st.metric("Melhor IFR Otimizado", melhor_ifr)
                
                # Segunda linha de métricas
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    ifr_medio_ativo = df_trades["IFR Entrada"].mean()
                    st.metric("IFR Médio Entrada", f"{ifr_medio_ativo:.1f}")
                with col2:
                    resultado_perc = resultado_detalhado["Resultado %"]
                    st.metric("Resultado %", f"{resultado_perc:.2f}%")
                with col3:
                    drawdown = resultado_detalhado["Drawdown %"]
                    st.metric("Drawdown %", f"{drawdown:.2f}%")
                with col4:
                    fator_lucro = resultado_detalhado["Fator Lucro"]
                    st.metric("Fator Lucro", f"{fator_lucro:.2f}")
                
                # DataFrame com os trades (aplicando formatação)
                df_trades_display = df_trades.copy()
                df_trades_display["Data Entrada"] = df_trades_display["Data Entrada"].dt.strftime("%d/%m/%Y")
                df_trades_display["Data Saída"] = df_trades_display["Data Saída"].dt.strftime("%d/%m/%Y")
                df_trades_display["Retorno %"] = (df_trades_display["Lucro"] / (df_trades_display["Preço Entrada"] * df_trades_display["Quantidade"])) * 100
                
                st.dataframe(
                    df_trades_display.style.format({
                        "Preço Entrada": "R$ {:.2f}",
                        "Preço Saída": "R$ {:.2f}",
                        "Lucro": "R$ {:.2f}",
                        "Retorno %": "{:.2f}%",
                        "IFR Entrada": "{:.1f}"
                    })
                )
                
                # Curva de Capital
                st.markdown(f"### 📈 Evolução do Capital - {ativo_selecionado_detalhes}")
                fig_cap = go.Figure()
                
                # Preparar dados para o gráfico
                df_trades_ordenado = df_trades.copy()
                df_trades_ordenado = df_trades_ordenado.sort_values("Data Saída")
                df_trades_ordenado["Capital Acumulado Correto"] = capital_inicial + df_trades_ordenado["Lucro"].cumsum()
                
                datas_plot = [pd.to_datetime(data_inicial)] + df_trades_ordenado["Data Saída"].tolist()
                capital_plot = [capital_inicial] + df_trades_ordenado["Capital Acumulado Correto"].tolist()
                
                fig_cap.add_trace(go.Scatter(
                    x=datas_plot,
                    y=capital_plot,
                    mode="lines+markers",
                    name="Capital Acumulado",
                    line=dict(width=2),
                    marker=dict(size=8),
                    hovertemplate="<b>Data:</b> %{x}<br><b>Capital:</b> R$ %{y:,.2f}<extra></extra>"
                ))
                
                fig_cap.add_hline(y=capital_inicial, line_dash="dash", line_color="gray", 
                                  annotation_text=f"Capital Inicial: R$ {capital_inicial:,.2f}")
                
                fig_cap.update_layout(
                    title="Evolução do Capital ao Longo do Tempo",
                    xaxis_title="Data",
                    yaxis_title="Capital (R$)",
                    hovermode="x unified",
                    height=500,
                    showlegend=True
                )
                
                st.plotly_chart(fig_cap, use_container_width=True)
                
                # Distribuição dos IFRs de entrada
                st.markdown(f"### 📉 Distribuição dos IFRs de Entrada - {ativo_selecionado_detalhes}")
                fig_ifr = go.Figure()
                fig_ifr.add_trace(go.Histogram(
                    x=df_trades["IFR Entrada"],
                    nbinsx=15,
                    name="Frequência",
                    opacity=0.7,
                    marker_color="lightcoral"
                ))
                
                # Linha do melhor IFR otimizado
                fig_ifr.add_vline(
                    x=melhor_ifr, 
                    line_dash="dash", 
                    line_color="red",
                    annotation_text=f"Melhor IFR: {melhor_ifr}"
                )
                
                fig_ifr.update_layout(
                    title="Distribuição dos Valores de IFR nas Entradas",
                    xaxis_title="IFR na Entrada",
                    yaxis_title="Frequência"
                )
                
                st.plotly_chart(fig_ifr, use_container_width=True)
                
                # Análise por motivo de saída
                st.markdown(f"### 🎯 Análise por Motivo de Saída - {ativo_selecionado_detalhes}")
                motivos_resumo = df_trades.groupby("Motivo").agg({
                    "Lucro": ["count", "sum", "mean"],
                    "IFR Entrada": "mean",
                    "Dias Hold": "mean"
                }).round(2)
                
                motivos_resumo.columns = ["Quantidade", "Lucro Total", "Lucro Médio", "IFR Médio", "Dias Hold Médio"]
                st.dataframe(motivos_resumo.style.format({
                    "Lucro Total": "R$ {:.2f}",
                    "Lucro Médio": "R$ {:.2f}",
                    "IFR Médio": "{:.1f}",
                    "Dias Hold Médio": "{:.1f}"
                }))
                
                # Retorno Mensal
                st.markdown(f"### 📅 Retorno Mensal (Não Acumulado) - {ativo_selecionado_detalhes}")
                
                df_trades["AnoMes"] = df_trades["Data Saída"].dt.to_period("M").astype(str)
                retorno_mensal = df_trades.groupby("AnoMes")["Lucro"].sum().reset_index()
                cores_mensal = ["mediumseagreen" if val >= 0 else "indianred" for val in retorno_mensal["Lucro"]]
                
                fig_bar = go.Figure(data=[
                    go.Bar(
                        x=retorno_mensal["AnoMes"],
                        y=retorno_mensal["Lucro"],
                        marker_color=cores_mensal,
                        text=[f"R$ {v:,.0f}" for v in retorno_mensal["Lucro"]],
                        textposition="outside",
                    )
                ])

                fig_bar.update_layout(
                    title="Retorno Mensal (Não Acumulado)",
                    xaxis_title="Mês",
                    yaxis_title="Retorno (R$)",
                    showlegend=False
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
        df_export["Lista_Azul"] = df_export["Ativo"].astype(str) + ";SetupIFR"

        # Gerar link para download do arquivo compacto
        st.markdown("#### 📄 Arquivo Compacto – Resultados Setup IFR por Ativo (Filtrados)")
        st.caption("Contém apenas o resumo dos resultados do Setup IFR por ativo que atendem aos critérios de filtro.")
        st.markdown(
            get_excel_download_link(df_export, f"backtest_setupIFR_{lista_selecionada}_filtrados.xlsx"), 
            unsafe_allow_html=True
        )
        st.markdown("---")
        
        # Exportar todos os trades detalhados para ativos filtrados
        ativos_filtrados = set(df_filtrado_resultados["Ativo"].tolist())
        filtered_trades = []
        for res in st.session_state.melhores_resultados_ifr:
            if res["Ativo"] in ativos_filtrados and isinstance(res["df_trades"], pd.DataFrame) and len(res["df_trades"]) > 0:
                df_trades = res["df_trades"].copy()
                df_trades["Setup"] = "SetupIFR"
                df_trades["Lista_Azul"] = df_trades["Ativo"].astype(str) + ";SetupIFR"
                df_trades["Melhor_IFR_Otimizado"] = res["IFR"]  # Adiciona o IFR otimizado
                
                # Formatar datas para exportação
                df_trades["Data Entrada"] = df_trades["Data Entrada"].dt.strftime("%d/%m/%Y")
                df_trades["Data Saída"] = df_trades["Data Saída"].dt.strftime("%d/%m/%Y")
                df_trades["Retorno %"] = (df_trades["Lucro"] / (df_trades["Preço Entrada"] * df_trades["Quantidade"])) * 100
                
                filtered_trades.append(df_trades)

        if filtered_trades:
            df_filtered_trades = pd.concat(filtered_trades, ignore_index=True)
            
            st.markdown("#### 📄 Arquivo Completo – Operações Detalhadas Setup IFR (Ativos Filtrados)")
            st.caption("Contém todas as operações (trades) feitas com o Setup IFR dos ativos filtrados, incluindo o IFR otimizado.")
            st.markdown(
                get_excel_download_link(df_filtered_trades, f"backtest_setupIFR_{lista_selecionada}_trades_detalhados_filtrados.xlsx"), 
                unsafe_allow_html=True
            )

# Se não executou backtest ainda, mostrar mensagem informativa
else:
    st.info("Selecione os parâmetros desejados e clique em 'Executar Backtest Múltiplo Setup IFR' para iniciar a análise. Depois você poderá filtrar os resultados.")
    
    # Mostrar resumo das configurações atuais
    st.subheader("⚙️ Configurações Atuais do Setup IFR")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if modo_otimizacao == "Valor fixo":
            ifr_info = f"IFR({periodo_ifr}) < {ifr_entrada}"
        else:
            ifr_info = f"IFR({periodo_ifr}) otimizado entre {ifr_min} e {ifr_max}"
            
        st.markdown(f"""
        **Setup Básico:**
        - Lista: {lista_selecionada}
        - Ativos: {len(ativos_escolhidos) if ativos_escolhidos else 0} selecionados
        - Período: {data_inicial} a {data_final}
        - Capital: R$ {capital_inicial:,.2f}
        - {ifr_info}
        """)
    
    with col2:
        media_status = "✅ Ativo" if usar_media else "❌ Inativo"
        stop_status = "✅ Ativo" if usar_stop else "❌ Inativo"
        timeout_status = "✅ Ativo" if usar_timeout else "❌ Inativo"
        volume_status = "✅ Ativo" if usar_filtro_volume else "❌ Inativo"
        
        st.markdown(f"""
        **Filtros e Gestão:**
        - Média Móvel: {media_status}
        - Stop Loss: {stop_status}
        - Timeout: {timeout_status}
        - Filtro Volume: {volume_status}
        - Saída na máxima de {max_candles_saida} candles
        """)
    
    if modo_otimizacao == "Intervalo de valores":
        st.info(f"🔍 Modo Otimização: O sistema testará {len(intervalo_ifr)} valores de IFR para cada ativo e escolherá o que der melhor Resultado %")
    
    if usar_media:
        st.info(f"📊 Filtro de Média Móvel configurado: MM{media_periodos}")
    
    if usar_timeout and max_hold_days:
        st.info(f"⏰ Saída forçada configurada para {max_hold_days} candles")
    
    if usar_stop and stop_pct:
        st.info(f"🛑 Stop Loss configurado em {stop_pct}% abaixo do preço de entrada")