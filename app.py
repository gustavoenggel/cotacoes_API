"""Câmbio - painel de cotação, conversão e histórico (Streamlit).
Rodar no terminal: python -m streamlit run app.py
"""
import html

import pandas as pd
import requests
import streamlit as st

MOEDAS = {
    "USD-BRL · Dólar Americano": "USD-BRL",
    "EUR-BRL · Euro": "EUR-BRL",
    "GBP-BRL · Libra Esterlina": "GBP-BRL",
    "ARS-BRL · Peso Argentino": "ARS-BRL",
    "BTC-BRL · Bitcoin": "BTC-BRL",
    "ETH-BRL · Ethereum": "ETH-BRL",
    "Outra (digitar o código)": None,
}
PAINEL = ["USD-BRL", "EUR-BRL", "GBP-BRL", "BTC-BRL"]
BASE_URL = "https://economia.awesomeapi.com.br/json"

st.set_page_config(page_title="Câmbio | Cotações", page_icon="💱", layout="centered")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');
:root{--ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--bg:#F5F7FB;--accent:#0F9D8F;--navy:#0B1B3A;}
html,body,.stApp,[class*="css"]{font-family:'Inter',sans-serif;color:var(--ink);}
.stApp{background:var(--bg);}
header[data-testid="stHeader"],footer,#MainMenu{display:none;}
.block-container{max-width:980px;padding:1.4rem 1.2rem 3rem;}
.num{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;}

/* Hero */
.hero{background:radial-gradient(120% 140% at 100% 0%,#14507A 0%,transparent 55%),linear-gradient(135deg,#0B1B3A,#10284F);
 border-radius:20px;padding:28px 28px 24px;color:#fff;margin-bottom:22px;}
.hero-top{display:flex;justify-content:space-between;align-items:center;font-size:13px;opacity:.85;}
.logo{font-weight:700;letter-spacing:.2px;font-size:15px;}
.live{display:flex;align-items:center;gap:8px;}
.live i{width:8px;height:8px;border-radius:50%;background:#4ADE80;box-shadow:0 0 0 4px rgba(74,222,128,.2);}
.hero h1{color:#fff;font-size:clamp(26px,4vw,36px);font-weight:700;letter-spacing:-.02em;margin:18px 0 4px;padding:0;line-height:1.15;}
.hero p{margin:0 0 20px;opacity:.75;font-size:15px;}
.tks{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;}
.tk{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:14px 16px;}
.tk-code{font-size:12px;font-weight:600;opacity:.7;letter-spacing:.4px;}
.tk-val{font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:700;margin:6px 0 8px;}

/* Badges */
.badge{display:inline-block;font-size:12px;font-weight:600;padding:3px 9px;border-radius:999px;}
.badge.up{background:#DCFCE7;color:#15803D;} .badge.down{background:#FEE2E2;color:#B91C1C;}
.hero .badge.up{background:rgba(74,222,128,.16);color:#4ADE80;}
.hero .badge.down{background:rgba(248,113,113,.16);color:#F87171;}

/* Controles */
label p{font-size:13px !important;font-weight:600 !important;color:#475569 !important;}
div[data-baseweb="select"]>div,div[data-baseweb="input"],div[data-baseweb="base-input"]{
 border-radius:10px !important;background:#fff !important;border-color:var(--line) !important;}
.stTabs [data-baseweb="tab-list"]{gap:6px;background:#E8ECF4;padding:5px;border-radius:12px;margin-bottom:12px;}
.stTabs [data-baseweb="tab"]{border-radius:9px;height:40px;padding:0 20px;font-weight:600;color:var(--muted);}
.stTabs [aria-selected="true"]{background:#fff;color:var(--ink);box-shadow:0 1px 3px rgba(15,23,42,.12);}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none;}

/* Cartões */
.card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:24px;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.pair{font-weight:700;font-size:15px;} .sub{color:var(--muted);font-size:13px;margin-top:2px;}
.price{font-family:'JetBrains Mono',monospace;font-size:clamp(30px,6vw,44px);font-weight:700;letter-spacing:-.02em;margin:14px 0 4px;}
.price .badge{font-family:'Inter',sans-serif;vertical-align:middle;margin-left:10px;font-size:13px;}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-top:18px;}
.stat{background:#F8FAFC;border:1px solid #EEF2F7;border-radius:12px;padding:12px 14px;}
.stat small{display:block;color:var(--muted);font-size:12px;font-weight:500;margin-bottom:4px;}
.stat b{font-family:'JetBrains Mono',monospace;font-size:16px;}
.foot{text-align:center;color:var(--muted);font-size:12px;margin-top:28px;line-height:1.6;}
details[data-testid="stExpander"]{border-radius:12px;border-color:var(--line);background:#fff;}
</style>
""",
    unsafe_allow_html=True,
)


def fmt(v, casas=None):
    """Formato brasileiro: 1.234,56"""
    if casas is None:
        casas = 2 if abs(v) >= 100 else 4
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def badge(pct):
    cls, seta = ("up", "▲") if pct >= 0 else ("down", "▼")
    return f"<span class='badge {cls}'>{seta} {fmt(abs(pct), 2)}%</span>"


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
        e = resposta.json()
        return None, f"Status: {e.get('status')} · Código: {e.get('code')} · {e.get('message')}"
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


def stat(rotulo, valor):
    return f"<div class='stat'><small>{rotulo}</small><b>{valor}</b></div>"


# ---------- Hero com painel de moedas ----------
painel, _ = consultar_moeda(",".join(PAINEL))
cards, hora = "", "--:--"
if painel:
    hora = list(painel.values())[0]["create_date"][11:16]
    for i in painel.values():
        cards += (
            f"<div class='tk'><div class='tk-code'>{i['code']}/{i['codein']}</div>"
            f"<div class='tk-val'>R$ {fmt(float(i['bid']))}</div>{badge(float(i['pctChange']))}</div>"
        )
st.markdown(
    f"<div class='hero'><div class='hero-top'><span class='logo'>◈ Câmbio</span>"
    f"<span class='live'><i></i>Atualizado às {hora}</span></div>"
    f"<h1>Painel de câmbio</h1><p>Cotações em tempo real, conversão de valores e histórico.</p>"
    f"<div class='tks'>{cards}</div></div>",
    unsafe_allow_html=True,
)

# ---------- Seleção da moeda ----------
col_a, col_b = st.columns([3, 2])
escolha = col_a.selectbox("Moeda", list(MOEDAS.keys()))
moeda = MOEDAS[escolha]
if moeda is None:
    moeda = col_b.text_input("Código da moeda", placeholder="Ex: CAD-BRL")
moeda = moeda.strip().upper()

if not moeda:
    st.info("Digite o código da moeda para continuar.")
    st.stop()

dados_api, erro = consultar_moeda(moeda)
aba_cotacao, aba_conversor, aba_historico = st.tabs(["Cotação", "Conversor", "Histórico"])

# ---------- Cotação ----------
with aba_cotacao:
    if not dados_api:
        st.error(f"Erro ao consultar a moeda {html.escape(moeda)}. Verifique se o formato está correto.")
        if erro:
            st.caption(erro)
    else:
        d = dados_api[list(dados_api)[0]]
        st.markdown(
            f"<div class='card'><div class='pair'>{d['code']}/{d['codein']}</div>"
            f"<div class='sub'>{html.escape(d['name'])}</div>"
            f"<div class='price'>R$ {fmt(float(d['bid']))}{badge(float(d['pctChange']))}</div>"
            f"<div class='sub'>Atualizado em {d['create_date']}</div>"
            f"<div class='stats'>{stat('Máxima', fmt(float(d['high'])))}{stat('Mínima', fmt(float(d['low'])))}"
            f"{stat('Compra', fmt(float(d['bid'])))}{stat('Venda', fmt(float(d['ask'])))}</div></div>",
            unsafe_allow_html=True,
        )
        with st.expander("Ver resposta completa da API"):
            st.json(dados_api)

# ---------- Conversor ----------
with aba_conversor:
    if not dados_api:
        st.error(erro or "Não foi possível obter a cotação.")
    else:
        cotacao = float(dados_api[list(dados_api)[0]]["bid"])
        codigo = moeda.split("-")[0]
        c1, c2 = st.columns([2, 3])
        valor = c1.number_input("Valor", min_value=0.0, value=100.0, step=10.0, format="%.2f")
        sentido = c2.radio("Sentido", [f"{codigo} → BRL", f"BRL → {codigo}"], horizontal=True)
        if sentido.startswith(codigo):
            rotulo, resultado = f"{fmt(valor, 2)} {codigo} valem", f"R$ {fmt(valor * cotacao, 2)}"
        else:
            rotulo, resultado = f"R$ {fmt(valor, 2)} compram", f"{fmt(valor / cotacao, 6)} {codigo}"
        st.markdown(
            f"<div class='card'><div class='sub'>{rotulo}</div><div class='price'>{resultado}</div>"
            f"<div class='sub'>Cotação usada: 1 {codigo} = R$ {fmt(cotacao)} · atualizada a cada minuto</div></div>",
            unsafe_allow_html=True,
        )

# ---------- Histórico ----------
with aba_historico:
    dias = st.select_slider("Período (dias)", options=[7, 15, 30, 60, 90], value=15)
    df, erro_h = consultar_historico(moeda, dias)
    if df is None:
        st.error(erro_h)
    else:
        v = df["Valor (R$)"]
        var = (v.iloc[-1] / v.iloc[0] - 1) * 100
        st.markdown(
            f"<div class='stats' style='margin:6px 0 14px'>{stat('Máxima', 'R$ ' + fmt(v.max()))}"
            f"{stat('Mínima', 'R$ ' + fmt(v.min()))}{stat('Média', 'R$ ' + fmt(v.mean()))}"
            f"<div class='stat'><small>Variação no período</small>{badge(var)}</div></div>",
            unsafe_allow_html=True,
        )
        st.area_chart(df, color="#0F9D8F", height=320)

st.markdown(
    "<div class='foot'>Fonte: AwesomeAPI · Cotações com atraso de até 1 minuto.<br>"
    "Informativo, não constitui recomendação de investimento.</div>",
    unsafe_allow_html=True,
)