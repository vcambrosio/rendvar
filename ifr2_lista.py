# ifr2_lista.py

import streamlit as st

def executar_ifr2_lista():
    """
    Interface para o setup IFR2 aplicado a uma lista de ativos.
    """
    lista = st.text_area("Digite os tickers da Lista Azul (um por linha):")

    if st.button("Executar IFR2 para lista"):
        if lista.strip():
            tickers = [linha.strip() for linha in lista.strip().splitlines()]
            st.info(f"Executando IFR2 para {len(tickers)} ativos...")
            # Aqui você implementará a lógica real para a lista azul
        else:
            st.warning("Digite pelo menos um ticker.")
