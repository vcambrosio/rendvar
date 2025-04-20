import streamlit as st
import pandas as pd
import os

# Configuração da página
st.set_page_config(page_title="Tickers Mais Líquidos", layout="wide")

# Caminho dos dados
parquet_path = "01-dados/ativos_historicos.parquet"

st.title("📊 Tickers Mais Líquidos por Lista")

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

# Número de dias para calcular a média móvel
dias_media_movel = st.sidebar.number_input(
    "Período da média móvel (dias)", 
    min_value=1, 
    max_value=200, 
    value=21
)

# Quantidade de tickers a serem exibidos
quantidade_tickers = st.sidebar.number_input(
    "Quantidade de tickers a serem exibidos", 
    min_value=1, 
    max_value=100, 
    value=50
)

# Filtrar dados pela lista selecionada
df_filtrado = df_base[df_base["Lista"] == lista_selecionada].copy()

# Verificar se há dados para a lista selecionada
if df_filtrado.empty:
    st.warning(f"Não há dados disponíveis para a lista '{lista_selecionada}'.")
    st.stop()

# Converter a coluna Date para datetime se necessário
df_filtrado['Date'] = pd.to_datetime(df_filtrado['Date'])

# Função para calcular a média móvel de cada ativo
def calcular_media_movel(grupo, dias):
    grupo = grupo.sort_values('Date')
    grupo['Media_Movel_Volume'] = grupo['Volume'].rolling(window=dias).mean()
    return grupo

# Calcular média móvel para cada ativo
df_com_media = df_filtrado.groupby('Ticker').apply(
    lambda x: calcular_media_movel(x, dias_media_movel)
).reset_index(drop=True)

# Pegar apenas os registros mais recentes de cada ativo
df_ultimos = df_com_media.sort_values('Date').groupby('Ticker').last().reset_index()

# Ordenar por média móvel de volume (do maior para o menor)
df_ordenado = df_ultimos.sort_values('Media_Movel_Volume', ascending=False)

# Selecionar os top N tickers
df_top_liquidos = df_ordenado[['Ticker', 'Media_Movel_Volume']].head(quantidade_tickers)

# Formatar o volume para melhor visualização
def formatar_volume(volume):
    if pd.isna(volume):
        return "N/A"
    if volume >= 1_000_000_000:
        return f"{volume/1_000_000_000:.2f}B"
    elif volume >= 1_000_000:
        return f"{volume/1_000_000:.2f}M"
    elif volume >= 1_000:
        return f"{volume/1_000:.2f}K"
    return f"{volume:.2f}"

df_top_liquidos["Volume Formatado"] = df_top_liquidos["Media_Movel_Volume"].apply(formatar_volume)

# Exibir resultados
st.subheader(f"🏆 Top {quantidade_tickers} Tickers Mais Líquidos - Lista: {lista_selecionada}")
st.write(f"📊 Média móvel calculada para {dias_media_movel} dias")

# Mostrar tabela com os tickers mais líquidos
st.dataframe(
    df_top_liquidos.style.format({"Media_Movel_Volume": "{:,.2f}"}),
    column_config={
        "Ticker": "Ticker",
        "Media_Movel_Volume": st.column_config.NumberColumn(
            f"Média Móvel ({dias_media_movel}d) Volume (R$)", 
            format="%.2f"
        ),
        "Volume Formatado": "Volume Formatado"
    },
    hide_index=True,
    use_container_width=True
)

# Opção para download dos resultados
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

csv = convert_df_to_csv(df_top_liquidos)

st.download_button(
    label="📥 Baixar resultados como CSV",
    data=csv,
    file_name=f"tickers_liquidos_{lista_selecionada}_media{dias_media_movel}d.csv",
    mime="text/csv"
)

# Gráfico de barras dos volumes
st.subheader(f"📈 Média Móvel de {dias_media_movel} dias do Volume")
st.bar_chart(
    df_top_liquidos.set_index("Ticker")["Media_Movel_Volume"],
    height=500,
    use_container_width=True
)