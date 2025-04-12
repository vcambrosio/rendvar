import streamlit as st
import pandas as pd
import yfinance as yf
import os

# Caminho para o arquivo Parquet onde os dados históricos serão salvos
parquet_path = "01-dados/ativos_historicos.parquet"

# Caminho do arquivo CSV com a lista de ativos
csv_path = "01-dados/lista_ativos.csv"

def atualizar_base():
    st.header("📥 Atualizar Base de Dados")

    # Verifica se o arquivo lista_ativos.csv existe
    if os.path.exists(csv_path):
        # Carrega os tickers do arquivo CSV
        tickers_df = pd.read_csv(csv_path, header=None)
        tickers = tickers_df[0].astype(str).str.upper().tolist()
        st.success(f"{len(tickers)} ativos carregados.")
    else:
        st.error(f"❌ O arquivo {csv_path} não foi encontrado na pasta '01-dados'.")
        return  # Interrompe a execução caso o arquivo não exista

    # Botão para iniciar a atualização
    if st.button("🔄 Atualizar Base"):
        st.info("⏳ Buscando dados do Yahoo Finance...")

        # Carrega a base de dados existente, se existir
        if os.path.exists(parquet_path):
            df_base = pd.read_parquet(parquet_path)
        else:
            df_base = pd.DataFrame()

        novos_dados = []

        for ticker in tickers:
            try:
                # Se o ticker já está na base, faz uma atualização incremental
                if not df_base.empty and ticker in df_base["Ticker"].unique():
                    ultima_data = df_base[df_base["Ticker"] == ticker]["Date"].max()
                    df_novo = yf.Ticker(ticker + ".SA").history(start=ultima_data)
                    df_novo = df_novo[df_novo.index > ultima_data]
                else:
                    # Se não está na base, puxa todos os dados históricos
                    df_novo = yf.Ticker(ticker + ".SA").history(period="max")

                if not df_novo.empty:
                    df_novo = df_novo.reset_index()
                    df_novo["Ticker"] = ticker
                    novos_dados.append(df_novo)
                    st.write(f"✅ {ticker}: {len(df_novo)} registros adicionados.")
                else:
                    st.warning(f"⚠️ {ticker} sem novos dados.")
            except Exception as e:
                st.error(f"Erro ao obter {ticker}: {e}")

        # Se houver novos dados, atualiza a base e salva
        if novos_dados:
            df_novos = pd.concat(novos_dados, ignore_index=True)
            df_total = pd.concat([df_base, df_novos], ignore_index=True)
            df_total.drop_duplicates(subset=["Ticker", "Date"], keep="last", inplace=True)
            df_total.to_parquet(parquet_path, index=False)
            st.success("✅ Base atualizada com sucesso.")
        else:
            st.warning("⚠️ Nenhum dado novo para atualizar.")

# Chama a função de atualizar base
atualizar_base()
