"""
dashboard/app.py — FinTech NovaAI · Dashboard · Hackathon 2026
===============================================================
FUENTE DE DATOS — 100 % desde Parquet, sin datos inventados:
  • data/gold/user_360.parquet   → 489 usuarios, 39 features
  • data/silver/events_silver.parquet → 2 000 eventos, 40 columnas

AGENTE IA — Prioridad de fallback:
  1. 🔥 Mistral-7B  — si MISTRAL_BASE_URL está configurado (cluster GPU Tesla T4)
  2. 🦙 LLaMA       — si LLAMA_BASE_URL está configurado
  3. 📋 Offline     — reglas determinísticas (siempre disponible)
"""
import sys, os, time, requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG DE PÁGINA
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="FinTech NovaAI",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Variables globales ── */
:root {
    --accent:   #00d4ff;
    --accent2:  #7c6cff;
    --accent3:  #00ffb2;
    --danger:   #ff4d6d;
    --warn:     #ffb830;
    --surface:  #10141f;
    --surface2: #161c2e;
    --border:   #1e2740;
    --text:     #e2e8f0;
    --muted:    #64748b;
    --dim:      #94a3b8;
}

/* ── Fuentes globales ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0a0d14 !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stRadio label {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    padding: 6px 0;
    cursor: pointer;
}

/* ── Fondo principal con grid ── */
.stApp {
    background: #0a0d14;
    background-image:
        linear-gradient(rgba(0,212,255,0.012) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.012) 1px, transparent 1px);
    background-size: 40px 40px;
}

/* ── Títulos con gradiente ── */
h1 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #ffffff 30%, var(--accent) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}
h2, h3 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    color: #e2e8f0 !important;
}

/* ── KPI cards (métricas) ── */
[data-testid="metric-container"] {
    background: rgba(16, 20, 31, 0.9) !important;
    border: 1px solid var(--border) !important;
    border-top: 2px solid var(--accent2) !important;
    border-radius: 10px !important;
    padding: 16px !important;
    backdrop-filter: blur(8px);
    transition: border-color 0.2s, transform 0.15s;
}
[data-testid="metric-container"]:hover {
    border-top-color: var(--accent) !important;
    transform: translateY(-1px);
}
[data-testid="metric-container"] label {
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: var(--muted) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
}

/* ── Tarjetas de insight ── */
.ins-card {
    padding: 14px 18px;
    border-radius: 8px;
    margin: 6px 0;
    border-left: 3px solid;
    font-size: 13.5px;
    line-height: 1.6;
    transition: transform 0.15s;
}
.ins-card:hover { transform: translateX(3px); }
.ins-critico     { border-color: #ff4d6d; background: rgba(255,77,109,0.07); }
.ins-alto        { border-color: #ffb830; background: rgba(255,184,48,0.07); }
.ins-medio       { border-color: #00d4ff; background: rgba(0,212,255,0.07); }
.ins-oportunidad { border-color: #00ffb2; background: rgba(0,255,178,0.07); }
.ins-info        { border-color: #64748b; background: rgba(100,116,139,0.07); }

/* ── KPI lateral ── */
.kpi-side {
    background: rgba(124,108,255,0.08);
    border: 1px solid rgba(124,108,255,0.2);
    border-radius: 8px;
    padding: 9px 13px;
    margin: 4px 0;
    font-size: 12.5px;
    font-family: 'DM Mono', monospace;
    transition: background 0.15s;
}
.kpi-side:hover { background: rgba(124,108,255,0.14); }

/* ── Badge de segmento ── */
.seg-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.05em;
}

/* ── Tarjeta de segmento (perfil) ── */
.seg-card {
    border-radius: 10px;
    padding: 16px 20px;
    margin: 8px 0 16px;
    border-left: 5px solid;
}

/* ── Flag de riesgo ── */
.flag {
    text-align: center;
    padding: 12px 8px;
    border-radius: 8px;
    border: 1px solid;
    margin: 3px;
    transition: transform 0.15s;
}
.flag:hover { transform: scale(1.04); }

/* ── Panel del agente ── */
.agent-status-card {
    border-radius: 10px;
    padding: 14px 18px;
    margin: 8px 0;
    border: 1px solid;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.agent-online  { border-color: rgba(0,255,178,0.35); background: rgba(0,255,178,0.05); }
.agent-offline { border-color: rgba(100,116,139,0.35); background: rgba(100,116,139,0.05); }
.agent-warn    { border-color: rgba(255,184,48,0.35);  background: rgba(255,184,48,0.05); }

/* ── Latency badge ── */
.latency-badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 20px;
    margin-left: 8px;
    vertical-align: middle;
}
.latency-fast   { background: rgba(0,255,178,0.12); color: #00ffb2; border: 1px solid rgba(0,255,178,0.25); }
.latency-medium { background: rgba(255,184,48,0.12); color: #ffb830; border: 1px solid rgba(255,184,48,0.25); }
.latency-slow   { background: rgba(255,77,109,0.12); color: #ff4d6d; border: 1px solid rgba(255,77,109,0.25); }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: rgba(16, 20, 31, 0.8) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    margin: 6px 0 !important;
}

/* ── Botones quick questions ── */
.stButton > button {
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    border: 1px solid var(--border) !important;
    background: rgba(16,20,31,0.8) !important;
    color: var(--dim) !important;
    border-radius: 6px !important;
    transition: all 0.15s !important;
    letter-spacing: 0.03em;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: rgba(0,212,255,0.05) !important;
}

/* ── Divider con color ── */
hr { border-color: var(--border) !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    background: rgba(16,20,31,0.5) !important;
}

/* ── Section header ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
}
.section-header::before {
    content: '';
    width: 3px;
    height: 22px;
    background: var(--accent);
    border-radius: 2px;
    flex-shrink: 0;
}

/* ── Pipeline flow ── */
.flow-row {
    display: flex;
    align-items: center;
    gap: 0;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 16px 20px;
    background: rgba(16,20,31,0.6);
    border: 1px solid var(--border);
    border-radius: 10px;
    margin: 12px 0;
}
.flow-box {
    padding: 8px 14px;
    border-radius: 6px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    text-align: center;
    flex-shrink: 0;
    min-width: 80px;
}
.flow-arrow { padding: 0 8px; color: var(--muted); font-size: 14px; }
.flow-bronze { background: rgba(205,127,50,0.12); border: 1px solid rgba(205,127,50,0.25); color: #cd7f32; }
.flow-silver { background: rgba(192,192,192,0.08); border: 1px solid rgba(192,192,192,0.18); color: #c0c0c0; }
.flow-gold   { background: rgba(255,184,0,0.10);  border: 1px solid rgba(255,184,0,0.22);  color: #ffb800; }
.flow-ml     { background: rgba(124,108,255,0.12); border: 1px solid rgba(124,108,255,0.25); color: #7c6cff; }
.flow-ai     { background: rgba(0,212,255,0.08);  border: 1px solid rgba(0,212,255,0.20);  color: #00d4ff; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES — CONEXIÓN AL AGENTE IA
# ═══════════════════════════════════════════════════════════════════════════
def detect_agent_mode() -> dict:
    """
    Detecta qué backend de IA está disponible y retorna su estado.
    Prioridad: Mistral → LLaMA → Offline
    """
    mistral_url = os.environ.get("MISTRAL_BASE_URL", "").strip().rstrip("/")
    llama_url   = os.environ.get("LLAMA_BASE_URL", "").strip().rstrip("/")

    if mistral_url:
        try:
            t0 = time.time()
            r  = requests.get(f"{mistral_url}/v1/models", timeout=4)
            ms = int((time.time() - t0) * 1000)
            if r.status_code == 200:
                models = [m.get("id", "?") for m in r.json().get("data", [])]
                return {
                    "mode": "mistral", "ok": True, "latency_ms": ms,
                    "url": mistral_url,
                    "label": "🔥 Mistral-7B (Tesla T4)",
                    "models": models or ["mistral-fintech"],
                    "color": "#00ffb2",
                }
        except Exception:
            pass

    if llama_url:
        try:
            t0 = time.time()
            r  = requests.get(f"{llama_url}/v1/models", timeout=4)
            ms = int((time.time() - t0) * 1000)
            if r.status_code == 200:
                return {
                    "mode": "llama", "ok": True, "latency_ms": ms,
                    "url": llama_url,
                    "label": "🦙 LLaMA (vLLM)",
                    "models": ["llama"],
                    "color": "#ffb830",
                }
        except Exception:
            pass

    return {
        "mode": "offline", "ok": False, "latency_ms": 0,
        "url": "",
        "label": "📋 Modo Offline (reglas)",
        "models": [],
        "color": "#64748b",
    }


def query_llm(prompt: str, system: str, base_url: str, model: str = "mistral-fintech",
              max_tokens: int = 512, temperature: float = 0.3) -> tuple[str, float]:
    """Llama al endpoint OpenAI-compatible. Retorna (respuesta, latencia_ms)."""
    t0 = time.time()
    resp = requests.post(
        f"{base_url}/v1/chat/completions",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=60,
    )
    ms = (time.time() - t0) * 1000
    if resp.status_code == 200:
        content = resp.json()["choices"][0]["message"]["content"]
        return content.strip(), ms
    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")


def build_user_context(u_row: pd.Series) -> str:
    """Construye el contexto financiero del usuario para el LLM."""
    return f"""
Usuario: {u_row.get('name','N/A')} (ID: {u_row.name if hasattr(u_row,'name') else 'N/A'})
Segmento: {u_row.get('segment_name','N/A')} {u_row.get('segment_icon','')}
Gasto total: ${u_row.get('total_spent',0):,.0f} COP
Balance actual: ${u_row.get('current_balance',0):,.0f} COP
Balance mínimo: ${u_row.get('min_balance',0):,.0f} COP
Balance máximo: ${u_row.get('max_balance',0):,.0f} COP
Total recargado: ${u_row.get('total_added',0):,.0f} COP
Total retirado: ${u_row.get('total_withdrawn',0):,.0f} COP
N° transacciones: {int(u_row.get('n_transactions',0))}
Tasa de fallos: {u_row.get('fail_ratio',0)*100:.1f}%
Días activos: {int(u_row.get('unique_days_active',0))}
Frecuencia de gasto: {u_row.get('spending_frequency',0):.2f} tx/día
Ratio gasto/recarga: {u_row.get('spend_vs_add_ratio',0):.2f}
Estrés financiero: {'SÍ' if u_row.get('financial_stress',0)==1 else 'No'}
Alto riesgo: {'SÍ' if u_row.get('is_high_risk',0)==1 else 'No'}
Balance bajo: {'SÍ' if u_row.get('is_low_balance',0)==1 else 'No'}
Dormido: {'SÍ' if u_row.get('is_dormant',0)==1 else 'No'}
Alto valor: {'SÍ' if u_row.get('is_high_value',0)==1 else 'No'}
Canal preferido: {u_row.get('preferred_channel','N/A')}
Dispositivo: {u_row.get('preferred_device','N/A')}
Hora pico: {u_row.get('peak_hour','N/A')}:00
""".strip()


FINTECH_SYSTEM = """Eres un analista financiero experto de FinTech NovaAI.
Analizas perfiles de usuarios de una plataforma fintech colombiana.
Tus respuestas son en español, concisas, directas y accionables.
Usa datos concretos del contexto del usuario. Evita repetir el contexto literal.
Estructura tus respuestas con emojis y bullet points cuando sea útil.
Máximo 3 párrafos o 5 bullets."""


def answer_offline(question: str, u_row: pd.Series) -> str:
    """Fallback con reglas determinísticas cuando no hay LLM disponible."""
    q = question.lower()
    name = u_row.get('name', 'el usuario')
    spent = u_row.get('total_spent', 0)
    balance = u_row.get('current_balance', 0)
    fail = u_row.get('fail_ratio', 0) * 100
    seg = u_row.get('segment_name', 'N/A')

    if any(w in q for w in ['gasto', 'gast', 'compra', 'categoría', 'más']):
        return (
            f"💳 **Análisis de gasto de {name}**\n\n"
            f"- Gasto total acumulado: **${spent:,.0f} COP**\n"
            f"- Segmento ML: **{seg}** (KMeans k=4)\n"
            f"- Tasa de fallos en transacciones: **{fail:.1f}%**\n\n"
            f"Para ver el desglose por categoría, revisa el gráfico de radar en la sección Perfil 360°."
        )
    if any(w in q for w in ['riesgo', 'peligro', 'stress', 'estrés', 'seguro']):
        flags = []
        if u_row.get('is_high_risk', 0): flags.append("⚠️ Marcado como **alto riesgo**")
        if u_row.get('financial_stress', 0): flags.append("💸 **Estrés financiero** detectado")
        if u_row.get('is_low_balance', 0): flags.append("📉 **Balance bajo** — posible iliquidez")
        if u_row.get('is_dormant', 0): flags.append("😴 Usuario **dormido** — posible churn")
        if not flags: flags = ["✅ Sin señales críticas de riesgo detectadas"]
        return f"🔍 **Señales de riesgo para {name}:**\n\n" + "\n".join(f"- {f}" for f in flags)
    if any(w in q for w in ['balance', 'saldo', 'dinero', 'cuenta']):
        return (
            f"🏦 **Balance de {name}**\n\n"
            f"- Balance actual: **${balance:,.0f} COP**\n"
            f"- Total recargado: **${u_row.get('total_added',0):,.0f} COP**\n"
            f"- Total retirado: **${u_row.get('total_withdrawn',0):,.0f} COP**\n"
            f"- Ratio gasto/recarga: **{u_row.get('spend_vs_add_ratio',0):.2f}**"
        )
    return (
        f"📊 **Resumen de {name}**\n\n"
        f"- Segmento: **{seg}** {u_row.get('segment_icon','')}\n"
        f"- Gasto total: **${spent:,.0f} COP** · "
        f"Balance: **${balance:,.0f} COP**\n"
        f"- Transacciones: **{int(u_row.get('n_transactions',0))}** · "
        f"Tasa fallos: **{fail:.1f}%**\n"
        f"- Días activos: **{int(u_row.get('unique_days_active',0))}**\n\n"
        f"💡 *Modo offline activo — configura MISTRAL_BASE_URL para respuestas con IA generativa.*"
    )


# ═══════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="⚙️ Cargando pipeline Medallion…")
def load_all_data() -> dict:
    from config import GOLD_FILE, SILVER_FILE

    if GOLD_FILE.exists() and SILVER_FILE.exists():
        gold   = pd.read_parquet(GOLD_FILE)
        silver = pd.read_parquet(SILVER_FILE)
    else:
        from pipeline.bronze import run_bronze
        from pipeline.silver import run_silver
        from pipeline.gold   import run_gold
        bronze = run_bronze(enrich=False)
        silver = run_silver(bronze)
        gold   = run_gold(silver)

    from models.clustering import run_clustering
    from models.anomaly    import run_anomaly_detection
    from insights.engine   import generate_portfolio_insights

    gold, _, _, sil, cluster_labels = run_clustering(gold)
    silver_a, n_anom, top_anom      = run_anomaly_detection(silver)
    insights = generate_portfolio_insights(gold, top_anom)

    seg_map = gold.set_index("userId")["segment_name"].to_dict()
    silver_a["segment_name"] = silver_a["userId"].map(seg_map)

    return dict(
        gold=gold, silver=silver_a,
        top_anomalies=top_anom, n_anomalies=n_anom,
        silhouette=sil, cluster_labels=cluster_labels,
        insights=insights,
    )


D      = load_all_data()
gold   = D["gold"]
silver = D["silver"]
top_a  = D["top_anomalies"]

CITY_COL  = "user_city" if "user_city" in gold.columns else "city"
CAT_COLS  = [c for c in gold.columns if c.startswith("cat_") and not c.endswith("_ratio")]
CAT_LABEL = {c: c.replace("cat_", "").capitalize() for c in CAT_COLS}
ALL_SEGS  = sorted(gold["segment_name"].dropna().unique())
SEG_COLOR = (
    gold.drop_duplicates("segment_name")
    .set_index("segment_name")["segment_color"].to_dict()
)
ALL_CITIES = sorted(gold[CITY_COL].dropna().unique()) if CITY_COL in gold.columns else []


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Logo / header
    st.markdown("""
    <div style="padding:4px 0 16px">
        <div style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800;
             background:linear-gradient(135deg,#fff 30%,#00d4ff 100%);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;
             background-clip:text;letter-spacing:-0.01em">
            FinTech NovaAI
        </div>
        <div style="font-family:'DM Mono',monospace;font-size:10px;
             color:#64748b;letter-spacing:0.15em;text-transform:uppercase;margin-top:3px">
            Hackathon 2026 · Medallion
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    section = st.radio("", [
        "🏠  KPIs Globales",
        "👤  Perfil 360°",
        "🎯  Segmentación ML",
        "🚨  Anomalías",
        "🤖  Agente IA",
    ], label_visibility="collapsed")

    st.divider()
    st.markdown(
        "<div style='font-family:DM Mono,monospace;font-size:10px;"
        "letter-spacing:0.15em;text-transform:uppercase;color:#64748b;"
        "margin-bottom:8px'>Filtros Globales</div>",
        unsafe_allow_html=True,
    )

    seg_sel = st.multiselect("Segmentos", ALL_SEGS, default=ALL_SEGS)
    if ALL_CITIES:
        city_sel = st.multiselect("Ciudades", ALL_CITIES, default=ALL_CITIES)
    else:
        city_sel = []
    only_risk = st.toggle("⚠️ Solo usuarios en riesgo", value=False)

    gf = gold.copy()
    if seg_sel:   gf = gf[gf["segment_name"].isin(seg_sel)]
    if city_sel and CITY_COL in gf.columns:
        gf = gf[gf[CITY_COL].isin(city_sel)]
    if only_risk: gf = gf[gf["is_high_risk"] == 1]

    total_fin = int(silver[silver["userId"].isin(gf["userId"])]["is_financial"].sum())
    fail_pct  = gf["n_failed"].sum() / max(gf["n_transactions"].sum(), 1) * 100

    st.divider()
    st.markdown(f"""
    <div class="kpi-side">👥 <b>{len(gf):,}</b> usuarios</div>
    <div class="kpi-side">💳 <b>{total_fin:,}</b> transacciones financieras</div>
    <div class="kpi-side">💰 <b>${gf['total_spent'].sum()/1e6:.1f}M</b> COP</div>
    <div class="kpi-side">⚠️ Fallos <b>{fail_pct:.1f}%</b></div>
    <div class="kpi-side">📊 Silhouette <b>{D['silhouette']:.3f}</b></div>
    """, unsafe_allow_html=True)

    # ── Configuración del Agente IA ──────────────────────────────────────
    st.divider()
    st.markdown(
        "<div style='font-family:DM Mono,monospace;font-size:10px;"
        "letter-spacing:0.15em;text-transform:uppercase;color:#64748b;"
        "margin-bottom:8px'>Agente IA</div>",
        unsafe_allow_html=True,
    )

    m_url = st.text_input(
        "URL Cluster Mistral-7B",
        value=os.environ.get("MISTRAL_BASE_URL", ""),
        placeholder="http://IP:PUERTO",
        help="Servidor vLLM compatible con OpenAI API · Tesla T4",
    )
    if m_url:
        os.environ["MISTRAL_BASE_URL"] = m_url.strip().rstrip("/")

    llama_url_input = st.text_input(
        "URL Fallback LLaMA",
        value=os.environ.get("LLAMA_BASE_URL", ""),
        placeholder="http://localhost:8080",
        help="Alternativa si Mistral no está disponible",
    )
    if llama_url_input:
        os.environ["LLAMA_BASE_URL"] = llama_url_input.strip().rstrip("/")

    # Estado del agente detectado en tiempo real
    if "agent_info_cache" not in st.session_state:
        st.session_state.agent_info_cache = None
        st.session_state.agent_last_check = 0

    now = time.time()
    if now - st.session_state.agent_last_check > 30 or st.button("🔄 Test conexión"):
        st.session_state.agent_info_cache = detect_agent_mode()
        st.session_state.agent_last_check = now

    ai = st.session_state.agent_info_cache or {"mode": "offline", "ok": False, "label": "📋 Offline", "color": "#64748b", "latency_ms": 0}
    css_class = "agent-online" if ai["ok"] else "agent-offline"
    lat_html = ""
    if ai["ok"] and ai["latency_ms"] > 0:
        ms = ai["latency_ms"]
        lat_class = "latency-fast" if ms < 300 else ("latency-medium" if ms < 1000 else "latency-slow")
        lat_html = f'<span class="latency-badge {lat_class}">{ms:.0f}ms</span>'
    st.markdown(f"""
    <div class="agent-status-card {css_class}">
        <span style="color:{ai['color']};font-size:15px">{'●' if ai['ok'] else '○'}</span>
        <span style="color:{ai['color']}">{ai['label']}</span>
        {lat_html}
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — KPIs GLOBALES
# ═══════════════════════════════════════════════════════════════════════════
if section == "🏠  KPIs Globales":
    st.title("KPIs Globales del Portafolio")

    # Pipeline flow visual
    st.markdown("""
    <div class="flow-row">
        <div class="flow-box flow-bronze">🥉 BRONZE<br><small>JSON→Parquet</small></div>
        <div class="flow-arrow">→</div>
        <div class="flow-box flow-silver">🥈 SILVER<br><small>Limpieza+FX</small></div>
        <div class="flow-arrow">→</div>
        <div class="flow-box flow-gold">🥇 GOLD<br><small>User 360°</small></div>
        <div class="flow-arrow">→</div>
        <div class="flow-box flow-ml">🧠 KMeans k=4<br><small>Segmentación</small></div>
        <div class="flow-arrow">→</div>
        <div class="flow-box flow-ml">🔍 IsoForest<br><small>Anomalías</small></div>
        <div class="flow-arrow">→</div>
        <div class="flow-box flow-ai">🤖 Agente IA<br><small>Mistral/Offline</small></div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("👥 Usuarios",       f"{len(gf):,}")
    c2.metric("💳 Transacciones",  f"{total_fin:,}")
    c3.metric("💰 Gasto Total",    f"${gf['total_spent'].sum()/1e6:.1f}M")
    c4.metric("🏦 Balance Medio",  f"${gf['current_balance'].mean():,.0f}")
    c5.metric("⚠️ Tasa Fallos",    f"{fail_pct:.1f}%",
              delta=f"{fail_pct-30:.1f}pp vs umbral", delta_color="inverse")
    c6.metric("🔍 Anomalías",      f"{D['n_anomalies']} tx")

    st.divider()

    col1, col2 = st.columns([3, 2])
    with col1:
        seg_df = gf["segment_name"].value_counts().reset_index()
        seg_df.columns = ["Segmento", "N"]
        fig_pie = px.pie(
            seg_df, values="N", names="Segmento",
            title=f"Segmentos ML — KMeans k=4 · Silhouette {D['silhouette']:.3f}",
            color="Segmento", color_discrete_map=SEG_COLOR, hole=0.44,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True, legend=dict(orientation="h", y=-0.25, font=dict(family="DM Mono")),
            margin=dict(t=50, b=60), font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        cat_df = gf[CAT_COLS].sum().reset_index()
        cat_df.columns = ["col", "Total"]
        cat_df["Categoría"] = cat_df["col"].map(CAT_LABEL)
        cat_df = cat_df.sort_values("Total", ascending=True)
        fig_bar = px.bar(
            cat_df, y="Categoría", x="Total", orientation="h",
            title="Gasto por Categoría (COP)",
            color="Total",
            color_continuous_scale=[[0, "#1e2740"], [0.5, "#7c6cff"], [1, "#00d4ff"]],
            text=cat_df["Total"].apply(lambda x: f"${x/1e6:.1f}M"),
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False, margin=dict(t=50, l=10),
            font=dict(family="DM Sans"), xaxis=dict(gridcolor="#1e2740"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        if CITY_COL in gf.columns:
            city_df = (
                gf.groupby(CITY_COL)
                .agg(usuarios=("userId","count"), gasto=("total_spent","sum"),
                     fallos=("fail_ratio","mean"))
                .reset_index().sort_values("usuarios", ascending=True).tail(10)
            )
            fig_city = px.bar(
                city_df, y=CITY_COL, x="usuarios", orientation="h",
                title="Usuarios por Ciudad", color="gasto",
                color_continuous_scale=[[0,"#1e3a8a"],[1,"#7c6cff"]],
                text="usuarios", labels={CITY_COL: "Ciudad"},
            )
            fig_city.update_traces(textposition="outside")
            fig_city.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False, margin=dict(t=50, l=10),
                font=dict(family="DM Sans"), xaxis=dict(gridcolor="#1e2740"),
            )
            st.plotly_chart(fig_city, use_container_width=True)

    with col4:
        rf  = ["is_high_risk","is_low_balance","is_dormant","financial_stress","is_high_value"]
        rl  = ["Alto Riesgo","Bal. Bajo","Dormido","Estrés Fin.","Alto Valor"]
        mat = [[gf[gf["segment_name"]==s][f].mean()*100 for f in rf] for s in ALL_SEGS]
        fig_heat = go.Figure(go.Heatmap(
            z=mat, x=rl, y=ALL_SEGS,
            colorscale=[[0,"#0f172a"],[0.5,"#7c6cff"],[1,"#ff4d6d"]],
            text=[[f"{v:.0f}%" for v in row] for row in mat],
            texttemplate="%{text}", showscale=True,
            colorbar=dict(title="% usuarios", thickness=12, tickfont=dict(family="DM Mono")),
        ))
        fig_heat.update_layout(
            title="Mapa de Riesgo por Segmento (%)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=50, l=10), font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()
    st.subheader("💡 Insights Automáticos del Portafolio")
    for ins in D["insights"]:
        st.markdown(f"""
        <div class="ins-card ins-{ins['nivel']}">
            <b style="font-family:'Syne',sans-serif">{ins['titulo']}</b><br>
            <span style="color:#cbd5e1">{ins['descripcion']}</span><br>
            <em style="color:#64748b;font-size:12px">→ {ins['accion']}</em>
        </div>""", unsafe_allow_html=True)

    with st.expander("💱 Enriquecimiento FX — datos reales del pipeline Silver"):
        ec = st.columns(3)
        if "usd_cop_rate" in silver.columns and silver["usd_cop_rate"].notna().any():
            ec[0].metric("💵 Tasa USD/COP", f"{silver['usd_cop_rate'].dropna().iloc[0]:,.0f}")
        if "btc_price_usd" in silver.columns and silver["btc_price_usd"].notna().any():
            ec[1].metric("₿ Precio BTC", f"${silver['btc_price_usd'].dropna().iloc[0]:,.0f} USD")
        if "amount_btc" in silver.columns:
            ec[2].metric("₿ Volumen BTC total", f"{silver['amount_btc'].sum():.4f} BTC")


# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — PERFIL 360°
# ═══════════════════════════════════════════════════════════════════════════
elif section == "👤  Perfil 360°":
    st.title("Vista 360° del Usuario")

    sel1, sel2, sel3 = st.columns([2, 3, 1])
    with sel1:
        seg_pre = st.selectbox("Filtrar por segmento", ["Todos"] + ALL_SEGS, key="seg_pre")
    with sel2:
        pool    = gold if seg_pre == "Todos" else gold[gold["segment_name"] == seg_pre]
        uid_map = {
            r["userId"]: f"{r['name']} ({r['userId']}) · {r.get('segment_name','?')}"
            for _, r in pool.iterrows()
        }
        uid = st.selectbox("Usuario", list(uid_map), format_func=lambda x: uid_map[x])
    with sel3:
        st.write(""); st.write("")
        if st.button("🎲 Aleatorio"):
            uid = __import__("random").choice(list(uid_map))

    u   = gold[gold["userId"] == uid].iloc[0]
    u_s = silver[silver["userId"] == uid]
    fin = u_s[u_s["is_financial"] == 1]
    sc  = u.get("segment_color", "#7c6cff")

    city_val    = u.get(CITY_COL, "N/A") if CITY_COL else "N/A"
    country_val = u.get("country", "Colombia")
    st.markdown(f"""
    <div class="seg-card" style="background:rgba(16,20,31,0.7);border-color:{sc}">
        <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
            <span style="font-size:2.4em;line-height:1">{u.get('segment_icon','👤')}</span>
            <div>
                <div style="font-family:'Syne',sans-serif;font-size:1.3em;font-weight:700;color:#fff">
                    {u.get('name','N/A')}
                    <span class="seg-badge" style="background:{sc}22;color:{sc};border:1px solid {sc}55;margin-left:8px">
                        {u.get('segment_name','N/A')}
                    </span>
                </div>
                <div style="font-family:'DM Mono',monospace;font-size:11px;color:#64748b;margin-top:4px">
                    {uid} &nbsp;·&nbsp; {city_val}, {country_val} &nbsp;·&nbsp;
                    {u.get('age','N/A')} años &nbsp;·&nbsp; {u.get('email','N/A')}
                </div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    kc = st.columns(5)
    kc[0].metric("💰 Gasto Total",    f"${u.get('total_spent',0):,.0f} COP")
    kc[1].metric("💳 Transacciones",  f"{int(u.get('n_transactions',0))}")
    kc[2].metric("🏦 Balance Actual", f"${u.get('current_balance',0):,.0f} COP")
    kc[3].metric("❌ Tasa Fallos",    f"{u.get('fail_ratio',0)*100:.1f}%",
                  delta=f"{u.get('fail_ratio',0)*100-30:.1f}pp", delta_color="inverse")
    kc[4].metric("📅 Días Activos",   f"{int(u.get('unique_days_active',0))}")

    bc = st.columns(4)
    bc[0].metric("📉 Balance Mín.", f"${u.get('min_balance',0):,.0f}")
    bc[1].metric("📈 Balance Máx.", f"${u.get('max_balance',0):,.0f}")
    bc[2].metric("💵 Recargado",    f"${u.get('total_added',0):,.0f}")
    bc[3].metric("💸 Retirado",     f"${u.get('total_withdrawn',0):,.0f}")

    ec = st.columns(3)
    ec[0].metric("📊 Ratio Gasto/Recarga", f"{u.get('spend_vs_add_ratio',0):.2f}")
    ec[1].metric("🔄 Frec. Gasto", f"{u.get('spending_frequency',0):.1f} tx/día")
    if "spend_per_txn" in u.index:
        ec[2].metric("💳 Gasto / Tx", f"${u.get('spend_per_txn',0):,.0f} COP")

    st.divider()

    gc1, gc2 = st.columns(2)
    with gc1:
        vals_u   = [u.get(c, 0) for c in CAT_COLS]
        seg_avg  = gold[gold["segment_name"] == u.get("segment_name","")][CAT_COLS].mean()
        cats_lbl = [CAT_LABEL[c] for c in CAT_COLS]

        fig_rad = go.Figure()
        if sum(vals_u) > 0:
            fig_rad.add_trace(go.Scatterpolar(
                r=vals_u + [vals_u[0]], theta=cats_lbl + [cats_lbl[0]],
                fill="toself", name=u.get("name",""),
                fillcolor="rgba(0,212,255,0.12)", line=dict(color="#00d4ff", width=2),
            ))
            fig_rad.add_trace(go.Scatterpolar(
                r=seg_avg.tolist() + [seg_avg.iloc[0]], theta=cats_lbl + [cats_lbl[0]],
                fill="toself", name=f"Promedio {u.get('segment_name','')}",
                fillcolor="rgba(124,108,255,0.10)", line=dict(color="#7c6cff", width=1, dash="dot"),
            ))
        fig_rad.update_layout(
            polar=dict(radialaxis=dict(visible=True, tickformat="$,.0f", gridcolor="#1e2740")),
            title="Gasto por Categoría vs Promedio del Segmento",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.2, font=dict(family="DM Mono")),
            margin=dict(t=50), font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_rad, use_container_width=True)

    with gc2:
        bal_df = pd.DataFrame({
            "Tipo": ["Mínimo", "Promedio", "Actual", "Máximo"],
            "COP":  [u.get("min_balance",0), u.get("avg_balance",0),
                     u.get("current_balance",0), u.get("max_balance",0)],
        })
        fig_bal = px.bar(
            bal_df, x="Tipo", y="COP", title="Historial de Balance",
            color="Tipo",
            color_discrete_sequence=["#ff4d6d","#ffb830","#00d4ff","#00ffb2"],
            text=bal_df["COP"].apply(lambda x: f"${x:,.0f}"),
        )
        fig_bal.update_traces(textposition="outside")
        fig_bal.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, margin=dict(t=50), font=dict(family="DM Sans"),
            yaxis=dict(gridcolor="#1e2740"),
        )
        st.plotly_chart(fig_bal, use_container_width=True)

    gc3, gc4 = st.columns(2)
    with gc3:
        cat_u = pd.DataFrame({
            "Categoría": [CAT_LABEL[c] for c in CAT_COLS],
            "Gasto":     [u.get(c, 0) for c in CAT_COLS],
        }).query("Gasto > 0")
        if len(cat_u) > 0:
            fig_don = px.pie(
                cat_u, values="Gasto", names="Categoría",
                title="Distribución del Gasto por Categoría", hole=0.5,
                color_discrete_sequence=["#00d4ff","#7c6cff","#00ffb2","#ffb830","#ff4d6d"],
            )
            fig_don.update_traces(textposition="inside", textinfo="percent+label")
            fig_don.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=50), font=dict(family="DM Sans"),
            )
            st.plotly_chart(fig_don, use_container_width=True)
        else:
            st.info("Este usuario no tiene gastos por categoría registrados.")

    with gc4:
        if len(fin) > 0:
            disp_cols = [c for c in ["event_type","amount","category","merchant",
                                     "event_status","time_slot","channel",
                                     "amount_cop","amount_btc"] if c in fin.columns]
            disp = fin[disp_cols].copy()
            if "amount"     in disp.columns: disp["amount"]     = disp["amount"].apply(lambda x: f"${x:,.0f}")
            if "amount_cop" in disp.columns: disp["amount_cop"] = disp["amount_cop"].apply(lambda x: f"${x:,.0f}")
            st.markdown(f"**📋 Transacciones financieras — {len(fin)} eventos**")
            st.dataframe(disp.head(12), use_container_width=True, hide_index=True)
        else:
            st.info("Sin transacciones financieras para este usuario.")

    st.divider()
    st.subheader("🚦 Señales de Riesgo")
    flags_def = [
        ("👑 Alto Valor",   "is_high_value",    True),
        ("⚠️ Balance Bajo", "is_low_balance",   False),
        ("❌ Alto Riesgo",  "is_high_risk",     False),
        ("😴 Dormido",      "is_dormant",        False),
        ("💸 Estrés Fin.",  "financial_stress", False),
    ]
    fc = st.columns(5)
    for i, (label, col, pos_good) in enumerate(flags_def):
        active = u.get(col, 0) == 1
        color = "#00ffb2" if (active and pos_good) else ("#ff4d6d" if active else "#64748b")
        bg    = f"rgba({('0,255,178' if (active and pos_good) else ('255,77,109' if active else '100,116,139'))},0.08)"
        icon  = "✅" if (active and pos_good) else ("🔴" if active else "⚪")
        fc[i].markdown(f"""
        <div class="flag" style="background:{bg};border-color:{color}44">
            <div style="font-size:1.6em">{icon}</div>
            <div style="font-family:'DM Mono',monospace;font-size:10px;
                 color:{color};font-weight:700;margin-top:5px">{label}</div>
            <div style="font-size:10px;color:#64748b">{'ACTIVO' if active else 'No aplica'}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    ac = st.columns(3)
    ac[0].info(f"⏰ **Hora pico:** {u.get('peak_hour','N/A')}:00")
    ac[1].info(f"📱 **Canal:** {u.get('preferred_channel','N/A')}")
    ac[2].info(f"💻 **Dispositivo:** {u.get('preferred_device','N/A')}")

    from insights.engine import generate_user_insights
    u_ins = generate_user_insights(u)
    if u_ins:
        st.subheader("💡 Insights Personalizados")
        for ins in u_ins:
            st.markdown(f"""
            <div class="ins-card ins-{ins['nivel']}">
                <b style="font-family:'Syne',sans-serif">{ins['titulo']}</b><br>
                <span style="color:#cbd5e1">{ins['descripcion']}</span><br>
                <em style="color:#64748b;font-size:12px">→ {ins['accion']}</em>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — SEGMENTACIÓN ML
# ═══════════════════════════════════════════════════════════════════════════
elif section == "🎯  Segmentación ML":
    st.title("Segmentación — KMeans k=4")
    st.markdown(
        f"<div style='font-family:DM Mono,monospace;font-size:12px;color:#64748b'>"
        f"Silhouette: <b style='color:#00ffb2'>{D['silhouette']:.3f}</b> &nbsp;·&nbsp; "
        f"Etiquetado dinámico por centroide &nbsp;·&nbsp; Sin labels supervisadas</div>",
        unsafe_allow_html=True,
    )

    seg_stats = (
        gf.groupby(["segment_name","segment_color","segment_icon"])
        .agg(n=("userId","count"), gasto=("total_spent","mean"),
             balance=("current_balance","mean"), fallos=("fail_ratio","mean"),
             pct_riesgo=("is_high_risk","mean"))
        .reset_index().sort_values("gasto", ascending=False)
    )
    sc_cols = st.columns(len(seg_stats))
    for i, (_, row) in enumerate(seg_stats.iterrows()):
        c = row["segment_color"]
        sc_cols[i].markdown(f"""
        <div style="border:1px solid {c}40;border-top:3px solid {c};
             border-radius:10px;padding:16px;text-align:center;
             background:rgba(16,20,31,0.7);transition:transform 0.15s">
            <div style="font-size:2.2em">{row['segment_icon']}</div>
            <div style="font-family:'Syne',sans-serif;font-weight:700;
                 color:{c};font-size:14px;margin:6px 0">{row['segment_name']}</div>
            <div style="font-family:'Syne',sans-serif;font-size:30px;
                 font-weight:800;color:#fff">{row['n']}</div>
            <div style="font-family:'DM Mono',monospace;font-size:10px;
                 color:#64748b;margin-bottom:10px">usuarios</div>
            <hr style="border-color:{c}25;margin:8px 0">
            <div style="font-family:'DM Mono',monospace;font-size:11px;
                 color:#94a3b8;text-align:left;line-height:1.8">
            Gasto:&nbsp;<b style='color:#e2e8f0'>${row['gasto']:,.0f}</b><br>
            Balance:&nbsp;<b style='color:#e2e8f0'>${row['balance']:,.0f}</b><br>
            Fallos:&nbsp;<b style='color:#e2e8f0'>{row['fallos']*100:.1f}%</b><br>
            Riesgo:&nbsp;<b style='color:#e2e8f0'>{row['pct_riesgo']*100:.0f}%</b>
            </div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    sc1, sc2 = st.columns(2)
    with sc1:
        hover = [c for c in ["userId","name","fail_ratio",CITY_COL] if c in gf.columns]
        fig_sc = px.scatter(
            gf, x="total_spent", y="current_balance",
            color="segment_name", color_discrete_map=SEG_COLOR,
            size="n_transactions", size_max=22, opacity=0.72,
            title="Gasto vs Balance (tamaño = N° transacciones)",
            hover_data=hover,
            labels={"total_spent":"Gasto (COP)","current_balance":"Balance (COP)"},
        )
        fig_sc.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.25, font=dict(family="DM Mono")),
            margin=dict(t=50), font=dict(family="DM Sans"),
            xaxis=dict(gridcolor="#1e2740"), yaxis=dict(gridcolor="#1e2740"),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    with sc2:
        fig_vi = px.violin(
            gf, x="segment_name", y="fail_ratio",
            color="segment_name", color_discrete_map=SEG_COLOR,
            box=True, points="outliers",
            title="Distribución de Tasa de Fallos por Segmento",
            labels={"fail_ratio":"Tasa Fallos","segment_name":"Segmento"},
        )
        fig_vi.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, margin=dict(t=50), font=dict(family="DM Sans"),
            yaxis=dict(gridcolor="#1e2740"),
        )
        st.plotly_chart(fig_vi, use_container_width=True)

    st.subheader("📊 Perfil Comparativo de Segmentos (normalizado)")
    radar_cols = {
        "Gasto prom":   "total_spent",
        "Balance prom": "current_balance",
        "N° Tx":        "n_transactions",
        "Tasa fallos":  "fail_ratio",
        "Días activos": "unique_days_active",
    }
    seg_r = gf.groupby("segment_name")[list(radar_cols.values())].mean()
    seg_n = (seg_r - seg_r.min()) / (seg_r.max() - seg_r.min() + 1e-9)
    fig_mr = go.Figure()
    for seg in seg_n.index:
        c    = SEG_COLOR.get(seg, "#64748b")
        vals = seg_n.loc[seg].tolist()
        keys = list(radar_cols)
        fig_mr.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=keys + [keys[0]],
        fill="toself",
        name=seg,
        line=dict(color=c, width=2),
        fillcolor=f"rgba({int(c[1:3],16)}, {int(c[3:5],16)}, {int(c[5:7],16)}, 0.13)",
    ))
    fig_mr.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,1], gridcolor="#1e2740")),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.18, font=dict(family="DM Mono")),
        margin=dict(t=40), font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_mr, use_container_width=True)

    st.subheader("👥 Tabla de Usuarios")
    t1, t2, t3 = st.columns(3)
    with t1: seg_tbl = st.selectbox("Segmento", ["Todos"] + ALL_SEGS, key="tbl_seg")
    with t2: sort_by = st.selectbox("Ordenar por", ["total_spent","current_balance","fail_ratio","n_transactions"])
    with t3: asc_    = st.toggle("Ascendente", value=False)

    df_t  = gf if seg_tbl == "Todos" else gf[gf["segment_name"] == seg_tbl]
    t_col = [c for c in ["userId","name",CITY_COL,"segment_name","total_spent",
                          "current_balance","fail_ratio","n_transactions","is_high_risk"]
             if c in df_t.columns]
    st.dataframe(
        df_t[t_col].sort_values(sort_by, ascending=asc_).head(100)
        .rename(columns={"userId":"ID","name":"Nombre",CITY_COL:"Ciudad",
                         "segment_name":"Segmento","total_spent":"Gasto",
                         "current_balance":"Balance","fail_ratio":"Fallos",
                         "n_transactions":"N° Tx","is_high_risk":"En Riesgo"})
        .style.format({"Gasto":"${:,.0f}","Balance":"${:,.0f}","Fallos":"{:.1%}"})
        .background_gradient(subset=["Fallos"], cmap="Reds"),
        use_container_width=True, height=400,
    )
    st.caption(f"Mostrando {min(100,len(df_t))} de {len(df_t)} usuarios")


# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — ANOMALÍAS
# ═══════════════════════════════════════════════════════════════════════════
elif section == "🚨  Anomalías":
    fin_total = len(silver[silver["is_financial"] == 1])
    st.title("Detección de Anomalías — Isolation Forest")
    st.markdown(
        f"<div style='font-family:DM Mono,monospace;font-size:12px;color:#64748b'>"
        f"Contaminación 7% &nbsp;·&nbsp; "
        f"<b style='color:#ff4d6d'>{D['n_anomalies']}</b> anomalías detectadas "
        f"en <b>{fin_total:,}</b> eventos financieros</div>",
        unsafe_allow_html=True,
    )

    ac = st.columns(4)
    ac[0].metric("🔍 Anomalías",     f"{D['n_anomalies']:,}")
    if len(top_a) > 0:
        ac[1].metric("💰 Monto prom.", f"${top_a['amount'].mean():,.0f} COP")
        ac[2].metric("❌ % Fallidas",  f"{top_a['is_failed'].mean()*100:.1f}%")
        ac[3].metric("📊 Score mín.",  f"{top_a['anomaly_score'].min():.3f}")

    if len(top_a) > 0:
        st.divider()
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            fig_h = px.histogram(
                top_a, x="amount", nbins=22, title="Distribución de Montos Anómalos",
                color_discrete_sequence=["#ffb830"], labels={"amount":"Monto (COP)"},
            )
            fig_h.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50), font=dict(family="DM Sans"),
                xaxis=dict(gridcolor="#1e2740"), yaxis=dict(gridcolor="#1e2740"),
            )
            st.plotly_chart(fig_h, use_container_width=True)

        with cc2:
            if "event_type" in top_a.columns:
                et = top_a["event_type"].value_counts().reset_index()
                et.columns = ["Tipo","N"]
                fig_et = px.pie(et, values="N", names="Tipo", hole=0.42, title="Por Tipo de Evento",
                                color_discrete_sequence=["#ff4d6d","#ffb830","#00d4ff","#00ffb2"])
                fig_et.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=50), font=dict(family="DM Sans"))
                st.plotly_chart(fig_et, use_container_width=True)

        with cc3:
            if "category" in top_a.columns:
                ca = top_a["category"].value_counts().head(6).reset_index()
                ca.columns = ["Categoría","N"]
                fig_ca = px.bar(ca, x="N", y="Categoría", orientation="h", title="Por Categoría",
                                color="N", color_continuous_scale=[[0,"#1e3a8a"],[1,"#ff4d6d"]], text="N")
                fig_ca.update_traces(textposition="outside")
                fig_ca.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False, margin=dict(t=50), font=dict(family="DM Sans"),
                    xaxis=dict(gridcolor="#1e2740"),
                )
                st.plotly_chart(fig_ca, use_container_width=True)

        hover_a = [c for c in ["userId","event_type","merchant","category"] if c in top_a.columns]
        fig_as = px.scatter(
            top_a, x="amount", y="anomaly_score", color="is_failed",
            color_discrete_map={0:"#00d4ff", 1:"#ff4d6d"},
            size="amount", size_max=18,
            title="Anomaly Score vs Monto  (rojo = transacción fallida)",
            hover_data=hover_a,
            labels={"amount":"Monto (COP)","anomaly_score":"Score","is_failed":"Fallida"},
        )
        fig_as.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=50), font=dict(family="DM Sans"),
            xaxis=dict(gridcolor="#1e2740"), yaxis=dict(gridcolor="#1e2740"),
        )
        st.plotly_chart(fig_as, use_container_width=True)

        st.subheader("🔎 Detalle de Transacciones Anómalas")
        fl1, fl2 = st.columns(2)
        with fl1:
            score_th = st.slider(
                "Filtrar por score mínimo",
                float(top_a["anomaly_score"].min()), 0.0,
                float(top_a["anomaly_score"].min()), step=0.01,
            )
        with fl2:
            only_fail = st.toggle("Solo transacciones fallidas", value=False)

        df_a = top_a[top_a["anomaly_score"] >= score_th]
        if only_fail and "is_failed" in df_a.columns:
            df_a = df_a[df_a["is_failed"] == 1]

        disp_a = [c for c in ["userId","event_type","amount","merchant","category",
                               "hour","is_failed","anomaly_score"] if c in df_a.columns]
        st.dataframe(
            df_a[disp_a].sort_values("anomaly_score").head(50)
            .style.format({"amount":"${:,.0f}","anomaly_score":"{:.3f}"})
            .background_gradient(subset=["anomaly_score"], cmap="Reds_r"),
            use_container_width=True, height=380,
        )
        st.caption(f"Mostrando {min(50,len(df_a))} de {len(df_a)} anomalías")


# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — AGENTE IA
# ═══════════════════════════════════════════════════════════════════════════
elif section == "🤖  Agente IA":
    st.title("Agente IA — Consultas en Lenguaje Natural")

    # Detectar estado actual del agente
    ai = detect_agent_mode()

    # ── Panel de estado del backend ───────────────────────────────────────
    status_col1, status_col2, status_col3 = st.columns([2, 2, 1])

    with status_col1:
        if ai["mode"] == "mistral":
            st.success(f"🔥 **Mistral-7B activo** — {ai['url']} · `{ai['latency_ms']:.0f}ms`")
        elif ai["mode"] == "llama":
            st.warning(f"🦙 **LLaMA activo** — {ai['url']} · `{ai['latency_ms']:.0f}ms`")
        else:
            st.info("📋 **Modo Offline** — configura `MISTRAL_BASE_URL` en el sidebar para activar el LLM")

    with status_col2:
        if ai["ok"] and ai.get("models"):
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:11px;"
                f"color:#64748b;padding:10px 0'>Modelo activo: "
                f"<code style='color:#00d4ff'>{ai['models'][0]}</code></div>",
                unsafe_allow_html=True,
            )

    with status_col3:
        if st.button("🔄 Re-detectar"):
            st.session_state.agent_info_cache = detect_agent_mode()
            st.session_state.agent_last_check = time.time()
            st.rerun()

    # ── Selector de usuario ───────────────────────────────────────────────
    st.divider()
    au1, au2 = st.columns([4, 1])
    with au1:
        au_map = {
            r["userId"]: (
                f"{r['name']} ({r['userId']}) · "
                f"{r.get('segment_name','?')} · "
                f"${r.get('total_spent',0):,.0f} COP"
            )
            for _, r in gold.iterrows()
        }
        au_uid = st.selectbox("Usuario de contexto", list(au_map), format_func=lambda x: au_map[x])
    with au2:
        st.write("")
        if st.button("🗑️ Limpiar chat"):
            st.session_state.chat_history  = []
            st.session_state.agent_history = []
            st.rerun()

    u_row = gold[gold["userId"] == au_uid].iloc[0]
    sc    = u_row.get("segment_color", "#7c6cff")

    # Header del usuario seleccionado
    st.markdown(f"""
    <div style="background:rgba(16,20,31,0.7);border:1px solid {sc}35;
         border-left:4px solid {sc};border-radius:8px;
         padding:12px 18px;margin:8px 0 16px;font-family:'DM Mono',monospace">
        <span style="color:#fff;font-size:13px;font-weight:500">{u_row.get('name','N/A')}</span>
        &nbsp;
        <span style="color:{sc}">{u_row.get('segment_icon','')} {u_row.get('segment_name','')}</span>
        &nbsp;·&nbsp;
        <span style="color:#64748b">Gasto: <b style='color:#e2e8f0'>${u_row.get('total_spent',0):,.0f} COP</b></span>
        &nbsp;·&nbsp;
        <span style="color:#64748b">Balance: <b style='color:#e2e8f0'>${u_row.get('current_balance',0):,.0f} COP</b></span>
        &nbsp;·&nbsp;
        <span style="color:#64748b">Fallos: <b style='color:{"#ff4d6d" if u_row.get("fail_ratio",0)>0.3 else "#00ffb2"}'>{u_row.get('fail_ratio',0)*100:.1f}%</b></span>
    </div>""", unsafe_allow_html=True)

    # ── Preguntas rápidas ─────────────────────────────────────────────────
    quick_qs = [
        "¿En qué gasto más?",
        "¿Tengo riesgo financiero?",
        "¿Cómo está mi balance?",
        "Dame un resumen completo",
        "¿Qué patrón raro tengo?",
    ]
    qcols = st.columns(len(quick_qs))
    for i, q in enumerate(quick_qs):
        if qcols[i].button(q, key=f"q{i}", use_container_width=True):
            st.session_state.pending_question = q

    # ── Chat ──────────────────────────────────────────────────────────────
    if "chat_history"  not in st.session_state: st.session_state.chat_history  = []
    if "agent_history" not in st.session_state: st.session_state.agent_history = []

    question = st.chat_input("Escribe tu pregunta sobre el usuario…")
    if not question and "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "meta" in msg:
                meta = msg["meta"]
                lat_html = ""
                if meta.get("latency_ms", 0) > 0:
                    ms = meta["latency_ms"]
                    lat_cls = "latency-fast" if ms < 500 else ("latency-medium" if ms < 2000 else "latency-slow")
                    lat_html = f'<span class="latency-badge {lat_cls}">{ms:.0f}ms</span>'
                mode_color = {"mistral": "#00ffb2", "llama": "#ffb830", "offline": "#64748b"}.get(meta.get("mode","offline"), "#64748b")
                mode_label = {"mistral": "🔥 Mistral-7B", "llama": "🦙 LLaMA", "offline": "📋 Offline"}.get(meta.get("mode","offline"), "📋 Offline")
                st.markdown(
                    f"<div style='font-family:DM Mono,monospace;font-size:10px;"
                    f"color:{mode_color};margin-top:4px'>"
                    f"Modelo: {mode_label} {lat_html}</div>",
                    unsafe_allow_html=True,
                )

    if question:
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_history.append({"role": "user", "content": question})

        with st.chat_message("assistant"):
            answer_placeholder = st.empty()
            mode_placeholder   = st.empty()

            with st.spinner("Analizando con el agente IA…"):
                # Construir contexto del usuario
                user_ctx = build_user_context(u_row)

                # Intentar usar el LLM real
                final_mode = "offline"
                final_latency = 0.0
                answer = ""

                if ai["mode"] in ("mistral", "llama"):
                    try:
                        prompt = f"""Contexto financiero del usuario:\n{user_ctx}\n\nPregunta: {question}"""
                        answer, final_latency = query_llm(
                            prompt=prompt,
                            system=FINTECH_SYSTEM,
                            base_url=ai["url"],
                            model=ai["models"][0] if ai.get("models") else "mistral-fintech",
                        )
                        final_mode = ai["mode"]
                    except Exception as e:
                        answer = answer_offline(question, u_row)
                        answer += f"\n\n> ⚠️ *LLM no disponible ({str(e)[:80]}). Respuesta por reglas.*"
                        final_mode = "offline"
                else:
                    # También intentar importar el agente original si existe
                    try:
                        from agent.agent import ask_agent
                        answer, new_hist, final_mode = ask_agent(
                            question=question,
                            user_row=u_row,
                            history=st.session_state.agent_history,
                        )
                        st.session_state.agent_history = new_hist
                    except Exception:
                        answer = answer_offline(question, u_row)
                        final_mode = "offline"

            answer_placeholder.markdown(answer)

            # Badge de modo
            mode_color = {"mistral": "#00ffb2", "llama": "#ffb830", "offline": "#64748b"}.get(final_mode, "#64748b")
            mode_label = {"mistral": "🔥 Mistral-7B", "llama": "🦙 LLaMA", "offline": "📋 Offline"}.get(final_mode, "📋 Offline")
            lat_html = ""
            if final_latency > 0:
                ms = final_latency
                lat_cls = "latency-fast" if ms < 500 else ("latency-medium" if ms < 2000 else "latency-slow")
                lat_html = f'<span class="latency-badge {lat_cls}">{ms:.0f}ms</span>'
            mode_placeholder.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:10px;"
                f"color:{mode_color};margin-top:4px'>"
                f"Modelo: {mode_label} {lat_html}</div>",
                unsafe_allow_html=True,
            )

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": answer,
            "meta": {"mode": final_mode, "latency_ms": final_latency},
        })

    # ── Panel de debug / estado del sistema (colapsable) ─────────────────
    with st.expander("🔧 Debug — Estado del sistema de IA"):
        d1, d2, d3 = st.columns(3)
        d1.metric("Modo activo",   ai["label"].replace("🔥","").replace("🦙","").replace("📋","").strip())
        d2.metric("Latencia LLM",  f"{ai['latency_ms']:.0f}ms" if ai["ok"] else "—")
        d3.metric("Mensajes chat", str(len(st.session_state.chat_history)))

        if ai["ok"]:
            st.markdown(f"""
            ```
            Endpoint: {ai['url']}/v1/chat/completions
            Modelo:   {ai['models'][0] if ai.get('models') else 'N/A'}
            Modo:     {ai['mode']}
            ```
            """)

            if st.button("🧪 Test rápido al LLM"):
                with st.spinner("Enviando ping…"):
                    try:
                        resp, ms = query_llm(
                            "Responde solo: OK",
                            "Eres un asistente.", ai["url"],
                            model=ai["models"][0] if ai.get("models") else "mistral-fintech",
                            max_tokens=10,
                        )
                        st.success(f"✅ Respuesta: `{resp}` — `{ms:.0f}ms`")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
        else:
            st.info(
                "Para conectar Mistral:\n"
                "1. Configura `MISTRAL_BASE_URL=http://IP:PUERTO` en el sidebar\n"
                "2. Haz clic en **🔄 Test conexión**\n"
                "3. El endpoint debe ser compatible con OpenAI API (`/v1/chat/completions`)"
            )
