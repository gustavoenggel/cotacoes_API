"""Consulta de cotações - versão Streamlit do main.py.
Rodar: python -m streamlit run app.py
"""
import requests
import streamlit as st

MOEDAS = {
    "USD-BRL (Dólar Americano)": "USD-BRL",
    "EUR-BRL (Euro)": "EUR-BRL",
    "GBP-BRL (Libra Esterlina)": "GBP-BRL",
    "ARS-BRL (Peso Argentino)": "ARS-BRL",
    "BTC-BRL (Bitcoin)": "BTC-BRL",
    "ETH-BRL (Ethereum)": "ETH-BRL",
    "Outra (digitar o código)": None,
}


def consultar_moeda(moeda):
    """Mesma lógica do main.py: retorna (dados, erro)."""
    moeda_formatada = moeda.strip().upper()
    url = f"https://economia.awesomeapi.com.br/json/last/{moeda_formatada}"
    try:
        resposta = requests.get(url, timeout=10)
    except requests.RequestException:
        return None, "Não foi possível conectar à API. Verifique sua internet."

    if resposta.status_code == 200:
        return resposta.json(), None
    if resposta.status_code == 404:
        erro = resposta.json()
        return None, (
            f"Status: {erro.get('status')}  \n"
            f"Código: {erro.get('code')}  \n"
            f"Mensagem: {erro.get('message')}"
        )
    return None, f"Erro na requisição: {resposta.status_code}"


st.set_page_config(page_title="Consulta de Moedas", page_icon="💱")
st.title("Consulta de moedas")

escolha = st.selectbox("Qual moeda deseja consultar?", list(MOEDAS.keys()))
moeda_desejada = MOEDAS[escolha]
if moeda_desejada is None:
    moeda_desejada = st.text_input("Código da moeda", placeholder="Ex: USD-BRL, EUR-BRL, BTC-BRL")

if st.button("Consultar", type="primary"):
    if not moeda_desejada.strip():
        st.warning("Digite o código da moeda.")
    else:
        with st.spinner("Consultando..."):
            dados_api, erro = consultar_moeda(moeda_desejada)

        if dados_api:
            chave = list(dados_api)[0]
            valor = dados_api[chave]["bid"]
            st.success("Requisição bem sucedida!")
            st.metric(f"Valor da moeda {moeda_desejada.strip().upper()}", f"R${float(valor):.2f}")
            with st.expander("Ver resposta completa da API"):
                st.json(dados_api)
        else:
            st.error(f"Erro ao consultar a moeda {moeda_desejada}. Verifique se o formato está correto.")
            if erro:
                st.info(erro)