import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import timedelta, datetime
from io import BytesIO
import base64
import random

from PIL import Image

# Configuração
st.set_page_config(page_title="Ranking Setup 123 - Índice LD", layout="wide")

parquet_path = "01-dados/ativos_historicos.parquet"

st.title("🏆 Ranking de Ativos Setup 123 pelo Índice LD Médio")

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

# Parâmetros configuráveis
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parâmetros do Setup 123")

# Configuração do Stop Loss
posicao_stop = st.sidebar.radio(
    "Posição do Stop Loss:",
    ["Mínima do penúltimo candle (padrão)", "Mínima do último candle"]
)

# Seção Éden dos Trades
st.sidebar.markdown("#### 🌟 Éden dos Trades")
eden_trades = st.sidebar.checkbox("Ativar Filtro Éden dos Trades", value=False)
mme_curta = st.sidebar.slider("MME Curta", min_value=1, max_value=50, value=8)
mme_longa = st.sidebar.slider("MME Longa", min_value=10, max_value=200, value=80)

# Filtros Adicionais
st.sidebar.markdown("#### 🔧 Filtros Adicionais")
usar_filtro_volume = st.sidebar.checkbox("Filtrar por volume mínimo")
if usar_filtro_volume:
    volume_minimo = st.sidebar.number_input("Volume mínimo diário", value=1000000, step=100000)
else:
    volume_minimo = 0

usar_filtro_gap = st.sidebar.checkbox("Ignorar gaps > 2%")
gap_maximo = 2.0 if usar_filtro_gap else 100.0

# Parâmetros de Saída
st.sidebar.markdown("#### Parâmetros de Saída")
usar_timeout = st.sidebar.checkbox("Usar timeout (saída forçada)", value=True)
max_hold_days = st.sidebar.slider("Dias máximos de permanência", min_value=1, max_value=20, value=10, disabled=not usar_timeout)

usar_trailing_stop = st.sidebar.checkbox("Usar trailing stop", value=False)
trailing_pct = st.sidebar.slider("Percentual de trailing stop", min_value=1.0, max_value=20.0, value=5.0, disabled=not usar_trailing_stop)

# Filtro de LD Médio
st.sidebar.markdown("#### Filtro de Resultados")
filtro_ld_ativo = st.sidebar.checkbox("Filtrar por LD Médio", value=True)
ld_minimo = st.sidebar.slider(
    "Valor mínimo de LD Médio:", 
    min_value=0.0,
    max_value=10.0,
    value=3.0,
    step=0.5,
    format="%.1f",
    disabled=not filtro_ld_ativo
)

# Parâmetros de Capital
st.sidebar.markdown("#### Parâmetros de Capital")
capital_inicial = st.sidebar.number_input("Capital inicial (R$)", min_value=10000, max_value=1000000, value=100000, step=10000)

def gerar_arquivos_exportacao(df_resultados):
    """
    Gera os arquivos setup123_dados.txt, lista_azul.set e ranking_setup123.txt
    """
    output_dir = "03-outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Arquivo setup123_dados.txt
    setup123_dados_path = os.path.join(output_dir, "setup123_dados.txt")
    with open(setup123_dados_path, "w") as f:
        for _, row in df_resultados.iterrows():
            f.write(f"{row['Ativo']};SETUP123\n")
    
    # Arquivo lista_azul.set
    lista_azul_filename = f"{timestamp}-lista_azul.set"
    lista_azul_path = os.path.join(output_dir, lista_azul_filename)
    with open(lista_azul_path, "w") as f:
        f.write(f"{random.randint(1, 1000)}\n")
        for _, row in df_resultados.iterrows():
            f.write(f"{row['Ativo']}\n")
    
    # Arquivo ranking_setup123.txt
    ranking_setup123_path = os.path.join(output_dir, "ranking_setup123.txt")
    with open(ranking_setup123_path, "w") as f:
        for _, row in df_resultados.iterrows():
            ld_formatado = f"{row['LD Médio']:.2f}".replace('.', ',')
            f.write(f"{row['Ativo']};{ld_formatado}\n")
    
    # Criar links de download
    setup123_dados_link = criar_link_download(setup123_dados_path, "setup123_dados.txt")
    lista_azul_link = criar_link_download(lista_azul_path, lista_azul_filename)
    ranking_setup123_link = criar_link_download(ranking_setup123_path, "ranking_setup123.txt")
    
    return setup123_dados_path, lista_azul_path, ranking_setup123_path, setup123_dados_link, lista_azul_link, ranking_setup123_link

def criar_link_download(file_path, filename):
    """
    Cria um link de download para um arquivo
    """
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    return f'<a href="data:text/plain;base64,{b64}" download="{filename}">📥 Baixar {filename}</a>'

def backtest_ativo_setup123(ativo, df_filtrado, data_inicial, data_final, 
                           posicao_stop, eden_trades, mme_curta, mme_longa,
                           usar_filtro_volume, volume_minimo, usar_filtro_gap, gap_maximo,
                           usar_timeout, max_hold_days, usar_trailing_stop, trailing_pct,
                           capital_inicial):
    
    # Filtra os dados do ativo
    df = df_filtrado[df_filtrado["Ticker"] == ativo].copy()
    if df.empty:
        return 0, 0, 0, 0
        
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    
    # Adiciona buffer para cálculo das médias
    buffer_dias = max(mme_longa if eden_trades else 10, 365)
    data_inicial_expandida = pd.to_datetime(data_inicial) - timedelta(days=buffer_dias)
    df = df[(df["Date"] >= data_inicial_expandida) & (df["Date"] <= pd.to_datetime(data_final))]
    
    if df.empty:
        return 0, 0, 0, 0
        
    df.sort_values("Date", inplace=True)
    df.set_index("Date", inplace=True)
    
    # Calcula médias móveis se necessário
    if eden_trades:
        df[f'MME_{mme_curta}'] = df['Close'].ewm(span=mme_curta).mean()
        df[f'MME_{mme_longa}'] = df['Close'].ewm(span=mme_longa).mean()
    
    # Filtra para período de análise
    df = df[df.index >= pd.to_datetime(data_inicial)]
    
    if len(df) <= 10:
        return 0, 0, 0, 0
    
    # Identifica padrões 123
    setup_123 = []
    for i in range(2, len(df)):
        candle_1 = df.iloc[i-2]
        candle_2 = df.iloc[i-1] 
        candle_3 = df.iloc[i]
        
        # Filtro de volume
        if usar_filtro_volume and candle_3["Volume"] < volume_minimo:
            continue
            
        # Condição do Setup 123 (FUNDO): segundo candle tem menor mínima
        condicao_fundo_123 = (candle_2["Low"] < candle_1["Low"] and 
                              candle_2["Low"] < candle_3["Low"])
        
        if condicao_fundo_123:
            if posicao_stop == "Mínima do penúltimo candle (padrão)":
                stop_loss_setup = candle_2["Low"]
            else:
                stop_loss_setup = candle_3["Low"]
            
            setup_123.append({
                'index': i,
                'data': candle_3.name,
                'entrada_target': candle_3["High"],
                'stop_loss': stop_loss_setup
            })
    
    if not setup_123:
        return 0, 0, 0, 0
    
    # Executa as operações
    posicao_ativa = False
    trades = []
    
    for setup in setup_123:
        if posicao_ativa:
            continue
            
        entrada_target = setup['entrada_target']
        stop_loss = setup['stop_loss']
        
        # Take profit (2x o risco)
        risco = entrada_target - stop_loss
        take_profit = entrada_target + (2 * risco)
        
        # Procura pela entrada
        entrada_executada = False
        for j in range(setup['index'] + 1, len(df)):
            candle_atual = df.iloc[j]
            
            # Filtro de gap
            if usar_filtro_gap:
                candle_anterior = df.iloc[j-1]
                gap_pct = abs(candle_atual["Open"] - candle_anterior["Close"]) / candle_anterior["Close"] * 100
                if gap_pct > gap_maximo:
                    continue
            
            # Verifica se rompeu a máxima (entrada)
            if candle_atual["High"] >= entrada_target:
                if candle_atual["Open"] >= entrada_target:
                    preco_entrada = candle_atual["Open"]
                else:
                    preco_entrada = entrada_target
                
                # Aplica filtro Éden dos trades
                if eden_trades:
                    mme_curta_atual = candle_atual[f"MME_{mme_curta}"]
                    mme_longa_atual = candle_atual[f"MME_{mme_longa}"]
                    
                    if preco_entrada <= mme_curta_atual or preco_entrada <= mme_longa_atual:
                        continue
                
                # Calcula quantidade
                quantidade = int((capital_inicial // preco_entrada) // 100) * 100
                if quantidade == 0:
                    break
                
                # Recalcula take profit com preço real
                risco_real = preco_entrada - stop_loss
                take_profit_real = preco_entrada + (2 * risco_real)
                
                posicao_ativa = True
                dias_hold = 0
                max_preco = preco_entrada
                entrada_executada = True
                
                # Acompanha a posição
                for k in range(j, len(df)):
                    candle_pos = df.iloc[k]
                    dias_hold += 1
                    
                    # Trailing stop
                    if usar_trailing_stop:
                        max_preco = max(max_preco, candle_pos["High"])
                        trailing_stop_price = max_preco * (1 - trailing_pct / 100)
                        stop_atual = max(stop_loss, trailing_stop_price)
                    else:
                        stop_atual = stop_loss
                    
                    # Verifica saídas
                    sair = False
                    preco_saida = None
                    
                    # Stop Loss
                    if candle_pos["Low"] <= stop_atual:
                        sair = True
                        preco_saida = min(candle_pos["Open"], stop_atual)
                    
                    # Take Profit
                    elif candle_pos["High"] >= take_profit_real:
                        sair = True
                        if candle_pos["Open"] >= take_profit_real:
                            preco_saida = candle_pos["Open"]
                        else:
                            preco_saida = take_profit_real
                    
                    # Timeout
                    elif usar_timeout and dias_hold >= max_hold_days:
                        sair = True
                        preco_saida = candle_pos["Close"]
                    
                    if sair:
                        lucro = (preco_saida - preco_entrada) * quantidade
                        trades.append(lucro)
                        posicao_ativa = False
                        break
                
                if entrada_executada:
                    break
    
    # Análise dos resultados
    if trades:
        capital = [capital_inicial]
        for lucro in trades:
            capital.append(capital[-1] + lucro)
        
        resultado_perc = (capital[-1] - capital_inicial) / capital_inicial * 100
        dd = max([max(capital[:i+1]) - v for i, v in enumerate(capital)])
        dd_perc = dd / max(capital) * 100 if max(capital) != 0 else 0
        indice_ld = resultado_perc / dd_perc if dd_perc != 0 else 0
        
        return indice_ld, resultado_perc, dd_perc, len(trades)
    else:
        return 0, 0, 0, 0

# === Execução Ranking ===
if st.button("🚀 Calcular Ranking"):
    resultados = []
    ativos_excluidos = []
    progress_bar = st.progress(0)
    total = len(ativos_escolhidos)

    for idx, ativo in enumerate(ativos_escolhidos):
        df_atv = df_filtrado[df_filtrado["Ticker"] == ativo]
        if df_atv.empty:
            ativos_excluidos.append({"Ativo": ativo, "Motivo": "Sem dados disponíveis"})
            progress_bar.progress((idx + 1) / total)
            continue

        data_final = pd.to_datetime(df_atv["Date"]).max()

        # Calcular para cada período
        ld_10a, lucro_10a, dd_10a, trades_10a = backtest_ativo_setup123(
            ativo, df_filtrado, data_final - timedelta(days=365*10), data_final,
            posicao_stop, eden_trades, mme_curta, mme_longa,
            usar_filtro_volume, volume_minimo, usar_filtro_gap, gap_maximo,
            usar_timeout, max_hold_days, usar_trailing_stop, trailing_pct,
            capital_inicial)
            
        ld_5a, lucro_5a, dd_5a, trades_5a = backtest_ativo_setup123(
            ativo, df_filtrado, data_final - timedelta(days=365*5), data_final,
            posicao_stop, eden_trades, mme_curta, mme_longa,
            usar_filtro_volume, volume_minimo, usar_filtro_gap, gap_maximo,
            usar_timeout, max_hold_days, usar_trailing_stop, trailing_pct,
            capital_inicial)
            
        ld_3a, lucro_3a, dd_3a, trades_3a = backtest_ativo_setup123(
            ativo, df_filtrado, data_final - timedelta(days=365*3), data_final,
            posicao_stop, eden_trades, mme_curta, mme_longa,
            usar_filtro_volume, volume_minimo, usar_filtro_gap, gap_maximo,
            usar_timeout, max_hold_days, usar_trailing_stop, trailing_pct,
            capital_inicial)
            
        ld_2a, lucro_2a, dd_2a, trades_2a = backtest_ativo_setup123(
            ativo, df_filtrado, data_final - timedelta(days=365*2), data_final,
            posicao_stop, eden_trades, mme_curta, mme_longa,
            usar_filtro_volume, volume_minimo, usar_filtro_gap, gap_maximo,
            usar_timeout, max_hold_days, usar_trailing_stop, trailing_pct,
            capital_inicial)
            
        ld_1a, lucro_1a, dd_1a, trades_1a = backtest_ativo_setup123(
            ativo, df_filtrado, data_final - timedelta(days=365*1), data_final,
            posicao_stop, eden_trades, mme_curta, mme_longa,
            usar_filtro_volume, volume_minimo, usar_filtro_gap, gap_maximo,
            usar_timeout, max_hold_days, usar_trailing_stop, trailing_pct,
            capital_inicial)

        # Verificar dados problemáticos
        dados_problematicos = False
        motivo_exclusao = ""

        if trades_10a <= 0 or trades_5a <= 0 or trades_3a <= 0 or trades_2a <= 0 or trades_1a <= 0:
            dados_problematicos = True
            motivo_exclusao = "Sem trades em pelo menos um período"
        
        if dd_10a < 0 or dd_5a < 0 or dd_3a < 0 or dd_2a < 0 or dd_1a < 0:
            dados_problematicos = True
            motivo_exclusao = "Drawdown negativo detectado"
            
        if lucro_10a <= 0 and lucro_5a <= 0 and lucro_3a <= 0 and lucro_2a <= 0 and lucro_1a <= 0:
            dados_problematicos = True
            motivo_exclusao = "Lucro negativo ou zero em todos os períodos"
        
        if dados_problematicos:
            ativos_excluidos.append({"Ativo": ativo, "Motivo": motivo_exclusao})
            progress_bar.progress((idx + 1) / total)
            continue

        # Calcular médias anualizadas
        lucros_anualizados = []
        if lucro_10a != 0: lucros_anualizados.append(lucro_10a / 10)
        if lucro_5a != 0: lucros_anualizados.append(lucro_5a / 5)
        if lucro_3a != 0: lucros_anualizados.append(lucro_3a / 3)
        if lucro_2a != 0: lucros_anualizados.append(lucro_2a / 2)
        if lucro_1a != 0: lucros_anualizados.append(lucro_1a / 1)
        
        lucro_medio = sum(lucros_anualizados) / len(lucros_anualizados) if lucros_anualizados else 0

        dds_anualizados = []
        if dd_10a != 0: dds_anualizados.append(dd_10a / 10)
        if dd_5a != 0: dds_anualizados.append(dd_5a / 5)
        if dd_3a != 0: dds_anualizados.append(dd_3a / 3)
        if dd_2a != 0: dds_anualizados.append(dd_2a / 2)
        if dd_1a != 0: dds_anualizados.append(dd_1a / 1)
        
        dd_medio = sum(dds_anualizados) / len(dds_anualizados) if dds_anualizados else 0

        trades_anualizados = []
        if trades_10a != 0: trades_anualizados.append(trades_10a / 10)
        if trades_5a != 0: trades_anualizados.append(trades_5a / 5)
        if trades_3a != 0: trades_anualizados.append(trades_3a / 3)
        if trades_2a != 0: trades_anualizados.append(trades_2a / 2)
        if trades_1a != 0: trades_anualizados.append(trades_1a / 1)
        
        trades_medio = sum(trades_anualizados) / len(trades_anualizados) if trades_anualizados else 0

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
            "LD Médio": ld_medio,
            "Trades em 2 anos": trades_2a
        })

        progress_bar.progress((idx + 1) / total)

    df_resultados = pd.DataFrame(resultados)
    
    if df_resultados.empty:
        st.warning("⚠️ Nenhum ativo válido encontrado com os parâmetros selecionados.")
    else:
        # Ordenar por LD Médio
        df_resultados = df_resultados.sort_values(by="LD Médio", ascending=False)
        
        # Aplicar filtro de LD Médio
        if filtro_ld_ativo:
            df_display = df_resultados[df_resultados["LD Médio"] >= ld_minimo]
            st.info(f"Exibindo {len(df_display)} de {len(df_resultados)} ativos com LD Médio >= {ld_minimo:.1f}")
        else:
            df_display = df_resultados

        st.subheader("📊 Ranking Final (por LD Médio)")
        
        colunas_display = ["Ativo", "LD Médio", "Lucro Médio", "DD Médio", "Trades medio"]
        
        st.dataframe(
            df_display[colunas_display].style.format({
                "LD Médio": "{:.2f}",
                "Lucro Médio": "{:.2f}%",
                "DD Médio": "{:.2f}%",
                "Trades medio": "{:.1f}"
            })
        )

        # Tabela detalhada
        st.subheader("📋 Tabela Detalhada")
        
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
            df_display[colunas_detalhadas].style.format({
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
        
        # Gerar arquivos de exportação
        setup123_dados_path, lista_azul_path, ranking_setup123_path, setup123_dados_link, lista_azul_link, ranking_setup123_link = gerar_arquivos_exportacao(df_display)
        
        # Links de download
        st.subheader("📥 Arquivos de Exportação")
        st.markdown("Os arquivos foram gerados automaticamente e estão disponíveis para download:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(setup123_dados_link, unsafe_allow_html=True)
        with col2:
            st.markdown(lista_azul_link, unsafe_allow_html=True)
        with col3:
            st.markdown(ranking_setup123_link, unsafe_allow_html=True)
        
    # Ativos excluídos
    if ativos_excluidos:
        st.subheader("⚠️ Ativos Excluídos do Ranking")
        st.markdown("Os seguintes ativos foram excluídos por apresentarem dados problemáticos:")
        df_excluidos = pd.DataFrame(ativos_excluidos)
        st.dataframe(df_excluidos)

    # Export para Excel
    output = BytesIO()
    df_resultados.to_excel(output, index=False, engine="xlsxwriter")
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="ranking_setup123_ld.xlsx">📥 Baixar Ranking em Excel</a>'
    st.markdown(href, unsafe_allow_html=True)
    
    # Metodologia
    st.markdown("**📋 Metodologia do Setup 123:**")
    st.markdown("")
    st.markdown("**Cálculos:**")
    st.markdown("- **Trades Médio**: Média das razões (Número de trades de N anos ÷ N anos)")
    st.markdown("- **Lucro Médio**: Média das razões (Lucro de N anos ÷ N anos)")
    st.markdown("- **DD Médio**: Média das razões (Drawdown de N anos ÷ N anos)")
    st.markdown("- **LD Médio**: Lucro Médio ÷ DD Médio")
    st.markdown("")
    st.markdown("**⚙️ Parâmetros do Setup:**")
    st.markdown("- **Períodos analisados**: 10, 5, 3, 2 e 1 anos")
    st.markdown("- **Padrão 123**: Fundo com 3 candles - 2º candle tem menor mínima")
    st.markdown(f"- **Stop Loss**: {posicao_stop}")
    st.markdown("- **Take Profit**: 2x o risco (distância entrada-stop)")
    
else:
    st.info("Clique em 'Calcular Ranking' para gerar o ranking de índice LD médio.")