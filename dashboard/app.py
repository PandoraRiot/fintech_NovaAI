"""
dashboard/app.py — Dashboard Principal FinTech Intelligence
Ejecutar: streamlit run dashboard/app.py
5 secciones: KPIs Globales | Perfil 360° | Segmentación | Anomalías | Agente IA
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinTech Intelligence",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
    border: 1px solid #3d3d5c;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.insight-critical { border-left: 4px solid #DC2626; background: #1a0a0a; padding: 12px; border-radius: 6px; margin: 6px 0; }
.insight-alto     { border-left: 4px solid #F59E0B; background: #1a1200; padding: 12px; border-radius: 6px; margin: 6px 0; }
.insight-medio    { border-left: 4px solid #2563EB; background: #0a0f1a; padding: 12px; border-radius: 6px; margin: 6px 0; }
.insight-oportunidad { border-left: 4px solid #10B981; background: #0a1a12; padding: 12px; border-radius: 6px; margin: 6px 0; }
.insight-info     { border-left: 4px solid #6B7280; background: #111118; padding: 12px; border-radius: 6px; margin: 6px 0; }
</style>
""", unsafe_allow_html=True)


# ── Pipeline + ML (cached) ─────────────────────────────────────────────────
@st.cache_data(show_spinner="🔄 Ejecutando pipeline Medallion...")
def load_all_data():
    from pipeline.bronze    import run_bronze
    from pipeline.silver    import run_silver
    from pipeline.gold      import run_gold
    from models.clustering  import run_clustering
    from models.anomaly     import run_anomaly_detection
    from insights.engine    import generate_portfolio_insights

    bronze = run_bronze()
    silver = run_silver(bronze)
    gold   = run_gold(silver)
    gold, kmeans, scaler, sil, cluster_labels = run_clustering(gold)
    silver_with_anom, n_anom, top_anomalies   = run_anomaly_detection(silver)
    portfolio_insights = generate_portfolio_insights(gold, top_anomalies)

    return {
        "gold": gold,
        "silver": silver_with_anom,
        "top_anomalies": top_anomalies,
        "n_anomalies": n_anom,
        "silhouette": sil,
        "cluster_labels": cluster_labels,
        "portfolio_insights": portfolio_insights,
    }


data = load_all_data()
gold  = data["gold"]
silver = data["silver"]
top_anomalies = data["top_anomalies"]
portfolio_insights = data["portfolio_insights"]

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bank-card-back-side.png", width=60)
    st.title("FinTech Intelligence")
    st.caption("MVP · Hackathon 2026")
    st.divider()

    section = st.radio(
        "Sección",
        ["🏠 KPIs Globales", "👤 Perfil 360°", "🎯 Segmentación", "🚨 Anomalías", "🤖 Agente IA"],
        label_visibility="collapsed",
    )
    st.divider()

    # API Key (para el agente)
    api_key = st.text_input("🔑 Anthropic API Key", type="password", placeholder="sk-ant-...")
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        st.success("✅ API conectada")

    st.caption(f"**{len(gold):,}** usuarios | **{len(silver):,}** eventos")
    st.caption(f"Silhouette: {data['silhouette']:.3f} | Anomalías: {data['n_anomalies']}")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1: KPIs GLOBALES
# ══════════════════════════════════════════════════════════════════════════════
if section == "🏠 KPIs Globales":
    st.title("🏠 KPIs Globales del Portafolio")
    st.caption("Vista ejecutiva — estado del negocio en tiempo real")

    # KPI row 1
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Usuarios",         f"{len(gold):,}")
    c2.metric("💳 Transacciones",    f"{silver['is_financial'].sum():,}")
    c3.metric("💰 Gasto Total",      f"${gold['total_spent'].sum()/1e6:.1f}M COP")
    c4.metric("⚠️ Tasa de Fallos",   f"{(gold['n_failed'].sum()/gold['n_transactions'].sum()*100):.1f}%")
    c5.metric("🔍 Anomalías",        f"{data['n_anomalies']:,} tx")

    st.divider()

    col1, col2 = st.columns([3, 2])

    with col1:
        # Distribución de segmentos
        seg_counts = gold["segment_name"].value_counts().reset_index()
        seg_counts.columns = ["Segmento", "Usuarios"]
        seg_colors = gold.drop_duplicates("segment_name").set_index("segment_name")["segment_color"].to_dict()
        fig_seg = px.pie(
            seg_counts, values="Usuarios", names="Segmento",
            title="Distribución de Segmentos de Usuarios",
            color="Segmento", color_discrete_map=seg_colors,
            hole=0.4,
        )
        fig_seg.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_seg, use_container_width=True)

    with col2:
        # Gasto por categoría
        cat_cols = [c for c in gold.columns if c.startswith("cat_")]
        cat_totals = gold[cat_cols].sum().reset_index()
        cat_totals.columns = ["Categoría", "Total"]
        cat_totals["Categoría"] = cat_totals["Categoría"].str.replace("cat_", "")
        cat_totals = cat_totals.sort_values("Total", ascending=True)
        fig_cat = px.bar(
            cat_totals, y="Categoría", x="Total", orientation="h",
            title="Gasto Total por Categoría (COP)",
            color="Total", color_continuous_scale="Purples",
        )
        fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_cat, use_container_width=True)

    # Insights de portafolio
    st.subheader("💡 Insights Automáticos")
    for ins in portfolio_insights:
        nivel_class = f"insight-{ins['nivel']}"
        st.markdown(f"""
        <div class="{nivel_class}">
            <strong>{ins['titulo']}</strong><br>
            {ins['descripcion']}<br>
            <em>→ {ins['accion']}</em>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2: PERFIL 360°
# ══════════════════════════════════════════════════════════════════════════════
elif section == "👤 Perfil 360°":
    st.title("👤 Vista 360° del Usuario")

    user_list = sorted(gold["userId"].tolist())
    selected_user = st.selectbox("Selecciona un usuario", user_list)
    user = gold[gold["userId"] == selected_user].iloc[0]

    # Header del usuario
    col_icon, col_info = st.columns([1, 5])
    with col_icon:
        st.markdown(f"<h1 style='text-align:center;font-size:3em'>{user.get('segment_icon','👤')}</h1>", unsafe_allow_html=True)
    with col_info:
        st.subheader(f"{user.get('name', 'N/A')} — {selected_user}")
        st.caption(f"{user.get('segment', 'N/A')} | {user.get('city', 'N/A')}, {user.get('country', 'N/A')} | {user.get('age', 'N/A')} años")
        st.markdown(f"**Segmento ML:** {user.get('segment_icon','')} {user.get('segment_name','')}")

    st.divider()

    # KPIs del usuario
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Gasto Total",       f"${user.get('total_spent', 0):,.0f} COP")
    c2.metric("💳 Transacciones",     f"{user.get('n_transactions', 0):.0f}")
    c3.metric("🏦 Balance Actual",    f"${user.get('current_balance', 0):,.0f} COP")
    c4.metric("❌ Tasa de Fallos",    f"{user.get('fail_ratio', 0)*100:.1f}%")

    col1, col2 = st.columns(2)

    with col1:
        # Radar de categorías
        cat_cols = [c for c in user.index if c.startswith("cat_")]
        cats = [c.replace("cat_", "") for c in cat_cols]
        vals = [user.get(c, 0) for c in cat_cols]
        if sum(vals) > 0:
            fig_radar = go.Figure(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=cats + [cats[0]],
                fill="toself",
                fillcolor="rgba(124,58,237,0.3)",
                line=dict(color="#7C3AED"),
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                title="Radar de Gasto por Categoría",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    with col2:
        # Flags de riesgo
        st.subheader("🚦 Señales de Riesgo")
        flags = {
            "👑 Usuario Premium": user.get("is_high_value", 0) == 1,
            "⚠️ Balance Bajo":    user.get("is_low_balance", 0) == 1,
            "❌ Alto Riesgo Fallos": user.get("is_high_risk", 0) == 1,
            "😴 Usuario Dormido": user.get("is_dormant", 0) == 1,
            "💸 Estrés Financiero": user.get("financial_stress", 0) == 1,
        }
        for label, active in flags.items():
            color = "#10B981" if (active and "Premium" in label) else ("#DC2626" if active else "#374151")
            status = "🟢 ACTIVO" if active else "⚪ No aplica"
            st.markdown(f"<span style='color:{color}'>{label}: **{status}**</span>", unsafe_allow_html=True)

        st.divider()
        st.subheader("📊 Datos de Actividad")
        st.write(f"📅 Días activos: {user.get('unique_days_active', 0):.0f}")
        st.write(f"⏰ Hora pico: {user.get('peak_hour', 'N/A')}:00")
        st.write(f"📱 Canal preferido: {user.get('preferred_channel', 'N/A')}")
        st.write(f"💻 Dispositivo: {user.get('preferred_device', 'N/A')}")

    # Insights personalizados
    from insights.engine import generate_user_insights
    user_insights = generate_user_insights(user)
    if user_insights:
        st.subheader("💡 Insights Personalizados")
        for ins in user_insights:
            nivel_class = f"insight-{ins['nivel']}"
            st.markdown(f"""
            <div class="{nivel_class}">
                <strong>{ins['titulo']}</strong><br>
                {ins['descripcion']}<br>
                <em>→ {ins['accion']}</em>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3: SEGMENTACIÓN
# ══════════════════════════════════════════════════════════════════════════════
elif section == "🎯 Segmentación":
    st.title("🎯 Segmentación de Usuarios — KMeans k=4")
    st.caption(f"Silhouette Score: **{data['silhouette']:.3f}** (separación real entre clusters)")

    # Resumen de clusters
    cluster_summary = (
        gold.groupby(["cluster", "segment_icon", "segment_name"])
        .agg(
            usuarios        = ("userId",       "count"),
            gasto_promedio  = ("total_spent",  "mean"),
            balance_promedio= ("current_balance","mean"),
            tasa_fallos     = ("fail_ratio",   "mean"),
            pct_premium     = ("is_high_value","mean"),
        )
        .reset_index()
    )

    for _, row in cluster_summary.iterrows():
        with st.expander(f"{row['segment_icon']} {row['segment_name']} — {row['usuarios']} usuarios ({row['usuarios']/len(gold)*100:.1f}%)"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Usuarios",           f"{row['usuarios']:.0f}")
            c2.metric("Gasto Promedio",     f"${row['gasto_promedio']:,.0f} COP")
            c3.metric("Balance Promedio",   f"${row['balance_promedio']:,.0f} COP")
            c4.metric("Tasa de Fallos",     f"{row['tasa_fallos']*100:.1f}%")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        # Scatter: gasto vs balance por segmento
        fig_scatter = px.scatter(
            gold, x="total_spent", y="current_balance",
            color="segment_name",
            color_discrete_map=gold.drop_duplicates("segment_name").set_index("segment_name")["segment_color"].to_dict(),
            title="Gasto Total vs Balance Actual por Segmento",
            labels={"total_spent": "Gasto Total (COP)", "current_balance": "Balance Actual (COP)"},
            hover_data=["userId", "name", "fail_ratio"],
            opacity=0.7,
        )
        fig_scatter.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col2:
        # Box: distribución de transacciones por segmento
        fig_box = px.box(
            gold, x="segment_name", y="n_transactions",
            color="segment_name",
            color_discrete_map=gold.drop_duplicates("segment_name").set_index("segment_name")["segment_color"].to_dict(),
            title="Distribución de Transacciones por Segmento",
            labels={"n_transactions": "N° Transacciones", "segment_name": "Segmento"},
        )
        fig_box.update_layout(paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    # Tabla de usuarios por segmento
    st.subheader("👥 Usuarios por Segmento")
    seg_filter = st.selectbox("Filtrar por segmento", ["Todos"] + gold["segment_name"].unique().tolist())
    df_show = gold if seg_filter == "Todos" else gold[gold["segment_name"] == seg_filter]
    st.dataframe(
        df_show[["userId", "name", "segment_name", "total_spent", "current_balance", "fail_ratio", "n_transactions"]]
        .sort_values("total_spent", ascending=False)
        .head(50)
        .rename(columns={
            "userId": "ID", "name": "Nombre", "segment_name": "Segmento",
            "total_spent": "Gasto Total", "current_balance": "Balance",
            "fail_ratio": "Tasa Fallos", "n_transactions": "N° Tx",
        })
        .style.format({
            "Gasto Total": "${:,.0f}",
            "Balance": "${:,.0f}",
            "Tasa Fallos": "{:.1%}",
        }),
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4: ANOMALÍAS
# ══════════════════════════════════════════════════════════════════════════════
elif section == "🚨 Anomalías":
    st.title("🚨 Detección de Anomalías — Isolation Forest")
    st.caption(f"Contaminación: 7% | {data['n_anomalies']} transacciones anómalas detectadas")

    c1, c2, c3 = st.columns(3)
    c1.metric("🔍 Anomalías",     f"{data['n_anomalies']:,}")
    c2.metric("💰 Monto Promedio", f"${top_anomalies['amount'].mean():,.0f} COP" if len(top_anomalies) > 0 else "N/A")
    c3.metric("❌ % Fallidas",    f"{top_anomalies['is_failed'].mean()*100:.1f}%" if len(top_anomalies) > 0 else "N/A")

    if len(top_anomalies) > 0:
        col1, col2 = st.columns(2)

        with col1:
            # Distribución de montos anómalos
            fig_hist = px.histogram(
                top_anomalies, x="amount",
                title="Distribución de Montos Anómalos",
                nbins=20, color_discrete_sequence=["#F59E0B"],
            )
            fig_hist.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_hist, use_container_width=True)

        with col2:
            # Anomalías por hora
            fig_hour = px.histogram(
                top_anomalies, x="hour", nbins=24,
                title="Distribución por Hora (transacciones anómalas)",
                color_discrete_sequence=["#DC2626"],
            )
            fig_hour.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_hour, use_container_width=True)

        st.subheader("🔎 Top Transacciones Anómalas")
        display_cols = ["userId", "event_type", "amount", "merchant", "category", "hour", "is_failed", "anomaly_score"]
        available_cols = [c for c in display_cols if c in top_anomalies.columns]
        st.dataframe(
            top_anomalies[available_cols]
            .sort_values("anomaly_score")
            .head(20)
            .style.format({
                "amount": "${:,.0f}",
                "anomaly_score": "{:.3f}",
            }),
            use_container_width=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5: AGENTE IA
# ══════════════════════════════════════════════════════════════════════════════
elif section == "🤖 Agente IA":
    st.title("🤖 Agente IA — Consultas en Lenguaje Natural")
    st.caption("Pregunta sobre cualquier usuario en español. Con API key activa, usa Claude Sonnet.")

    # Selección de usuario
    selected_user = st.selectbox("Usuario de contexto", sorted(gold["userId"].tolist()))
    user_row = gold[gold["userId"] == selected_user].iloc[0]

    # Info rápida del usuario seleccionado
    st.info(
        f"**{user_row.get('name', 'N/A')}** | {user_row.get('segment_icon','')} {user_row.get('segment_name','')} | "
        f"Gasto: ${user_row.get('total_spent',0):,.0f} COP | Balance: ${user_row.get('current_balance',0):,.0f} COP"
    )

    # Inicializar historial
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []

    # Preguntas rápidas
    st.subheader("💬 Preguntas rápidas")
    quick_qs = [
        "¿En qué gasto más?",
        "¿Tengo riesgo financiero?",
        "¿Qué patrón raro tengo?",
        "¿Cómo está mi balance?",
        "Dame un resumen completo de mi situación",
    ]
    cols = st.columns(len(quick_qs))
    for i, q in enumerate(quick_qs):
        if cols[i].button(q, key=f"quick_{i}"):
            st.session_state.pending_question = q

    # Input de pregunta
    question = st.chat_input("Escribe tu pregunta aquí...")
    if not question and "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")

    # Mostrar historial
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Procesar nueva pregunta
    if question:
        from agent.agent import ask_agent

        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_history.append({"role": "user", "content": question})

        with st.chat_message("assistant"):
            with st.spinner("Analizando..."):
                answer, new_agent_history, agent_mode = ask_agent(
                    question=question,
                    user_row=user_row,
                    history=st.session_state.agent_history,
                )
            st.markdown(answer)
            st.caption(f"🤖 Agente: `{agent_mode}` — {'🦙 LLaMA 3.2' if agent_mode=='llama' else '🔵 Claude' if agent_mode=='claude' else '📋 Offline'}")
            st.session_state.agent_history = new_agent_history

        st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # Botón limpiar chat
    if st.session_state.chat_history:
        if st.button("🗑️ Limpiar conversación"):
            st.session_state.chat_history = []
            st.session_state.agent_history = []
            st.rerun()
