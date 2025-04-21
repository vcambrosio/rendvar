import streamlit as st
import pandas as pd
import os
from datetime import date
from PIL import Image

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


# Volume médio mínimo (entrada em milhões de R$)
volume_minimo_milhoes = st.sidebar.number_input(
    "Volume médio mínimo (R$ milhões)", 
    min_value=0.0,
    value=10.0,
    step=10.0,
    format="%.2f"
)

# Converter para reais
volume_minimo = volume_minimo_milhoes * 1_000_000


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

# Aplicar filtro de volume mínimo
df_filtrados_volume = df_ordenado[df_ordenado['Media_Movel_Volume'] >= volume_minimo]

# Selecionar os top N tickers após o filtro
df_top_liquidos = df_filtrados_volume[['Ticker', 'Media_Movel_Volume']].head(quantidade_tickers)


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


# Botão para salvar CSV com nome padronizado (somente os tickers, sem cabeçalho)
if st.button("💾 Gerar lista para base de dados"):
    # Garante que a pasta existe
    pasta_listas = "01-dados/listas_csv"
    os.makedirs(pasta_listas, exist_ok=True)

    # Nome do arquivo com data
    data_hoje = date.today().strftime("%Y-%m-%d")
    nome_arquivo = f"{lista_selecionada}-Mais_liq-{data_hoje}.csv"
    caminho_completo = os.path.join(pasta_listas, nome_arquivo)

    # Salva apenas os tickers, sem cabeçalho
    df_top_liquidos["Ticker"].to_csv(
        caminho_completo,
        index=False,
        header=False,
        encoding="utf-8"
    )
    st.success(f"📄 Lista salva com sucesso em: {caminho_completo}")