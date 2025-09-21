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
st.set_page_config(page_title="Backtest Setup 123 Múltiplo", layout="wide")

# Caminho dos dados
parquet_path = "01-dados/ativos_historicos.parquet"

st.title("📈 Backtest - Setup 123 - Múltiplos Ativos")

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
data_inicial_padrao = data_final_padrao - timedelta(days=730)

st.sidebar.header("📅 Período do Backtest")
data_inicial = st.sidebar.date_input("Data inicial", value=data_inicial_padrao)
data_final = st.sidebar.date_input("Data final", value=data_final_padrao)

st.sidebar.header("💰 Capital Inicial")
capital_inicial = st.sidebar.number_input("Capital disponível (R$)", value=100000.0, step=10000.0)

st.sidebar.header("📈 Setup 123 - Configurações")
st.sidebar.markdown("**Formação 123:** Fundo com 3 candles - 2º candle tem menor mínima")

posicao_stop = st.sidebar.radio(
    "Posição do Stop Loss:",
    ["Mínima do penúltimo candle (padrão)", "Mínima do último candle"]
)

# SEÇÃO ÉDEN DOS TRADES E MÉDIAS MÓVEIS
st.sidebar.header("🌟 Éden dos Trades")
eden_trades = st.sidebar.checkbox(
    "Ativar Filtro Éden dos Trades", 
    value=False,
    help="Só permite trades se entrada for acima das MMEs selecionadas"
)

# Controles das médias móveis SEMPRE visíveis
st.sidebar.markdown("**Configuração das Médias Móveis:**")
mme_curta = st.sidebar.number_input("MME Curta", min_value=1, max_value=50, value=8, key="mme_curta")
mme_longa = st.sidebar.number_input("MME Longa", min_value=10, max_value=200, value=80, key="mme_longa")

if eden_trades:
    st.sidebar.success(f"✅ Filtro ativo: Entrada > MME({mme_curta}) E MME({mme_longa})")
else:
    st.sidebar.info(f"ℹ️ MMEs configuradas: {mme_curta} e {mme_longa} (filtro inativo)")

st.sidebar.header("🔧 Filtros Adicionais")
usar_filtro_volume = st.sidebar.checkbox("Filtrar por volume mínimo")
if usar_filtro_volume:
    volume_minimo = st.sidebar.number_input("Volume mínimo diário", value=1000000, step=100000)
else:
    volume_minimo = 0

usar_filtro_gap = st.sidebar.checkbox("Ignorar gaps > 2%")
gap_maximo = 2.0 if usar_filtro_gap else 100.0

st.sidebar.header("⚙️ Gestão de Risco")
usar_timeout = st.sidebar.checkbox("Saída forçada por tempo")
if usar_timeout:
    max_hold_days = st.sidebar.number_input("Máximo de candles em posição", min_value=1, max_value=30, value=10)
else:
    max_hold_days = None

usar_trailing_stop = st.sidebar.checkbox("Trailing Stop")
if usar_trailing_stop:
    trailing_pct = st.sidebar.number_input("Trailing Stop (%)", min_value=1.0, max_value=20.0, value=5.0)
else:
    trailing_pct = None

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

# Função para realizar o backtest em um ativo específico
def backtest_ativo_123(ativo, df_filtrado, data_inicial, data_final, 
                       posicao_stop, eden_trades, mme_curta, mme_longa,
                       usar_filtro_volume, volume_minimo, usar_filtro_gap, gap_maximo,
                       usar_timeout, max_hold_days, usar_trailing_stop, trailing_pct,
                       capital_inicial):
    
    df = df_filtrado[df_filtrado["Ticker"] == ativo].copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    df = df[(df["Date"] >= pd.to_datetime(data_inicial)) & (df["Date"] <= pd.to_datetime(data_final))]
    df.sort_values("Date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    min_candles = 90 if eden_trades else 10
    if len(df) < min_candles:
        return {
            "Ativo": ativo, "Trades": 0, "Lucro Total": 0,
            "% Trades Lucrativos": 0, "Capital Final": capital_inicial,
            "df_trades": pd.DataFrame(), "Lista": lista_selecionada,
            "Resultado %": 0, "Drawdown %": 0, "Fator Lucro": 0,
            "Ganho Médio": 0, "Perda Média": 0, "Padrões Encontrados": 0,
            "Trades Filtrados Éden": 0
        }
    
    # Médias móveis
    df[f'MME_{mme_curta}'] = df['Close'].ewm(span=mme_curta).mean()
    df[f'MME_{mme_longa}'] = df['Close'].ewm(span=mme_longa).mean()
    
    # Identificação do setup 123
    setup_123 = []
    for i in range(2, len(df)):
        c1, c2, c3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
        if usar_filtro_volume and c3["Volume"] < volume_minimo:
            continue
        if c2["Low"] < c1["Low"] and c2["Low"] < c3["Low"]:
            stop_loss_setup = c2["Low"] if posicao_stop == "Mínima do penúltimo candle (padrão)" else c3["Low"]
            setup_123.append({
                'index': i,
                'data': c3["Date"],
                'entrada_target': c3["High"],
                'stop_loss': stop_loss_setup,
                'padrao_tipo': 'Fundo 123'
            })
    
    padroes_encontrados = len(setup_123)
    if not setup_123:
        return {
            "Ativo": ativo, "Trades": 0, "Lucro Total": 0,
            "% Trades Lucrativos": 0, "Capital Final": capital_inicial,
            "df_trades": pd.DataFrame(), "Lista": lista_selecionada,
            "Resultado %": 0, "Drawdown %": 0, "Fator Lucro": 0,
            "Ganho Médio": 0, "Perda Média": 0,
            "Padrões Encontrados": 0, "Trades Filtrados Éden": 0
        }
    
    posicao_ativa = False
    trades, trades_filtrados_eden = [], 0
    
    for setup in setup_123:
        if posicao_ativa:
            continue
        
        entrada_target, stop_loss = setup['entrada_target'], setup['stop_loss']
        
        # Entrada somente no próximo candle
        if setup['index'] + 1 >= len(df):
            continue
        candle_atual = df.iloc[setup['index'] + 1]
        
        # Filtro de gap
        if usar_filtro_gap:
            candle_anterior = df.iloc[setup['index']]
            gap_pct = abs(candle_atual["Open"] - candle_anterior["Close"]) / candle_anterior["Close"] * 100
            if gap_pct > gap_maximo:
                continue
        
        # Verifica se rompeu a máxima
        if candle_atual["High"] >= entrada_target:
            preco_entrada = candle_atual["Open"] if candle_atual["Open"] >= entrada_target else entrada_target
            
            # Filtro Éden
            if eden_trades:
                mme_curta_atual = candle_atual.get(f"MME_{mme_curta}", 0)
                mme_longa_atual = candle_atual.get(f"MME_{mme_longa}", 0)
                if preco_entrada <= mme_curta_atual or preco_entrada <= mme_longa_atual:
                    trades_filtrados_eden += 1
                    continue
            
            quantidade = int((capital_inicial // preco_entrada) // 100) * 100
            if quantidade == 0:
                continue
            
            risco_real = preco_entrada - stop_loss
            take_profit_real = preco_entrada + (2 * risco_real)
            
            posicao_ativa = True
            data_entrada = candle_atual["Date"]
            dias_hold, max_preco = 0, preco_entrada
            
            for k in range(setup['index'] + 1, len(df)):
                candle_pos = df.iloc[k]
                dias_hold += 1
                
                if usar_trailing_stop:
                    max_preco = max(max_preco, candle_pos["High"])
                    trailing_stop_price = max_preco * (1 - trailing_pct / 100)
                    stop_atual = max(stop_loss, trailing_stop_price)
                else:
                    stop_atual = stop_loss
                
                sair, preco_saida, motivo = False, None, ""
                if candle_pos["Low"] <= stop_atual:
                    sair, preco_saida, motivo = True, min(candle_pos["Open"], stop_atual), "Stop Loss"
                elif candle_pos["High"] >= take_profit_real:
                    sair, preco_saida, motivo = True, (candle_pos["Open"] if candle_pos["Open"] >= take_profit_real else take_profit_real), "Take Profit"
                elif usar_timeout and max_hold_days and dias_hold >= max_hold_days:
                    sair, preco_saida, motivo = True, candle_pos["Close"], "Timeout"
                
                if sair:
                    lucro = (preco_saida - preco_entrada) * quantidade
                    retorno_pct = (preco_saida - preco_entrada) / preco_entrada * 100
                    trade_data = {
                        "Setup Data": setup['data'].strftime("%d/%m/%Y"),
                        "Data Entrada": data_entrada.strftime("%d/%m/%Y"), 
                        "Preço Entrada": preco_entrada,
                        "Data Saída": candle_pos["Date"].strftime("%d/%m/%Y"),
                        "Preço Saída": preco_saida,
                        "Stop Loss": stop_loss,
                        "Take Profit": take_profit_real,
                        "Dias Hold": dias_hold,
                        "Quantidade": quantidade,
                        "Lucro": lucro,
                        "Retorno %": retorno_pct,
                        "Motivo": motivo,
                        "Risco/Recompensa": "1:2.0",
                        "Lista": lista_selecionada,
                        "Padrão": setup['padrao_tipo'],
                        "Ativo": ativo,
                        "Éden Ativo": "Sim" if eden_trades else "Não"
                    }
                    trades.append(trade_data)
                    posicao_ativa = False
                    break
    
    # Análise dos resultados
    if not trades:
        return {
            "Ativo": ativo,
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
            "Padrões Encontrados": padroes_encontrados,
            "Trades Filtrados Éden": trades_filtrados_eden
        }
    
    df_trades = pd.DataFrame(trades)
    df_trades["Capital Acumulado"] = capital_inicial + df_trades["Lucro"].cumsum()
    
    # Estatísticas
    total_ops = len(df_trades)
    ops_lucrativas = (df_trades["Lucro"] > 0).sum()
    perc_acertos = (ops_lucrativas / total_ops * 100) if total_ops > 0 else 0
    lucro_total = df_trades["Lucro"].sum()
    resultado_pct = (lucro_total / capital_inicial) * 100
    
    ganhos = df_trades[df_trades["Lucro"] > 0]["Lucro"]
    perdas = df_trades[df_trades["Lucro"] <= 0]["Lucro"]
    ganho_medio = ganhos.mean() if not ganhos.empty else 0
    perda_media = perdas.mean() if not perdas.empty else 0
    
    # Drawdown
    capital_curve = df_trades["Capital Acumulado"].tolist()
    capital_curve.insert(0, capital_inicial)
    running_max = np.maximum.accumulate(capital_curve)
    drawdown = np.array(capital_curve) - running_max
    max_drawdown = abs(min(drawdown))
    max_dd_pct = (max_drawdown / max(running_max)) * 100 if max(running_max) > 0 else 0
    
    # Fator de lucro
    fator_lucro = -ganhos.sum() / perdas.sum() if not perdas.empty and perdas.sum() != 0 else 0
    
    return {
        "Ativo": ativo,
        "Trades": total_ops,
        "Lucro Total": lucro_total,
        "% Trades Lucrativos": perc_acertos,
        "Capital Final": capital_inicial + lucro_total,
        "df_trades": df_trades,
        "Lista": lista_selecionada,
        "Resultado %": resultado_pct,
        "Drawdown %": max_dd_pct,
        "Fator Lucro": fator_lucro,
        "Ganho Médio": ganho_medio,
        "Perda Média": perda_media,
        "Padrões Encontrados": padroes_encontrados,
        "Trades Filtrados Éden": trades_filtrados_eden
    }

# === EXECUÇÃO DO BACKTEST ===
if 'backtest_executado' not in st.session_state:
    st.session_state.backtest_executado = False
    st.session_state.df_melhores = None
    st.session_state.melhores_resultados = None

if st.button("▶️ Executar Backtest Múltiplo Setup 123"):
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
        resultado = backtest_ativo_123(
            ativo, df_filtrado, data_inicial, data_final,
            posicao_stop, eden_trades, mme_curta, mme_longa,
            usar_filtro_volume, volume_minimo, usar_filtro_gap, gap_maximo,
            usar_timeout, max_hold_days, usar_trailing_stop, trailing_pct,
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
    
    # Criar DataFrame com os resultados
    df_melhores = pd.DataFrame([{
        "Ativo": res["Ativo"],
        "Trades": res["Trades"],
        "Padrões Encontrados": res["Padrões Encontrados"],
        "Trades Filtrados Éden": res["Trades Filtrados Éden"],
        "Lucro Total (R$)": res["Lucro Total"],
        "% Trades Lucrativos": res["% Trades Lucrativos"],
        "Resultado (%)": res["Resultado %"],
        "Drawdown (%)": res["Drawdown %"],
        "Fator Lucro": res["Fator Lucro"],
        "Ganho Médio (R$)": res["Ganho Médio"],
        "Perda Média (R$)": res["Perda Média"],
        "Capital Final (R$)": res["Capital Final"]
    } for res in resultados])
    
    # Ordenar por resultado percentual
    df_melhores = df_melhores.sort_values(by="Resultado (%)", ascending=False)
    
    # Salvar os resultados na sessão
    st.session_state.backtest_executado = True
    st.session_state.df_melhores = df_melhores
    st.session_state.melhores_resultados = resultados
    
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
            value=st.session_state.get("Filtro_min_perc_lucrativos", 60),
            step=1,
            key="Filtro_min_perc_lucrativos"
        )

    with col2:
        max_drawdown = st.slider(
            "Drawdown Máximo (%)", 
            min_value=0, 
            max_value=50,
            value=st.session_state.get("Filtro_max_drawdown", 15),
            step=1,
            key="Filtro_max_drawdown"
        )

    with col3:
        min_resultado = st.slider(
            "Resultado Mínimo (%)", 
            min_value=-50, 
            max_value=200,
            value=st.session_state.get("Filtro_min_resultado", 10),
            step=1,
            key="Filtro_min_resultado"
        )

    with col4:
        min_trades = st.slider(
            "Número Mínimo de Trades", 
            min_value=0, 
            max_value=50,
            value=st.session_state.get("Filtro_min_trades", 3),
            step=1,
            key="Filtro_min_trades"
        )

    col1, col2 = st.columns(2)

    with col1:
        min_fator_lucro = st.slider(
            "Fator de Lucro Mínimo", 
            min_value=0.0, 
            max_value=10.0,
            value=st.session_state.get("Filtro_min_fator_lucro", 1.5),
            step=0.1,
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
        
        # Estatística específica do Setup 123
        st.subheader("🎯 Estatísticas Setup 123")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_padroes = df_filtrado_resultados['Padrões Encontrados'].sum()
            st.metric("Total Padrões 123 Encontrados", total_padroes)
        
        with col2:
            total_trades_filtrados = df_filtrado_resultados['Trades Filtrados Éden'].sum()
            eden_status = "Ativo" if eden_trades else "Inativo"
            st.metric(f"Trades Filtrados Éden ({eden_status})", total_trades_filtrados)
        
        with col3:
            if total_padroes > 0:
                taxa_conversao = (df_filtrado_resultados['Trades'].sum() / total_padroes) * 100
                st.metric("Taxa de Conversão Padrão→Trade", f"{taxa_conversao:.1f}%")
        
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
        
        st.plotly_chart(fig, width="stretch")
        
        # Gráfico de dispersão: Trades vs Resultado %
        st.subheader("📊 Relação Trades x Resultado %")
        
        fig_scatter = go.Figure()
        
        fig_scatter.add_trace(go.Scatter(
            x=df_filtrado_resultados["Trades"],
            y=df_filtrado_resultados["Resultado (%)"],
            mode="markers",
            marker=dict(
                size=8,
                color=df_filtrado_resultados["% Trades Lucrativos"],
                colorscale="RdYlGn",
                showscale=True,
                colorbar=dict(title="% Trades<br>Lucrativos")
            ),
            text=df_filtrado_resultados["Ativo"],
            hovertemplate="<b>%{text}</b><br>" +
                         "Trades: %{x}<br>" +
                         "Resultado: %{y:.2f}%<br>" +
                         "% Lucrativos: %{marker.color:.1f}%<extra></extra>"
        ))
        
        fig_scatter.update_layout(
            title="Relação entre Número de Trades e Resultado %",
            xaxis_title="Número de Trades",
            yaxis_title="Resultado (%)",
            height=500
        )
        
        st.plotly_chart(fig_scatter, width="stretch")
        
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
                st.markdown(f"### Trades do ativo {ativo_selecionado_detalhes}")
                
                # Informações gerais do ativo
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Padrões 123 Encontrados", resultado_detalhado["Padrões Encontrados"])
                with col2:
                    st.metric("Trades Executados", resultado_detalhado["Trades"])
                with col3:
                    st.metric("Trades Filtrados Éden", resultado_detalhado["Trades Filtrados Éden"])
                with col4:
                    eden_status = "Ativo" if eden_trades else "Inativo"
                    st.metric("Filtro Éden", eden_status)
                
                # DataFrame com os trades
                st.dataframe(
                    df_trades_detalhado.style.format({
                        "Preço Entrada": "R$ {:.2f}",
                        "Preço Saída": "R$ {:.2f}",
                        "Stop Loss": "R$ {:.2f}",
                        "Take Profit": "R$ {:.2f}",
                        "Lucro": "R$ {:.2f}",
                        "Retorno %": "{:.2f}%",
                        "Capital Acumulado": "R$ {:.2f}"
                    })
                )
                
                # Curva de Capital
                st.subheader("📈 Evolução do Capital")
                fig_cap = go.Figure()
                
                # Preparar dados para o gráfico
                df_trades_ordenado = df_trades_detalhado.copy()
                df_trades_ordenado["Data Saída Dt"] = pd.to_datetime(df_trades_ordenado["Data Saída"], format="%d/%m/%Y")
                df_trades_ordenado = df_trades_ordenado.sort_values("Data Saída Dt")
                df_trades_ordenado["Capital Acumulado Correto"] = capital_inicial + df_trades_ordenado["Lucro"].cumsum()
                
                datas_plot = [pd.to_datetime(data_inicial)] + df_trades_ordenado["Data Saída Dt"].tolist()
                capital_plot = [capital_inicial] + df_trades_ordenado["Capital Acumulado Correto"].tolist()
                
                fig_cap.add_trace(go.Scatter(
                    x=datas_plot,
                    y=capital_plot,
                    mode="lines+markers",
                    name="Capital Acumulado",
                    line=dict(color="blue", width=2),
                    marker=dict(size=8, color="blue"),
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
                
                st.plotly_chart(fig_cap, width="stretch")
                
                # Distribuição dos retornos
                st.subheader("📊 Distribuição dos Retornos")
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Histogram(
                    x=df_trades_detalhado["Retorno %"],
                    nbinsx=15,
                    name="Frequência",
                    marker_color="lightblue",
                    opacity=0.7
                ))
                
                fig_hist.update_layout(
                    title="Distribuição dos Retornos por Operação",
                    xaxis_title="Retorno (%)",
                    yaxis_title="Frequência"
                )
                
                st.plotly_chart(fig_hist, width="stretch")
                
                # Análise por motivo de saída
                st.subheader("🎯 Análise por Motivo de Saída")
                motivos_resumo = df_trades_detalhado.groupby("Motivo").agg({
                    "Lucro": ["count", "sum", "mean"],
                    "Retorno %": "mean"
                }).round(2)
                
                motivos_resumo.columns = ["Quantidade", "Lucro Total", "Lucro Médio", "Retorno Médio %"]
                st.dataframe(motivos_resumo.style.format({
                    "Lucro Total": "R$ {:.2f}",
                    "Lucro Médio": "R$ {:.2f}",
                    "Retorno Médio %": "{:.2f}%"
                }))
                
                # Retorno Mensal
                st.subheader("📅 Retorno Mensal (Não Acumulado)")
                
                df_trades_detalhado["Data Saída Dt"] = pd.to_datetime(df_trades_detalhado["Data Saída"], format="%d/%m/%Y")
                df_trades_detalhado["AnoMes"] = df_trades_detalhado["Data Saída Dt"].dt.to_period("M").astype(str)
                
                retorno_mensal = df_trades_detalhado.groupby("AnoMes")["Lucro"].sum().reset_index()
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
                
                st.plotly_chart(fig_bar, width="stretch")
            else:
                st.info("Não há operações registradas para este ativo com os parâmetros selecionados.")
        else:
            st.info("Não foi possível encontrar detalhes para este ativo.")
        
        # Oferecer opção para download do Excel
        st.subheader("📥 Exportar Resultados Filtrados")
    
        # Copiar o DataFrame sem as informações detalhadas que não precisam ir para o Excel
        df_export = df_filtrado_resultados.copy()
        df_export["Lista_Azul"] = df_export["Ativo"].astype(str) + ";Setup123"

        # Gerar link para download do arquivo compacto
        st.markdown("#### 📄 Arquivo Compacto – Resultados Setup 123 por Ativo (Filtrados)")
        st.caption("Contém apenas o resumo dos resultados do Setup 123 por ativo que atendem aos critérios de filtro.")
        st.markdown(
            get_excel_download_link(df_export, f"backtest_setup123_{lista_selecionada}_filtrados.xlsx"), 
            unsafe_allow_html=True
        )
        st.markdown("---")
        
        # Exportar todos os trades detalhados para ativos filtrados
        ativos_filtrados = set(df_filtrado_resultados["Ativo"].tolist())
        filtered_trades = []
        for res in st.session_state.melhores_resultados:
            if res["Ativo"] in ativos_filtrados and isinstance(res["df_trades"], pd.DataFrame) and len(res["df_trades"]) > 0:
                df_trades = res["df_trades"].copy()
                df_trades["Setup"] = "Setup123"
                df_trades["Lista_Azul"] = df_trades["Ativo"].astype(str) + ";Setup123"
                filtered_trades.append(df_trades)

        if filtered_trades:
            df_filtered_trades = pd.concat(filtered_trades)
            
            st.markdown("#### 📄 Arquivo Completo – Operações Detalhadas Setup 123 (Ativos Filtrados)")
            st.caption("Contém todas as operações (trades) feitas com o Setup 123 dos ativos filtrados.")
            st.markdown(
                get_excel_download_link(df_filtered_trades, f"backtest_setup123_{lista_selecionada}_trades_detalhados_filtrados.xlsx"), 
                unsafe_allow_html=True
            )

# Se não executou backtest ainda, mostrar mensagem informativa
else:
    st.info("Selecione os parâmetros desejados e clique em 'Executar Backtest Múltiplo Setup 123' para iniciar a análise. Depois você poderá filtrar os resultados.")
    
    # Mostrar resumo das configurações atuais
    st.subheader("⚙️ Configurações Atuais do Setup 123")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **Setup Básico:**
        - Lista: {lista_selecionada}
        - Ativos: {len(ativos_escolhidos) if ativos_escolhidos else 0} selecionados
        - Período: {data_inicial} a {data_final}
        - Capital: R$ {capital_inicial:,.2f}
        - Stop Loss: {posicao_stop}
        """)
    
    with col2:
        eden_status = "✅ Ativo" if eden_trades else "❌ Inativo"
        trailing_status = "✅ Ativo" if usar_trailing_stop else "❌ Inativo"
        timeout_status = "✅ Ativo" if usar_timeout else "❌ Inativo"
        volume_status = "✅ Ativo" if usar_filtro_volume else "❌ Inativo"
        gap_status = "✅ Ativo" if usar_filtro_gap else "❌ Inativo"
        
        st.markdown(f"""
        **Filtros e Gestão:**
        - Éden dos Trades: {eden_status}
        - Trailing Stop: {trailing_status}
        - Timeout: {timeout_status}
        - Filtro Volume: {volume_status}
        - Filtro Gap: {gap_status}
        """)
    
    if eden_trades:
        st.info(f"🌟 Filtro Éden configurado: MME {mme_curta} e MME {mme_longa}")
    
    if usar_timeout and max_hold_days:
        st.info(f"⏰ Saída forçada configurada para {max_hold_days} candles")
    
    if usar_trailing_stop and trailing_pct:
        st.info(f"📊 Trailing Stop configurado em {trailing_pct}%")