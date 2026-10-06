"""Câmbio - painel de cotação, conversão e histórico (Streamlit).
Rodar no terminal: python -m streamlit run app.py
"""
import html

import altair as alt
import pandas as pd
import requests
import streamlit as st

RESERVA = {
    "USD-BRL": "Dólar Americano/Real Brasileiro",
    "EUR-BRL": "Euro/Real Brasileiro",
    "GBP-BRL": "Libra Esterlina/Real Brasileiro",
    "ARS-BRL": "Peso Argentino/Real Brasileiro",
    "BTC-BRL": "Bitcoin/Real Brasileiro",
    "ETH-BRL": "Ethereum/Real Brasileiro",
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
[data-baseweb="tab-list"]{gap:6px;background:#E8ECF4;padding:5px;border-radius:12px;margin-bottom:12px;}
[data-baseweb="tab"]{border-radius:9px;height:40px;padding:0 20px;font-weight:600;color:var(--muted);}
[aria-selected="true"]{background:#fff;color:var(--ink);box-shadow:0 1px 3px rgba(15,23,42,.12);}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none;}

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
        a = abs(v)
        casas = 2 if a >= 100 else 4 if a >= 1 else 6 if a >= 0.01 else 8
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def valor_moeda(v, cod):
    """R$ 1,00 para BRL; '1,0000 EUR' para as demais."""
    txt = fmt(v)
    return f"R$ {txt}" if cod == "BRL" else f"{txt} {cod}"


def badge(pct):
    cls, seta = ("up", "▲") if pct >= 0 else ("down", "▼")
    return f"<span class='badge {cls}'>{seta} {fmt(abs(pct), 2)}%</span>"


@st.cache_data(ttl=86400)
def listar_moedas():
    """Todos os pares disponíveis na API: {'USD-BRL': 'Dólar Americano/Real Brasileiro', ...}"""
    try:
        resposta = requests.get(f"{BASE_URL}/available", timeout=10)
        if resposta.status_code == 200 and resposta.json():
            return resposta.json()
    except requests.RequestException:
        pass
    return None


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


DIAS = ["seg.", "ter.", "qua.", "qui.", "sex.", "sáb.", "dom."]
MESES = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]


def grafico(df, subiu, contra):
    """Linha com degradê, grade horizontal, eixo Y ajustado e marcador no hover."""
    cor, topo = ("#16A34A", "rgba(22,163,74,0.30)") if subiu else ("#EF4444", "rgba(239,68,68,0.30)")
    d = df.reset_index()
    d["Data"] = pd.to_datetime(d["Data"])
    d["Valor"] = d["Valor (R$)"]
    d["Dia"] = d["Data"].apply(lambda x: f"{DIAS[x.weekday()]}, {x.day:02d} de {MESES[x.month - 1]}")
    d["Texto"] = d["Valor"].apply(lambda x: valor_moeda(x, contra))

    lo, hi = float(d["Valor"].min()), float(d["Valor"].max())
    pad = (hi - lo) * 0.2 or hi * 0.01
    casas = 2 if (hi - lo) >= 0.1 or hi >= 100 else (4 if hi >= 1 else 6 if hi >= 0.01 else 8)
    # separadores no padrão brasileiro nos rótulos do eixo
    rotulo = (
        "replace(replace(replace(format(datum.value, ',." + str(casas) + "f'), /,/g, '#'), /\\./g, ','), /#/g, '.')"
    )

    base = alt.Chart(d).encode(
        x=alt.X("Data:T", axis=alt.Axis(title=None, format="%d/%m", grid=False, domain=False, ticks=False, labelAngle=0, tickCount=6)),
        y=alt.Y(
            "Valor:Q",
            scale=alt.Scale(domain=[lo - pad, hi + pad], nice=False),
            axis=alt.Axis(title=None, grid=True, gridColor="#E2E8F0", domain=False, ticks=False, labelExpr=rotulo),
        ),
    )
    gradiente = alt.Gradient(
        gradient="linear",
        stops=[alt.GradientStop(color="rgba(255,255,255,0)", offset=0), alt.GradientStop(color=topo, offset=1)],
        x1=1, x2=1, y1=1, y2=0,
    )
    area = base.mark_area(clip=True, interpolate="linear", color=gradiente, line={"color": cor, "strokeWidth": 2.2})

    nearest = alt.selection_point(nearest=True, on="mouseover", fields=["Data"], empty=False, clear="mouseout")
    selectors = alt.Chart(d).mark_point().encode(x="Data:T", opacity=alt.value(0)).add_params(nearest)
    pontos = base.mark_point(filled=True, size=90, color=cor).encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0))
    )
    regua = (
        alt.Chart(d)
        .mark_rule(color="#94A3B8", strokeDash=[3, 3])
        .encode(x="Data:T", tooltip=[alt.Tooltip("Texto:N", title="Valor"), alt.Tooltip("Dia:N", title="Data")])
        .transform_filter(nearest)
    )
    return (
        alt.layer(area, selectors, pontos, regua)
        .properties(width="container", height=320)
        .configure_view(stroke=None)
        .configure_axis(labelFont="Inter", labelColor="#64748B", labelFontSize=12)
    )


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
pares = listar_moedas()
if not pares:
    pares = RESERVA
    st.warning("Não foi possível carregar a lista completa de moedas. Exibindo as principais.")
codigos = sorted(pares, key=lambda k: (not k.endswith("-BRL"), k))  # pares com real primeiro
moeda = st.selectbox(
    f"Moeda ({len(codigos)} pares disponíveis · digite para buscar)",
    codigos,
    index=codigos.index("USD-BRL") if "USD-BRL" in codigos else 0,
    format_func=lambda k: f"{k} · {pares[k]}",
)
codigo, contra = moeda.split("-")

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
            f"<div class='price'>{valor_moeda(float(d['bid']), d['codein'])}{badge(float(d['pctChange']))}</div>"
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
        opcoes = [f"{codigo} → {contra}", f"{contra} → {codigo}"]
        c1, c2 = st.columns([2, 3])
        valor = c1.number_input("Valor", min_value=0.0, value=100.0, step=10.0, format="%.2f")
        sentido = c2.radio("Sentido", opcoes, horizontal=True)
        if sentido == opcoes[0]:
            rotulo, resultado = f"{fmt(valor, 2)} {codigo} valem", valor_moeda(valor * cotacao, contra)
        else:
            rotulo = f"{fmt(valor, 2)} {contra} compram"
            resultado = f"{fmt(valor / cotacao)} {codigo}" if cotacao else "—"
        st.markdown(
            f"<div class='card'><div class='sub'>{rotulo}</div><div class='price'>{resultado}</div>"
            f"<div class='sub'>Cotação usada: 1 {codigo} = {valor_moeda(cotacao, contra)} · atualizada a cada minuto</div></div>",
            unsafe_allow_html=True,
        )

# ---------- Histórico ----------
with aba_historico:
    periodos = [7, 15, 30, 60, 90]
    if hasattr(st, "segmented_control"):
        dias = st.segmented_control(
            "Período", periodos, default=30, format_func=lambda n: f"{n}D", label_visibility="collapsed"
        ) or 30
    else:
        dias = st.select_slider("Período (dias)", options=periodos, value=30)
    df, erro_h = consultar_historico(moeda, dias)
    if df is None:
        st.error(erro_h)
    else:
        v = df["Valor (R$)"]
        var = (v.iloc[-1] / v.iloc[0] - 1) * 100
        st.markdown(
            f"<div class='stats' style='margin:6px 0 14px'>{stat('Máxima', valor_moeda(v.max(), contra))}"
            f"{stat('Mínima', valor_moeda(v.min(), contra))}{stat('Média', valor_moeda(v.mean(), contra))}"
            f"<div class='stat'><small>Variação no período</small>{badge(var)}</div></div>",
            unsafe_allow_html=True,
        )
        st.altair_chart(grafico(df, var >= 0, contra))

st.markdown(
    "<div class='foot'>Fonte: AwesomeAPI · Cotações com atraso de até 1 minuto.<br>"
    "Informativo, não constitui recomendação de investimento.</div>",
    unsafe_allow_html=True,
)