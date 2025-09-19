import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from datetime import timedelta
from PIL import Image

# Caminho dos dados
parquet_path = "01-dados/ativos_historicos.parquet"

st.title("📈 Backtest - Setup 123 - Ativo único")

# Verifica se a base existe
if not os.path.exists(parquet_path):
    st.error("⚠ Base de dados não encontrada. Atualize a base antes de continuar.")
    st.stop()

# Carrega dados
df_base = pd.read_parquet(parquet_path)

# === INTERFACE STREAMLIT ===
st.sidebar.header("📋 Filtros Básicos")
listas_disponiveis = sorted(df_base["Lista"].unique().tolist())
lista_selecionada = st.sidebar.selectbox("Selecione a lista", listas_disponiveis)

df_filtrado = df_base[df_base["Lista"] == lista_selecionada]
ativos_disponiveis = sorted(df_filtrado["Ticker"].unique().tolist())

data_final_padrao = pd.to_datetime(df_filtrado["Date"].max()).normalize()
data_inicial_padrao = data_final_padrao - timedelta(days=730)

st.sidebar.header("🎯 Configuração do Ativo")
ativo_escolhido = st.sidebar.selectbox("Escolha o ativo", ativos_disponiveis)
data_inicial = st.sidebar.date_input("Data inicial", value=data_inicial_padrao)
data_final = st.sidebar.date_input("Data final", value=data_final_padrao)
capital_inicial = st.sidebar.number_input("Capital disponível (R$)", value=10000.0, step=100.0)

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
            st.image(logo, use_container_width=False)
    
    with col_texto:
        st.markdown("""
        <div style='display: flex; align-items: center; height: 100%;'>
            <p style='margin: 0;'>Desenvolvido por Vladimir</p>
        </div>
        """, unsafe_allow_html=True)

# === BACKTEST ===
if st.button("▶️ Executar Backtest Setup 123", type="primary"):
    # Filtra os dados do ativo escolhido
    df = df_filtrado[df_filtrado["Ticker"] == ativo_escolhido].copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    
    # Filtra por período
    df = df[(df["Date"] >= pd.to_datetime(data_inicial)) & (df["Date"] <= pd.to_datetime(data_final))]
    df.sort_values("Date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # Verifica se há dados suficientes
    min_candles = 90 if eden_trades else 10
    if len(df) < min_candles:
        st.error(f"Dados insuficientes. Necessário pelo menos {min_candles} candles.")
        st.stop()
    
    # Calcula médias móveis exponenciais (sempre calcula para consistência)
    df[f'MME_{mme_curta}'] = df['Close'].ewm(span=mme_curta).mean()
    df[f'MME_{mme_longa}'] = df['Close'].ewm(span=mme_longa).mean()
    
    if eden_trades:
        st.info(f"📈 Filtro Éden ativo - usando MME {mme_curta} e {mme_longa}")
    
    # CORREÇÃO: Identifica padrões 123 corretamente (FUNDO com 2º candle tendo menor mínima)
    setup_123 = []
    
    for i in range(2, len(df)):
        candle_1 = df.iloc[i-2]  # primeiro candle
        candle_2 = df.iloc[i-1]  # segundo candle (deve ter menor mínima)
        candle_3 = df.iloc[i]    # terceiro candle
        
        # Verifica filtro de volume no terceiro candle
        if usar_filtro_volume and candle_3["Volume"] < volume_minimo:
            continue
            
        # CORREÇÃO: Condições corretas do Setup 123 (FUNDO):
        # O segundo candle deve ter a menor mínima dos três
        condicao_fundo_123 = (candle_2["Low"] < candle_1["Low"] and 
                              candle_2["Low"] < candle_3["Low"])
        
        if condicao_fundo_123:
            # Define posição do stop baseado na escolha do usuário
            if posicao_stop == "Mínima do penúltimo candle (padrão)":
                stop_loss_setup = candle_2["Low"]  # mínima do segundo candle (penúltimo)
            else:
                stop_loss_setup = candle_3["Low"]  # mínima do terceiro candle (último)
            
            setup_123.append({
                'index': i,
                'data': candle_3["Date"],
                'entrada_target': candle_3["High"],  # máxima do terceiro candle
                'stop_loss': stop_loss_setup,
                'candle_1_low': candle_1["Low"],
                'candle_2_low': candle_2["Low"], 
                'candle_3_low': candle_3["Low"],
                'candle_3_high': candle_3["High"],
                'padrao_tipo': 'Fundo 123'
            })
    
    st.info(f"📊 Encontrados {len(setup_123)} padrões Setup 123 (fundo) no período")
    
    if not setup_123:
        st.warning("⚠️ Nenhum padrão Setup 123 encontrado no período selecionado.")
        st.stop()
    
    # Executa as operações - APENAS UMA POSIÇÃO POR VEZ
    posicao_ativa = False
    trades = []
    trades_filtrados_eden = 0
    
    for setup in setup_123:
        # CORREÇÃO: Só entra se não estiver posicionado
        if posicao_ativa:
            continue
            
        entrada_target = setup['entrada_target']
        stop_loss = setup['stop_loss']
        
        # Calcula o take profit (2x o risco)
        risco = entrada_target - stop_loss
        take_profit = entrada_target + (2 * risco)
        
        # CORREÇÃO: Procura pela entrada a partir do próximo candle
        entrada_executada = False
        for j in range(setup['index'] + 1, len(df)):
            candle_atual = df.iloc[j]
            
            # Verifica gap excessivo na abertura
            if usar_filtro_gap:
                candle_anterior = df.iloc[j-1]
                gap_pct = abs(candle_atual["Open"] - candle_anterior["Close"]) / candle_anterior["Close"] * 100
                if gap_pct > gap_maximo:
                    continue
            
            # Verifica se rompeu a máxima (entrada)
            if candle_atual["High"] >= entrada_target:
                # Determina preço de entrada
                if candle_atual["Open"] >= entrada_target:
                    preco_entrada = candle_atual["Open"]
                else:
                    preco_entrada = entrada_target
                
                # CORREÇÃO: Aplica filtro Éden dos trades corretamente
                if eden_trades:
                    # Obtém as MMEs do candle atual
                    if j < len(df):
                        candle_para_mme = df.iloc[j]
                        mme_curta_atual = candle_para_mme.get(f"MME_{mme_curta}", 0)
                        mme_longa_atual = candle_para_mme.get(f"MME_{mme_longa}", 0)
                        
                        # Entrada deve ser ACIMA de ambas as MMEs
                        if preco_entrada <= mme_curta_atual or preco_entrada <= mme_longa_atual:
                            trades_filtrados_eden += 1
                            continue
                
                # Calcula quantidade de ações
                quantidade = int((capital_inicial // preco_entrada) // 100) * 100
                if quantidade == 0:
                    break
                
                # Recalcula stop e take com base no preço real de entrada
                risco_real = preco_entrada - stop_loss
                take_profit_real = preco_entrada + (2 * risco_real)
                
                posicao_ativa = True  # MARCA POSIÇÃO COMO ATIVA
                data_entrada = candle_atual["Date"]
                dias_hold = 0
                max_preco = preco_entrada
                entrada_executada = True
                
                # Acompanha a posição
                for k in range(j, len(df)):
                    candle_pos = df.iloc[k]
                    dias_hold += 1
                    
                    # Atualiza máximo para trailing stop
                    if usar_trailing_stop:
                        max_preco = max(max_preco, candle_pos["High"])
                        trailing_stop_price = max_preco * (1 - trailing_pct / 100)
                        stop_atual = max(stop_loss, trailing_stop_price)
                    else:
                        stop_atual = stop_loss
                    
                    # Verifica saídas
                    sair = False
                    preco_saida = None
                    motivo = ""
                    
                    # 1. Stop Loss
                    if candle_pos["Low"] <= stop_atual:
                        sair = True
                        preco_saida = min(candle_pos["Open"], stop_atual)
                        motivo = "Trailing Stop" if usar_trailing_stop and stop_atual > stop_loss else "Stop Loss"
                    
                    # 2. Take Profit
                    elif candle_pos["High"] >= take_profit_real:
                        sair = True
                        if candle_pos["Open"] >= take_profit_real:
                            preco_saida = candle_pos["Open"]
                        else:
                            preco_saida = take_profit_real
                        motivo = "Take Profit"
                    
                    # 3. Timeout
                    elif usar_timeout and dias_hold >= max_hold_days:
                        sair = True
                        preco_saida = candle_pos["Close"]
                        motivo = "Timeout"
                    
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
                            "Risco/Recompensa": f"1:2.0",
                            "Lista": lista_selecionada,
                            "Padrão": setup['padrao_tipo']
                        }
                        
                        if eden_trades:
                            trade_data[f"MME {mme_curta}"] = mme_curta_atual
                            trade_data[f"MME {mme_longa}"] = mme_longa_atual
                            trade_data["Éden Ativo"] = "Sim"
                        else:
                            trade_data["Éden Ativo"] = "Não"
                        
                        trades.append(trade_data)
                        posicao_ativa = False  # LIBERA POSIÇÃO PARA PRÓXIMO SETUP
                        break
                
                if entrada_executada:
                    break
    
    # Mostra estatística do filtro Éden
    if eden_trades and trades_filtrados_eden > 0:
        st.info(f"🌟 Filtro Éden eliminou {trades_filtrados_eden} trades por não atenderem ao critério das MMEs")
    
    # Análise dos resultados
    if not trades:
        st.warning("⚠️ Nenhuma operação foi executada no período analisado.")
        st.stop()
    
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
    
    # Exibição dos resultados
    st.success(f"✅ Setup 123 executado! {total_ops} operações | Éden: {'Ativo' if eden_trades else 'Inativo'}")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Capital Final", f"R$ {capital_inicial + lucro_total:,.2f}", f"R$ {lucro_total:,.2f}")
    with col2:
        st.metric("Retorno Total", f"{resultado_pct:.2f}%")
    with col3:
        st.metric("Taxa de Acerto", f"{perc_acertos:.1f}%", f"{ops_lucrativas}/{total_ops}")
    with col4:
        st.metric("Max Drawdown", f"{max_dd_pct:.2f}%", f"R$ {max_drawdown:,.2f}")
    
    # Estatísticas detalhadas
    st.subheader("📋 Estatísticas Detalhadas")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        - 🔢 **Total de Operações**: {total_ops}
        - ✅ **Operações Lucrativas**: {ops_lucrativas} ({perc_acertos:.1f}%)
        - ❌ **Operações Perdedoras**: {total_ops - ops_lucrativas} ({100-perc_acertos:.1f}%)
        - 💰 **Lucro Total**: R$ {lucro_total:,.2f}
        - 📈 **Retorno Percentual**: {resultado_pct:.2f}%
        """)
    
    with col2:
        st.markdown(f"""
        - 📊 **Ganho Médio**: R$ {ganho_medio:,.2f}
        - 📉 **Perda Média**: R$ {perda_media:,.2f}
        - ⚖️ **Fator de Lucro**: {fator_lucro:.2f}
        - 📉 **Drawdown Máximo**: {max_dd_pct:.2f}%
        - 📅 **Dias Médios em Posição**: {df_trades['Dias Hold'].mean():.1f}
        """)
    
    # Tabela de operações
    st.subheader("📄 Histórico de Operações")
    
    if not df_trades.empty:
        format_dict = {
            "Preço Entrada": "R$ {:.2f}",
            "Preço Saída": "R$ {:.2f}", 
            "Stop Loss": "R$ {:.2f}",
            "Take Profit": "R$ {:.2f}",
            "Lucro": "R$ {:.2f}",
            "Retorno %": "{:.2f}%",
            "Capital Acumulado": "R$ {:.2f}"
        }
        
        # Verifica se há colunas de MME para formatação
        colunas_mme = [col for col in df_trades.columns if col.startswith("MME")]
        if colunas_mme:
            for col in colunas_mme:
                format_dict[col] = "R$ {:.2f}"
        
        st.dataframe(
            df_trades.style.format(format_dict),
            use_container_width=True
        )
    
    # Curva de capital
    st.subheader("📈 Evolução do Capital")
    fig = go.Figure()
    
    if not df_trades.empty:
        df_trades_ordenado = df_trades.copy()
        df_trades_ordenado["Data Saída Dt"] = pd.to_datetime(df_trades_ordenado["Data Saída"], format="%d/%m/%Y")
        df_trades_ordenado = df_trades_ordenado.sort_values("Data Saída Dt")
        df_trades_ordenado["Capital Acumulado Correto"] = capital_inicial + df_trades_ordenado["Lucro"].cumsum()
        
        datas_plot = [pd.to_datetime(data_inicial)] + df_trades_ordenado["Data Saída Dt"].tolist()
        capital_plot = [capital_inicial] + df_trades_ordenado["Capital Acumulado Correto"].tolist()
        
        fig.add_trace(go.Scatter(
            x=datas_plot,
            y=capital_plot,
            mode="lines+markers",
            name="Capital Acumulado",
            line=dict(color="blue", width=2),
            marker=dict(size=8, color="blue"),
            hovertemplate="<b>Data:</b> %{x}<br><b>Capital:</b> R$ %{y:,.2f}<extra></extra>"
        ))
        
        fig.add_hline(y=capital_inicial, line_dash="dash", line_color="gray", 
                      annotation_text=f"Capital Inicial: R$ {capital_inicial:,.2f}")
        
        df_trades["Capital Acumulado"] = df_trades_ordenado.set_index(df_trades.index)["Capital Acumulado Correto"]
    
    fig.update_layout(
        title="Evolução do Capital ao Longo do Tempo",
        xaxis_title="Data",
        yaxis_title="Capital (R$)",
        hovermode="x unified",
        height=500,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Distribuição dos retornos
    st.subheader("📊 Distribuição dos Retornos")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=df_trades["Retorno %"],
        nbinsx=20,
        name="Frequência",
        marker_color="lightblue",
        opacity=0.7
    ))
    
    fig_hist.update_layout(
        title="Distribuição dos Retornos por Operação",
        xaxis_title="Retorno (%)",
        yaxis_title="Frequência"
    )
    
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # Análise por motivo de saída
    st.subheader("🎯 Análise por Motivo de Saída")
    motivos_resumo = df_trades.groupby("Motivo").agg({
        "Lucro": ["count", "sum", "mean"],
        "Retorno %": "mean"
    }).round(2)
    
    motivos_resumo.columns = ["Quantidade", "Lucro Total", "Lucro Médio", "Retorno Médio %"]
    st.dataframe(motivos_resumo.style.format({
        "Lucro Total": "R$ {:.2f}",
        "Lucro Médio": "R$ {:.2f}",
        "Retorno Médio %": "{:.2f}%"
    }))
    
    # Retorno mensal
    st.subheader("📅 Retorno Mensal")
    df_trades["Data Saída Dt"] = pd.to_datetime(df_trades["Data Saída"], format="%d/%m/%Y")
    df_trades["AnoMes"] = df_trades["Data Saída Dt"].dt.to_period("M").astype(str)
    
    retorno_mensal = df_trades.groupby("AnoMes")["Lucro"].sum().reset_index()
    cores = ["green" if val >= 0 else "red" for val in retorno_mensal["Lucro"]]
    
    fig_bar = go.Figure(data=[
        go.Bar(
            x=retorno_mensal["AnoMes"],
            y=retorno_mensal["Lucro"],
            marker_color=cores,
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
    
    # Download dos dados
    with st.expander("💾 Download dos Resultados"):
        csv = df_trades.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="📊 Baixar Histórico de Operações (CSV)",
            data=csv,
            file_name=f"setup_123_{ativo_escolhido}_{data_inicial}_{data_final}.csv",
            mime="text/csv"
        )