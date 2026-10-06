"""Consulta, conversão e histórico de moedas (Streamlit).
Rodar no terminal: python -m streamlit run app.py
"""
import pandas as pd
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
BASE_URL = "https://economia.awesomeapi.com.br/json"


@st.cache_data(ttl=60)
def consultar_moeda(moeda):
    """Cotação atual. Retorna (dados, erro)."""
    moeda = moeda.strip().upper()
    try:
        resposta = requests.get(f"{BASE_URL}/last/{moeda}", timeout=10)
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


@st.cache_data(ttl=300)
def consultar_historico(moeda, dias):
    """Últimos N dias (um valor por dia). Retorna (DataFrame, erro)."""
    moeda = moeda.strip().upper()
    try:
        resposta = requests.get(f"{BASE_URL}/daily/{moeda}/{dias}", timeout=10)
    except requests.RequestException:
        return None, "Não foi possível conectar à API. Verifique sua internet."
    if resposta.status_code != 200 or not resposta.json():
        return None, f"Não foi possível obter o histórico (código {resposta.status_code})."

    df = pd.DataFrame(resposta.json())
    df["Data"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.date
    df["Valor (R$)"] = df["bid"].astype(float)
    return df.sort_values("Data").set_index("Data")[["Valor (R$)"]], None


def bid_atual(dados):
    return float(dados[list(dados)[0]]["bid"])


st.set_page_config(page_title="Consulta de Moedas", page_icon="💱")
st.title("Consulta de moedas")

escolha = st.selectbox("Qual moeda deseja consultar?", list(MOEDAS.keys()))
moeda = MOEDAS[escolha]
if moeda is None:
    moeda = st.text_input("Código da moeda", placeholder="Ex: USD-BRL, EUR-BRL, BTC-BRL")
moeda = moeda.strip().upper()

if not moeda:
    st.info("Digite o código da moeda para continuar.")
    st.stop()

aba_cotacao, aba_conversor, aba_historico = st.tabs(["Cotação", "Conversor", "Histórico"])

# ---------- 1) Cotação (igual ao main) ----------
with aba_cotacao:
    if st.button("Consultar", type="primary"):
        with st.spinner("Consultando..."):
            dados_api, erro = consultar_moeda(moeda)
        if dados_api:
            st.success("Requisição bem sucedida!")
            st.metric(f"Valor da moeda {moeda}", f"R${bid_atual(dados_api):.2f}")
            with st.expander("Ver resposta completa da API"):
                st.json(dados_api)
        else:
            st.error(f"Erro ao consultar a moeda {moeda}. Verifique se o formato está correto.")
            if erro:
                st.info(erro)

# ---------- 2) Conversor de valores ----------
with aba_conversor:
    dados_api, erro = consultar_moeda(moeda)
    if not dados_api:
        st.error(erro or "Não foi possível obter a cotação.")
    else:
        cotacao = bid_atual(dados_api)
        codigo = moeda.split("-")[0]
        sentido = st.radio("Converter", [f"{codigo} → Real (BRL)", f"Real (BRL) → {codigo}"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, value=1.0, step=1.0, format="%.2f")

        if sentido.startswith(codigo):
            st.metric(f"{valor:,.2f} {codigo} valem", f"R$ {valor * cotacao:,.2f}")
        else:
            st.metric(f"R$ {valor:,.2f} compram", f"{valor / cotacao:,.6f} {codigo}")
        st.caption(f"Cotação usada: 1 {codigo} = R$ {cotacao:,.4f} (atualizada a cada 1 minuto)")

# ---------- 3) Histórico com gráfico ----------
with aba_historico:
    dias = st.select_slider("Período (dias)", options=[7, 15, 30, 60, 90], value=15)
    df, erro = consultar_historico(moeda, dias)
    if df is None:
        st.error(erro)
    else:
        primeiro, ultimo = df["Valor (R$)"].iloc[0], df["Valor (R$)"].iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Máxima", f"R${df['Valor (R$)'].max():,.2f}")
        c2.metric("Mínima", f"R${df['Valor (R$)'].min():,.2f}")
        c3.metric("Variação", f"{(ultimo / primeiro - 1) * 100:+.2f}%")
        st.line_chart(df)