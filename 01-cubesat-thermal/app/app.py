"""
app.py — Dashboard Streamlit interactif pour la simulation thermique CubeSat

Lancement :
  streamlit run app/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import yaml

from src.thermal_model import ThermalModel, NODE_NAMES
from src.solver import run_simulation
from src.orbital import OrbitalParameters, in_eclipse

# ─── Configuration de la page ────────────────────────────────────────────────
st.set_page_config(
    page_title="CubeSat Thermal Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Thème couleur pour les nœuds ────────────────────────────────────────────
NODE_COLORS = {
    "+X":        "#E74C3C",
    "-X":        "#C0392B",
    "+Y":        "#F39C12",
    "-Y":        "#D35400",
    "+Z":        "#3498DB",
    "-Z":        "#1A5276",
    "Structure": "#27AE60",
    "OBC/EPS":   "#8E44AD",
    "Payload":   "#16A085",
}


# ─── Chargement de la config de base ─────────────────────────────────────────
@st.cache_data
def load_default_config():
    config_path = Path(__file__).parent.parent / "config" / "cubesat_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


# ─── Simulation (mise en cache par paramètres) ────────────────────────────────
@st.cache_data(show_spinner=False)
def cached_simulation(altitude, beta, n_orbits, alpha_panels, epsilon_panels,
                       p_obc, p_payload, p_radio):
    """
    Cache la simulation pour éviter de recalculer si les paramètres n'ont pas changé.
    La fonction est recalculée seulement si un paramètre change.
    """
    cfg = load_default_config()

    # Surcharges depuis les sliders
    cfg["orbit"]["altitude_km"]    = altitude
    cfg["orbit"]["beta_angle_deg"] = beta
    cfg["simulation"]["n_orbits"]  = n_orbits

    # Mettre à jour alpha et epsilon pour les 4 faces latérales
    for face in ["plus_X", "minus_X", "plus_Y", "minus_Y"]:
        cfg["faces"][face]["alpha"]   = alpha_panels
        cfg["faces"][face]["epsilon"] = epsilon_panels

    cfg["power_dissipation"]["obc_W"]         = p_obc
    cfg["power_dissipation"]["payload_sun_W"] = p_payload
    cfg["power_dissipation"]["radio_sun_W"]   = p_radio

    model  = ThermalModel(cfg)
    result = run_simulation(model, cfg)
    return result, cfg


# ─── Utilitaires de visualisation ────────────────────────────────────────────

def get_eclipse_periods(result, config):
    """Calcule les intervalles d'éclipse pour les zones grisées sur les graphiques."""
    orb = OrbitalParameters(
        altitude_km = config["orbit"]["altitude_km"],
        beta_deg    = config["orbit"]["beta_angle_deg"],
    )
    periods = []
    in_ecl   = False
    t_start  = None

    for t in result.t:
        ecl = in_eclipse(t, orb)
        if ecl and not in_ecl:
            t_start = t
            in_ecl  = True
        elif not ecl and in_ecl:
            periods.append((t_start / 60.0, t / 60.0))
            in_ecl = False

    if in_ecl:
        periods.append((t_start / 60.0, result.t[-1] / 60.0))

    return periods


def add_eclipse_bands(fig, eclipse_periods, row=None, col=None):
    """Ajoute des bandes grisées pour les périodes d'éclipse."""
    kwargs = {}
    if row is not None:
        kwargs = {"row": row, "col": col}
    for i, (t0, t1) in enumerate(eclipse_periods):
        fig.add_vrect(
            x0=t0, x1=t1,
            fillcolor="rgba(50, 50, 80, 0.15)",
            line_width=0,
            annotation_text="🌑 Éclipse" if i == 0 else "",
            annotation_position="top left",
            annotation_font_size=10,
            **kwargs,
        )


# ─── Graphiques ──────────────────────────────────────────────────────────────

def plot_face_temperatures(result, eclipse_periods, limits):
    """Courbes de températures des 6 faces externes."""
    fig = go.Figure()
    face_names = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]

    for name in face_names:
        i = NODE_NAMES.index(name)
        fig.add_trace(go.Scatter(
            x    = result.t_min,
            y    = result.T_C[i],
            name = f"Face {name}",
            line = dict(color=NODE_COLORS[name], width=1.5),
            mode = "lines",
        ))

    add_eclipse_bands(fig, eclipse_periods)

    # Lignes de limites opérationnelles
    fig.add_hline(y=limits["panels"]["max_C"], line=dict(color="red", dash="dash", width=1),
                  annotation_text=f"Limite max panels ({limits['panels']['max_C']}°C)",
                  annotation_font_size=10)
    fig.add_hline(y=limits["panels"]["min_C"], line=dict(color="blue", dash="dash", width=1),
                  annotation_text=f"Limite min panels ({limits['panels']['min_C']}°C)",
                  annotation_font_size=10)

    fig.update_layout(
        title       = "Températures des 6 faces extérieures",
        xaxis_title = "Temps [min]",
        yaxis_title = "Température [°C]",
        hovermode   = "x unified",
        legend      = dict(orientation="h", yanchor="bottom", y=1.02),
        height      = 400,
    )
    return fig


def plot_internal_temperatures(result, eclipse_periods, limits):
    """Courbes de températures des nœuds internes."""
    fig = go.Figure()
    internal_names = ["Structure", "OBC/EPS", "Payload"]

    for name in internal_names:
        i = NODE_NAMES.index(name)
        fig.add_trace(go.Scatter(
            x    = result.t_min,
            y    = result.T_C[i],
            name = name,
            line = dict(color=NODE_COLORS[name], width=2),
            mode = "lines",
        ))

    add_eclipse_bands(fig, eclipse_periods)

    # Limite critique payload
    fig.add_hline(y=limits["payload"]["max_C"], line=dict(color="red", dash="dot", width=1),
                  annotation_text=f"Payload max ({limits['payload']['max_C']}°C)")
    fig.add_hline(y=limits["payload"]["min_C"], line=dict(color="blue", dash="dot", width=1),
                  annotation_text=f"Payload min ({limits['payload']['min_C']}°C)")

    fig.update_layout(
        title       = "Températures nœuds internes",
        xaxis_title = "Temps [min]",
        yaxis_title = "Température [°C]",
        hovermode   = "x unified",
        height      = 400,
    )
    return fig


def plot_heatmap(result):
    """Carte thermique : température de chaque nœud au fil du temps."""
    T_steady = result.T_steady_C
    t_steady = result.t_steady_min

    # Sous-échantillonner pour la heatmap (max 500 points)
    step = max(1, len(t_steady) // 500)

    fig = px.imshow(
        T_steady[:, ::step],
        x                   = t_steady[::step],
        y                   = NODE_NAMES,
        color_continuous_scale = "RdYlBu_r",
        labels              = {"x": "Temps [min]", "y": "Nœud", "color": "T [°C]"},
        title               = "Carte thermique — Tous les nœuds (régime établi)",
        aspect              = "auto",
    )
    fig.update_layout(height=350)
    return fig


def plot_margins(result, config):
    """Bar chart des marges thermiques froides et chaudes."""
    margins = result.thermal_margins(config["thermal_limits"])

    names       = list(margins.keys())
    m_cold      = [margins[n]["margin_cold_K"] for n in names]
    m_hot       = [margins[n]["margin_hot_K"]  for n in names]

    def color(val):
        if val < 0:   return "#E74C3C"   # Rouge : hors limites
        if val < 10:  return "#F39C12"   # Orange : marge faible
        return "#27AE60"                  # Vert : OK

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Marge froide [K]", "Marge chaude [K]"],
    )

    fig.add_trace(go.Bar(
        x             = names,
        y             = m_cold,
        marker_color  = [color(v) for v in m_cold],
        name          = "Marge froide",
        showlegend    = False,
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x             = names,
        y             = m_hot,
        marker_color  = [color(v) for v in m_hot],
        name          = "Marge chaude",
        showlegend    = False,
    ), row=1, col=2)

    # Ligne de référence marge = 0 (limite opérationnelle)
    for col in [1, 2]:
        fig.add_hline(y=0,  line=dict(color="black", width=1), row=1, col=col)
        fig.add_hline(y=10, line=dict(color="gray", dash="dot", width=1),
                      annotation_text="10K" if col == 2 else "",
                      row=1, col=col)

    fig.update_layout(
        title  = "Marges thermiques par nœud",
        height = 380,
    )
    return fig


# ─── Interface principale ─────────────────────────────────────────────────────

def main():
    st.title("🛰️ CubeSat 3U — Thermal Balance Dashboard")
    st.caption("Simulation thermique nodale en orbite basse (LEO) — Modèle à 9 nœuds")

    # ── Sidebar : paramètres ─────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Paramètres de simulation")

        st.subheader("🌍 Orbite")
        altitude = st.slider("Altitude [km]",          min_value=300,  max_value=800,  value=550,  step=50)
        beta     = st.slider("Angle β [°]",            min_value=0,    max_value=90,   value=30,   step=5)
        n_orbits = st.slider("Nombre d'orbites",       min_value=3,    max_value=10,   value=5,    step=1)

        st.subheader("🎨 Surfaces (faces latérales)")
        alpha_p  = st.slider("Absorptivité α",         min_value=0.05, max_value=0.95, value=0.23, step=0.01,
                              help="Fraction de lumière solaire absorbée (0=miroir, 1=noir)")
        epsilon_p = st.slider("Émissivité ε",          min_value=0.05, max_value=0.95, value=0.88, step=0.01,
                              help="Efficacité de rayonnement thermique (0=isolant, 1=parfait)")

        st.subheader("⚡ Puissance interne")
        p_obc     = st.slider("OBC [W]",               min_value=0.1,  max_value=2.0,  value=0.5,  step=0.1)
        p_payload = st.slider("Payload soleil [W]",    min_value=0.0,  max_value=5.0,  value=2.0,  step=0.1)
        p_radio   = st.slider("Radio soleil [W]",      min_value=0.0,  max_value=3.0,  value=0.8,  step=0.1)

        st.divider()
        run_btn = st.button("▶️  Lancer la simulation", type="primary", use_container_width=True)

    # ── Zone principale ──────────────────────────────────────────────────────
    if run_btn or "result" not in st.session_state:
        with st.spinner("Simulation en cours..."):
            result, config = cached_simulation(
                altitude, beta, n_orbits, alpha_p, epsilon_p, p_obc, p_payload, p_radio
            )
            st.session_state["result"] = result
            st.session_state["config"] = config
    else:
        result = st.session_state["result"]
        config = st.session_state["config"]

    # ── Métriques rapides en haut ────────────────────────────────────────────
    summary = result.summary()
    limits  = config["thermal_limits"]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Période orbitale",  f"{result.T_orb/60:.1f} min")
    col2.metric("T_min Payload",     f"{summary['Payload']['T_min_C']:.1f} °C",
                delta=f"{summary['Payload']['T_min_C'] - limits['payload']['min_C']:+.1f}K vs limite")
    col3.metric("T_max Payload",     f"{summary['Payload']['T_max_C']:.1f} °C",
                delta=f"{limits['payload']['max_C'] - summary['Payload']['T_max_C']:+.1f}K marge")
    col4.metric("ΔT face +Y (PV)",   f"{summary['+Y']['delta_T']:.1f} K")
    col5.metric("ΔT OBC/EPS",        f"{summary['OBC/EPS']['delta_T']:.1f} K")

    st.divider()

    # ── Graphiques ───────────────────────────────────────────────────────────
    eclipse_periods = get_eclipse_periods(result, config)

    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(
            plot_face_temperatures(result, eclipse_periods, limits),
            use_container_width=True,
        )
    with col_r:
        st.plotly_chart(
            plot_internal_temperatures(result, eclipse_periods, limits),
            use_container_width=True,
        )

    st.plotly_chart(plot_heatmap(result), use_container_width=True)
    st.plotly_chart(plot_margins(result, config), use_container_width=True)

    # ── Tableau récapitulatif ────────────────────────────────────────────────
    st.subheader("📊 Tableau des marges thermiques")
    margins = result.thermal_margins(limits)

    rows = []
    for name in NODE_NAMES:
        m  = margins[name]
        mc = m["margin_cold_K"]
        mh = m["margin_hot_K"]
        if mc < 0 or mh < 0:
            status = "🔴 HORS LIMITES"
        elif mc < 10 or mh < 10:
            status = "🟡 Marge faible"
        else:
            status = "🟢 OK"
        rows.append({
            "Nœud":        name,
            "T_min [°C]":  m["T_min_C"],
            "T_max [°C]":  m["T_max_C"],
            "Lim. min [°C]": m["limit_min_C"],
            "Lim. max [°C]": m["limit_max_C"],
            "M. froide [K]": mc,
            "M. chaude [K]": mh,
            "Statut":      status,
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.caption("Marges calculées sur le régime établi (après les orbites de transitoire initiales).")


if __name__ == "__main__":
    main()
