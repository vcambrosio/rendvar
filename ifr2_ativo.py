# ifr2_ativo.py

import streamlit as st

def executar_ifr2_ativo():
    """
    Interface para o setup IFR2 aplicado a um ativo único.
    """
    ativo = st.text_input("Digite o ticker do ativo (ex: PETR4.SA):")

    if st.button("Executar análise IFR2"):
        if ativo:
            st.info(f"Executando análise IFR2 para o ativo {ativo}...")
            # Aqui você implementará a lógica real do IFR2 para ativo único
        else:
            st.warning("Por favor, insira um ticker válido.")
