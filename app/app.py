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
import pandas as pd

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

# ─── CSS personnalisé ─────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Boîtes pédagogiques */
.info-box {
    background: linear-gradient(135deg, #1a1f3a 0%, #16213e 100%);
    border-left: 4px solid #4a9eff;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 12px 0;
    color: #e0e8ff;
}
.warn-box {
    background: linear-gradient(135deg, #2d1f00 0%, #1f1500 100%);
    border-left: 4px solid #ff9500;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 12px 0;
    color: #ffe0a0;
}
.success-box {
    background: linear-gradient(135deg, #001f1a 0%, #001510 100%);
    border-left: 4px solid #00c785;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 12px 0;
    color: #a0ffd8;
}
.physics-box {
    background: linear-gradient(135deg, #1f0030 0%, #150020 100%);
    border-left: 4px solid #bb86fc;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 12px 0;
    color: #e8d0ff;
}
.metric-explain {
    font-size: 12px;
    color: #8899bb;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

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

# ─── Descriptions pédagogiques des nœuds ─────────────────────────────────────
NODE_DESCRIPTIONS = {
    "+X": "Face droite — exposée au Soleil selon l'orientation",
    "-X": "Face gauche — opposée à +X",
    "+Y": "Face avant — porte souvent les panneaux solaires",
    "-Y": "Face arrière — opposée à +Y",
    "+Z": "Face haute — pointée vers le zénith (nadir côté −Z)",
    "-Z": "Face basse — pointée vers la Terre",
    "Structure": "Châssis aluminium — distribue la chaleur entre composants",
    "OBC/EPS": "Ordinateur de bord + gestion énergie — principal générateur de chaleur interne",
    "Payload": "Charge utile (caméra…) — composant le plus sensible thermiquement",
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
    cfg = load_default_config()
    cfg["orbit"]["altitude_km"]    = altitude
    cfg["orbit"]["beta_angle_deg"] = beta
    cfg["simulation"]["n_orbits"]  = n_orbits
    for face in ["plus_X", "minus_X", "plus_Y", "minus_Y"]:
        cfg["faces"][face]["alpha"]   = alpha_panels
        cfg["faces"][face]["epsilon"] = epsilon_panels
    cfg["power_dissipation"]["obc_W"]         = p_obc
    cfg["power_dissipation"]["payload_sun_W"] = p_payload
    cfg["power_dissipation"]["radio_sun_W"]   = p_radio
    model  = ThermalModel(cfg)
    result = run_simulation(model, cfg)
    return result, cfg


# ─── Utilitaires ─────────────────────────────────────────────────────────────

def get_eclipse_periods(result, config):
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
            t_start = t; in_ecl = True
        elif not ecl and in_ecl:
            periods.append((t_start / 60.0, t / 60.0)); in_ecl = False
    if in_ecl:
        periods.append((t_start / 60.0, result.t[-1] / 60.0))
    return periods


def add_eclipse_bands(fig, eclipse_periods, row=None, col=None):
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


def orbital_period_minutes(altitude_km):
    """Calcule la période orbitale approximative en minutes."""
    R_earth = 6371
    mu = 398600.4418  # km³/s²
    r = R_earth + altitude_km
    T = 2 * np.pi * np.sqrt(r**3 / mu)
    return T / 60.0


# ─── Graphiques ──────────────────────────────────────────────────────────────

def plot_face_temperatures(result, eclipse_periods, limits):
    fig = go.Figure()
    face_names = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
    for name in face_names:
        i = NODE_NAMES.index(name)
        fig.add_trace(go.Scatter(
            x=result.t_min, y=result.T_C[i],
            name=f"Face {name}",
            line=dict(color=NODE_COLORS[name], width=1.5),
            mode="lines",
            hovertemplate=f"<b>Face {name}</b><br>t = %{{x:.1f}} min<br>T = %{{y:.1f}} °C<extra></extra>",
        ))
    add_eclipse_bands(fig, eclipse_periods)
    fig.add_hline(y=limits["panels"]["max_C"],
                  line=dict(color="red", dash="dash", width=1),
                  annotation_text=f"⚠ Limite max panels ({limits['panels']['max_C']}°C)",
                  annotation_font_size=10)
    fig.add_hline(y=limits["panels"]["min_C"],
                  line=dict(color="blue", dash="dash", width=1),
                  annotation_text=f"⚠ Limite min panels ({limits['panels']['min_C']}°C)",
                  annotation_font_size=10)
    fig.update_layout(
        title="Températures des 6 faces extérieures",
        xaxis_title="Temps [min]",
        yaxis_title="Température [°C]",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=420,
    )
    return fig


def plot_internal_temperatures(result, eclipse_periods, limits):
    fig = go.Figure()
    internal_names = ["Structure", "OBC/EPS", "Payload"]
    for name in internal_names:
        i = NODE_NAMES.index(name)
        fig.add_trace(go.Scatter(
            x=result.t_min, y=result.T_C[i],
            name=name,
            line=dict(color=NODE_COLORS[name], width=2),
            mode="lines",
            hovertemplate=f"<b>{name}</b><br>t = %{{x:.1f}} min<br>T = %{{y:.1f}} °C<extra></extra>",
        ))
    add_eclipse_bands(fig, eclipse_periods)
    fig.add_hline(y=limits["payload"]["max_C"],
                  line=dict(color="red", dash="dot", width=1),
                  annotation_text=f"Payload max ({limits['payload']['max_C']}°C)")
    fig.add_hline(y=limits["payload"]["min_C"],
                  line=dict(color="blue", dash="dot", width=1),
                  annotation_text=f"Payload min ({limits['payload']['min_C']}°C)")
    fig.update_layout(
        title="Températures nœuds internes",
        xaxis_title="Temps [min]",
        yaxis_title="Température [°C]",
        hovermode="x unified",
        height=420,
    )
    return fig


def plot_heatmap(result):
    T_steady = result.T_steady_C
    t_steady = result.t_steady_min
    step = max(1, len(t_steady) // 500)
    fig = px.imshow(
        T_steady[:, ::step],
        x=t_steady[::step],
        y=NODE_NAMES,
        color_continuous_scale="RdYlBu_r",
        labels={"x": "Temps [min]", "y": "Nœud", "color": "T [°C]"},
        title="Carte thermique — Tous les nœuds (régime établi)",
        aspect="auto",
    )
    fig.update_layout(height=360)
    return fig


def plot_margins(result, config):
    margins = result.thermal_margins(config["thermal_limits"])
    names  = list(margins.keys())
    m_cold = [margins[n]["margin_cold_K"] for n in names]
    m_hot  = [margins[n]["margin_hot_K"]  for n in names]

    def color(val):
        if val < 0:  return "#E74C3C"
        if val < 10: return "#F39C12"
        return "#27AE60"

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=["Marge froide [K]", "Marge chaude [K]"])
    fig.add_trace(go.Bar(
        x=names, y=m_cold,
        marker_color=[color(v) for v in m_cold],
        name="Marge froide", showlegend=False,
        hovertemplate="<b>%{x}</b><br>Marge froide = %{y:.1f} K<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=names, y=m_hot,
        marker_color=[color(v) for v in m_hot],
        name="Marge chaude", showlegend=False,
        hovertemplate="<b>%{x}</b><br>Marge chaude = %{y:.1f} K<extra></extra>",
    ), row=1, col=2)
    for col in [1, 2]:
        fig.add_hline(y=0,  line=dict(color="black", width=1), row=1, col=col)
        fig.add_hline(y=10, line=dict(color="gray", dash="dot", width=1),
                      annotation_text="Seuil 10K" if col == 2 else "",
                      row=1, col=col)
    fig.update_layout(title="Marges thermiques par nœud", height=400)
    return fig


def plot_node_overview(result, eclipse_periods):
    """Graphique multi-panneaux : un sous-graphique par nœud."""
    n = len(NODE_NAMES)
    cols = 3
    rows = (n + cols - 1) // cols
    titles = [f"{name} — {NODE_DESCRIPTIONS[name][:30]}…"
              if len(NODE_DESCRIPTIONS[name]) > 30 else f"{name} — {NODE_DESCRIPTIONS[name]}"
              for name in NODE_NAMES]
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=titles, shared_xaxes=True)
    for idx, name in enumerate(NODE_NAMES):
        r = idx // cols + 1
        c = idx %  cols + 1
        i = NODE_NAMES.index(name)
        fig.add_trace(go.Scatter(
            x=result.t_min, y=result.T_C[i],
            name=name,
            line=dict(color=NODE_COLORS[name], width=1.5),
            mode="lines",
            showlegend=False,
        ), row=r, col=c)
        add_eclipse_bands(fig, eclipse_periods, row=r, col=c)
    fig.update_layout(height=650, title="Vue individuelle — Température de chaque nœud")
    fig.update_xaxes(title_text="Temps [min]")
    fig.update_yaxes(title_text="T [°C]")
    return fig


def build_summary_df(result, config):
    """Construit le dataframe de marges thermiques."""
    summary = result.summary()
    limits  = config["thermal_limits"]
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
            "Nœud":            name,
            "Description":     NODE_DESCRIPTIONS[name],
            "T_min [°C]":      round(m["T_min_C"], 1),
            "T_max [°C]":      round(m["T_max_C"], 1),
            "ΔT [K]":          round(m["T_max_C"] - m["T_min_C"], 1),
            "Lim. min [°C]":   m["limit_min_C"],
            "Lim. max [°C]":   m["limit_max_C"],
            "Marge froide [K]": round(mc, 1),
            "Marge chaude [K]": round(mh, 1),
            "Statut":          status,
        })
    return pd.DataFrame(rows)


# ─── 3D Visualisation animée ──────────────────────────────────────────────────

def temp_to_color(T: float, T_min: float, T_max: float) -> str:
    """
    Mappe une température → couleur RGB (style RdYlBu_r).
    Bleu froid → jaune médian → rouge chaud.
    """
    t = float(np.clip((T - T_min) / max(float(T_max - T_min), 1.0), 0.0, 1.0))
    pts = [
        (0.00, (49,  54, 149)),
        (0.25, (116, 173, 209)),
        (0.50, (255, 255, 191)),
        (0.75, (253, 141,  60)),
        (1.00, (215,  48,  39)),
    ]
    for i in range(len(pts) - 1):
        t0, c0 = pts[i]
        t1, c1 = pts[i + 1]
        if t <= t1 + 1e-9:
            f = (t - t0) / (t1 - t0)
            r = int(c0[0] + f * (c1[0] - c0[0]))
            g = int(c0[1] + f * (c1[1] - c0[1]))
            b = int(c0[2] + f * (c1[2] - c0[2]))
            return f"rgb({r},{g},{b})"
    return "rgb(215,48,39)"


def _orbit_xyz(altitude_km: float, beta_deg: float, t_seconds: np.ndarray):
    """Positions 3D sur l'orbite circulaire + flag éclipse pour chaque instant."""
    R_earth = 6371.0
    mu      = 398600.4418
    r       = R_earth + altitude_km
    T_orb   = 2.0 * np.pi * np.sqrt(r ** 3 / mu)
    beta    = np.radians(beta_deg)
    theta   = 2.0 * np.pi * t_seconds / T_orb
    x = r * np.cos(theta)
    y = r * np.sin(theta) * np.cos(beta)
    z = r * np.sin(theta) * np.sin(beta)
    orb    = OrbitalParameters(altitude_km=altitude_km, beta_deg=beta_deg)
    is_ecl = np.array([in_eclipse(float(ts), orb) for ts in t_seconds], dtype=bool)
    return x, y, z, is_ecl


def build_3d_animation(result, config, N_frames: int = 80) -> go.Figure:
    """
    Figure Plotly animée (▶ Play / ⏸ Pause + slider temporel) avec deux scènes 3D :
      - Gauche : Terre + trajectoire orbitale colorée + satellite mobile
      - Droite  : CubeSat 3U dont les faces et composants changent de couleur
                  en fonction des températures issues de la simulation
    """
    altitude = config["orbit"]["altitude_km"]
    beta_deg = config["orbit"]["beta_angle_deg"]
    R_earth  = 6371.0
    r_orb    = R_earth + altitude

    # ── Sous-échantillonnage ──────────────────────────────────────────────────
    fidxs  = np.linspace(0, len(result.t) - 1, N_frames, dtype=int)
    t_secs = result.t[fidxs]
    t_mins = result.t_min[fidxs]

    # Positions du satellite aux instants des frames
    xf, yf, zf, ecl = _orbit_xyz(altitude, beta_deg, t_secs)

    # Trajectoire de fond (plus dense, statique)
    t_bg                 = np.linspace(0.0, float(result.t[-1]), 400)
    xb, yb, zb, ecl_bg  = _orbit_xyz(altitude, beta_deg, t_bg)
    orb_col              = np.where(ecl_bg, 0.0, 1.0).tolist()

    # ── Plage thermique globale ───────────────────────────────────────────────
    T_min = float(result.T_C.min())
    T_max = float(result.T_C.max())

    # ── Géométrie CubeSat 3U (ratio 1:1:3) ───────────────────────────────────
    HX, HY, HZ = 1.0, 1.0, 3.0
    vx = np.array([-HX, +HX, +HX, -HX, -HX, +HX, +HX, -HX], dtype=float)
    vy = np.array([-HY, -HY, +HY, +HY, -HY, -HY, +HY, +HY], dtype=float)
    vz = np.array([-HZ, -HZ, -HZ, -HZ, +HZ, +HZ, +HZ, +HZ], dtype=float)

    FACE_ORDER = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
    FACE_QUADS = {
        "+X": [1, 5, 6, 2], "-X": [0, 3, 7, 4],
        "+Y": [3, 2, 6, 7], "-Y": [0, 4, 5, 1],
        "+Z": [4, 7, 6, 5], "-Z": [0, 1, 2, 3],
    }
    mi, mj, mk = [], [], []
    for fn in FACE_ORDER:
        a, b, c, d = FACE_QUADS[fn]
        mi += [a, a]; mj += [b, c]; mk += [c, d]

    def face_colors_at(full_idx: int):
        cols = []
        for fn in FACE_ORDER:
            T   = float(result.T_C[NODE_NAMES.index(fn), full_idx])
            col = temp_to_color(T, T_min, T_max)
            cols += [col, col]    # 2 triangles par face
        return cols

    # Wireframe en un seul Scatter3d (NaN = séparateurs de segments)
    EDGES = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    wx, wy, wz = [], [], []
    for a, b in EDGES:
        wx += [vx[a], vx[b], None]
        wy += [vy[a], vy[b], None]
        wz += [vz[a], vz[b], None]

    FACE_LBL_POS = {
        "+X": ( HX+0.55, 0,        0       ),
        "-X": (-HX-0.55, 0,        0       ),
        "+Y": ( 0,        HY+0.55, 0       ),
        "-Y": ( 0,       -HY-0.55, 0       ),
        "+Z": ( 0,        0,        HZ+0.8 ),
        "-Z": ( 0,        0,       -HZ-0.8 ),
    }

    INTERNALS = [
        ("OBC/EPS",   0.0, 0.0, -1.5, "💻"),
        ("Structure", 0.0, 0.0,  0.0, "🔩"),
        ("Payload",   0.0, 0.0, +1.5, "📷"),
    ]

    # ── Construction de la figure de base ─────────────────────────────────────
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "scene"}, {"type": "scene"}]],
        column_widths=[0.55, 0.45],
        subplot_titles=["🌍  Trajectoire orbitale", "🛰️  CubeSat — Thermique en temps réel"],
        horizontal_spacing=0.01,
    )

    # ── SCENE 1 : Terre + orbite + satellite ──────────────────────────────────
    # trace 0 — Terre (sphère)
    n_e = 42
    u_e = np.linspace(0, 2 * np.pi, n_e)
    v_e = np.linspace(0, np.pi,     n_e)
    xe_s = R_earth * np.outer(np.cos(u_e), np.sin(v_e))
    ye_s = R_earth * np.outer(np.sin(u_e), np.sin(v_e))
    ze_s = R_earth * np.outer(np.ones(n_e), np.cos(v_e))
    fig.add_trace(go.Surface(
        x=xe_s, y=ye_s, z=ze_s,
        colorscale=[[0,"#091540"],[0.3,"#14459e"],[0.65,"#2580c9"],[1,"#59b5e8"]],
        showscale=False, opacity=0.88, hoverinfo="skip", name="Terre",
        lighting=dict(ambient=0.55, diffuse=0.75),
    ), row=1, col=1)

    # trace 1 — Trajectoire de fond (soleil/éclipse)
    fig.add_trace(go.Scatter3d(
        x=xb.tolist(), y=yb.tolist(), z=zb.tolist(),
        mode="lines",
        line=dict(color=orb_col, colorscale=[[0,"#0f1f3f"],[1,"#FFD700"]], width=3),
        hoverinfo="skip", name="Orbite",
    ), row=1, col=1)

    # trace 2 — Position courante du satellite  ← ANIMÉ
    fig.add_trace(go.Scatter3d(
        x=[float(xf[0])], y=[float(yf[0])], z=[float(zf[0])],
        mode="markers",
        marker=dict(size=10, color="#ffffff", symbol="diamond",
                    line=dict(color="#ff4444", width=2)),
        name="🛰️ Satellite",
        hovertemplate="<b>CubeSat</b><br>X=%{x:.0f} km<br>Y=%{y:.0f} km<extra></extra>",
    ), row=1, col=1)

    # trace 3 — Soleil (statique)
    fig.add_trace(go.Scatter3d(
        x=[r_orb * 1.78], y=[0], z=[0],
        mode="markers+text", text=["☀️"],
        textfont=dict(size=20), textposition="middle right",
        marker=dict(size=14, color="#FFD700"),
        name="Soleil", hoverinfo="skip",
    ), row=1, col=1)

    # ── SCENE 2 : CubeSat ────────────────────────────────────────────────────
    init_idx = int(fidxs[0])

    # trace 4 — Faces colorées  ← ANIMÉ
    fig.add_trace(go.Mesh3d(
        x=vx.tolist(), y=vy.tolist(), z=vz.tolist(),
        i=mi, j=mj, k=mk,
        facecolor=face_colors_at(init_idx),
        flatshading=True, opacity=1.0, showscale=False, hoverinfo="skip",
        name="Faces",
        lighting=dict(ambient=0.7, diffuse=0.6, specular=0.2),
        lightposition=dict(x=3, y=3, z=6),
    ), row=1, col=2)

    # trace 5 — Wireframe (statique)
    fig.add_trace(go.Scatter3d(
        x=wx, y=wy, z=wz, mode="lines",
        line=dict(color="rgba(255,255,255,0.28)", width=2),
        hoverinfo="skip", showlegend=False,
    ), row=1, col=2)

    # traces 6, 7, 8 — Composants internes  ← ANIMÉS
    for name, xi, yi, zi, emoji in INTERNALS:
        ni  = NODE_NAMES.index(name)
        T0  = float(result.T_C[ni, init_idx])
        col0 = temp_to_color(T0, T_min, T_max)
        fig.add_trace(go.Scatter3d(
            x=[xi], y=[yi], z=[zi],
            mode="markers+text",
            marker=dict(size=12, color=col0, opacity=0.95,
                        line=dict(color="white", width=2)),
            text=[f"  {emoji} {name}<br>  {T0:.1f}°C"],
            textposition="middle right",
            textfont=dict(color="white", size=9),
            name=name,
        ), row=1, col=2)

    # traces 9-14 — Labels de chaque face  ← ANIMÉS
    for fn in FACE_ORDER:
        ni   = NODE_NAMES.index(fn)
        T0   = float(result.T_C[ni, init_idx])
        fx, fy, fz = FACE_LBL_POS[fn]
        fig.add_trace(go.Scatter3d(
            x=[fx], y=[fy], z=[fz],
            mode="text",
            text=[f"<b>{fn}</b><br>{T0:.1f}°C"],
            textfont=dict(color="white", size=9),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=2)

    # trace 15 — Barre de couleur (trace fantôme)
    fig.add_trace(go.Scatter3d(
        x=[None], y=[None], z=[None], mode="markers",
        marker=dict(
            colorscale=[[0,"rgb(49,54,149)"],[0.25,"rgb(116,173,209)"],
                        [0.5,"rgb(255,255,191)"],[0.75,"rgb(253,141,60)"],
                        [1,"rgb(215,48,39)"]],
            cmin=T_min, cmax=T_max, color=[T_min],
            colorbar=dict(
                title=dict(text="T [°C]", font=dict(color="white", size=11)),
                tickfont=dict(color="white", size=10),
                len=0.55, thickness=14, x=1.01,
            ),
            showscale=True,
        ),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=2)

    # ── Frames d'animation ────────────────────────────────────────────────────
    # Traces animées (dans l'ordre) :
    # idx 2  → satellite marker
    # idx 4  → cubesat faces (Mesh3d)
    # idx 6  → OBC/EPS
    # idx 7  → Structure
    # idx 8  → Payload
    # idx 9-14 → labels +X -X +Y -Y +Z -Z
    ANIM_TRACES = [2, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14]

    frames       = []
    slider_steps = []

    for fi, (full_idx, t_m) in enumerate(zip(fidxs.tolist(), t_mins.tolist())):
        full_idx = int(full_idx)
        t_m      = float(t_m)
        x_s, y_s, z_s = float(xf[fi]), float(yf[fi]), float(zf[fi])
        is_ecl_f       = bool(ecl[fi])
        orbit_n        = t_m / (result.T_orb / 60.0)
        ecl_icon       = "🌑" if is_ecl_f else "☀️"
        sat_col        = "#888888" if is_ecl_f else "#ffffff"

        fdata = []

        # trace 2 — satellite marker
        fdata.append(go.Scatter3d(
            x=[x_s], y=[y_s], z=[z_s],
            marker=dict(size=10, color=sat_col, symbol="diamond",
                        line=dict(color="#ff4444" if not is_ecl_f else "#553333", width=2)),
        ))

        # trace 4 — faces CubeSat
        fdata.append(go.Mesh3d(facecolor=face_colors_at(full_idx)))

        # traces 6-8 — composants internes
        for name, xi, yi, zi, emoji in INTERNALS:
            ni  = NODE_NAMES.index(name)
            T   = float(result.T_C[ni, full_idx])
            col = temp_to_color(T, T_min, T_max)
            fdata.append(go.Scatter3d(
                x=[xi], y=[yi], z=[zi],
                marker=dict(color=col),
                text=[f"  {emoji} {name}<br>  {T:.1f}°C"],
            ))

        # traces 9-14 — labels faces
        for fn in FACE_ORDER:
            ni  = NODE_NAMES.index(fn)
            T   = float(result.T_C[ni, full_idx])
            fx, fy, fz = FACE_LBL_POS[fn]
            fdata.append(go.Scatter3d(
                x=[fx], y=[fy], z=[fz],
                text=[f"<b>{fn}</b><br>{T:.1f}°C"],
            ))

        frame_name = f"f{fi:03d}"
        frames.append(go.Frame(
            data=fdata,
            traces=ANIM_TRACES,
            name=frame_name,
            layout=go.Layout(title=dict(
                text=f"⏱ {t_m:.1f} min · Orbite {orbit_n:.2f} · {ecl_icon}",
                font=dict(color="white", size=13),
            )),
        ))
        slider_steps.append({
            "args": [[frame_name], {"frame":{"duration":0,"redraw":True}, "mode":"immediate"}],
            "label": f"{t_m:.0f}",
            "method": "animate",
        })

    fig.frames = frames

    # ── Mise en page globale ──────────────────────────────────────────────────
    r_max = r_orb * 1.88
    t0_str = f"{float(t_mins[0]):.1f}"

    fig.update_layout(
        paper_bgcolor="#04040f",
        plot_bgcolor="#04040f",
        font=dict(color="white"),
        height=660,
        margin=dict(l=0, r=70, t=80, b=100),
        title=dict(
            text=f"⏱ {t0_str} min · Orbite 0.00 · ☀️",
            font=dict(color="white", size=13),
            x=0.5,
        ),
        # Scène 1 : orbite
        scene=dict(
            bgcolor="#04040f",
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[-r_max, r_max]),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[-r_max, r_max]),
            zaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[-r_max, r_max]),
            aspectmode="cube",
            camera=dict(up=dict(x=0,y=0,z=1), eye=dict(x=1.45,y=1.45,z=0.7)),
        ),
        # Scène 2 : CubeSat
        scene2=dict(
            bgcolor="#04040f",
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[-HX*3.2, HX*3.2]),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[-HY*3.2, HY*3.2]),
            zaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[-HZ*1.75, HZ*1.75]),
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=3),
            camera=dict(up=dict(x=0,y=0,z=1), eye=dict(x=2.1,y=2.1,z=0.65)),
        ),
        # Boutons Play / Pause
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            y=-0.10, x=0.0, xanchor="left", yanchor="top",
            pad=dict(t=5, r=10),
            bgcolor="#1a1a3a", bordercolor="#4a4aaa",
            font=dict(color="white", size=13),
            buttons=[
                dict(
                    label="▶  Play",
                    method="animate",
                    args=[None, {
                        "frame":       {"duration": 90, "redraw": True},
                        "fromcurrent": True,
                        "transition":  {"duration": 0},
                        "mode":        "immediate",
                    }],
                ),
                dict(
                    label="⏸  Pause",
                    method="animate",
                    args=[[None], {
                        "frame": {"duration": 0, "redraw": False},
                        "mode":  "immediate",
                    }],
                ),
            ],
        )],
        # Slider temporel
        sliders=[dict(
            active=0,
            currentvalue=dict(
                prefix="t = ",
                suffix=" min",
                font=dict(color="white", size=12),
                visible=True,
                xanchor="center",
            ),
            pad=dict(b=10, t=55),
            len=0.82, x=0.09, y=0,
            font=dict(color="white", size=9),
            bgcolor="#1a1a3a",
            bordercolor="#3a3a6a",
            tickcolor="white",
            steps=slider_steps,
        )],
        legend=dict(
            font=dict(color="white", size=10),
            bgcolor="rgba(0,0,0,0.45)",
            x=0.0, y=1.0,
        ),
    )
    return fig


# ─── Sections pédagogiques ────────────────────────────────────────────────────

def show_intro_card():
    st.markdown("""
<div class="info-box">
<strong>🛰️ Comment fonctionne cette simulation ?</strong><br><br>
Ce dashboard simule le comportement thermique d'un <strong>CubeSat 3U</strong> (10×10×30 cm, ~4 kg)
en orbite basse (LEO). Le satellite est découpé en <strong>9 zones thermiques</strong> (nœuds).
Pour chacune, le programme résout en temps réel l'équation de bilan énergétique :<br><br>
<code>Chaleur reçue (Soleil + Terre + électronique) − Chaleur rayonnée vers l'espace = ΔTempérature</code><br><br>
Modifiez les paramètres à gauche et lancez la simulation pour voir comment les températures réagissent.
</div>
""", unsafe_allow_html=True)


def show_orbital_explainer(altitude, beta, t_orb):
    eclipse_frac = max(0, 1 - 1 / np.cos(np.radians(min(beta, 66))))
    if beta >= 66:
        eclipse_text = "☀️ <strong>Aucune éclipse</strong> à cet angle β — le satellite est au soleil en permanence (cas le plus chaud)."
        eclipse_color = "warn-box"
    else:
        t_ecl = t_orb * (1 - 60/96)  # approximation
        eclipse_text = f"🌑 Le satellite traverse l'ombre de la Terre à chaque orbite (~{t_ecl:.0f} min d'éclipse sur {t_orb:.0f} min)."
        eclipse_color = "info-box"

    st.markdown(f"""
<div class="{eclipse_color}">
<strong>📐 Angle β = {beta}°</strong> — Ce paramètre détermine l'inclinaison du plan orbital par rapport au Soleil.<br>
• <strong>β = 0°</strong> → Soleil dans le plan orbital → éclipses longues → cas le plus <em>froid</em><br>
• <strong>β = 90°</strong> → Soleil perpendiculaire → aucune éclipse → cas le plus <em>chaud</em><br><br>
{eclipse_text}
</div>
""", unsafe_allow_html=True)


def show_coating_explainer(alpha, epsilon):
    if alpha < 0.3:
        alpha_desc = "surface claire (peinture blanche) — absorbe peu de solaire"
    elif alpha < 0.6:
        alpha_desc = "surface intermédiaire"
    else:
        alpha_desc = "surface sombre — absorbe beaucoup de solaire"

    if epsilon > 0.7:
        eps_desc = "bon radiateur — évacue efficacement la chaleur vers l'espace"
    elif epsilon > 0.4:
        eps_desc = "radiateur moyen"
    else:
        eps_desc = "mauvais radiateur — garde la chaleur (type aluminium nu)"

    balance = "⚖️ Équilibre thermique raisonnable." if (epsilon / max(alpha, 0.01)) > 2 else "🔥 Ratio α/ε élevé → tendance à surchauffer."

    st.markdown(f"""
<div class="physics-box">
<strong>🎨 Propriétés de surface choisies</strong><br>
• α = {alpha:.2f} → {alpha_desc}<br>
• ε = {epsilon:.2f} → {eps_desc}<br><br>
{balance} Le ratio ε/α = <strong>{epsilon/max(alpha,0.01):.2f}</strong> gouverne la température d'équilibre des faces externes.
<br><small>Plus ε/α est grand, plus la face est froide à l'équilibre.</small>
</div>
""", unsafe_allow_html=True)


def show_power_explainer(p_obc, p_payload, p_radio):
    total = p_obc + p_payload + p_radio
    st.markdown(f"""
<div class="physics-box">
<strong>⚡ Dissipation interne totale : {total:.1f} W</strong><br>
Toute énergie électrique consommée par les composants finit en <em>chaleur</em> (loi de conservation).
Cette chaleur ne peut s'évacuer que par rayonnement — il n'y a pas de ventilation dans l'espace.<br><br>
• OBC/EPS : {p_obc:.1f} W &nbsp;|&nbsp; Payload : {p_payload:.1f} W &nbsp;|&nbsp; Radio : {p_radio:.1f} W
</div>
""", unsafe_allow_html=True)


def show_graph_reading_guide():
    with st.expander("📖 Comment lire ces graphiques ?", expanded=False):
        st.markdown("""
**Zones grisées 🌑** — Périodes d'éclipse. Le satellite passe dans l'ombre de la Terre :
plus de flux solaire, la température chute progressivement.

**Lignes pointillées rouges/bleues** — Limites opérationnelles des composants.
Si une courbe franchit ces lignes, le composant risque de dysfonctionner ou d'être endommagé.

**Forme des courbes** — Les températures montent rapidement à l'entrée dans le soleil
(flux solaire intense) et descendent plus lentement à l'éclipse (inertie thermique de la masse).

**Régime établi** — Après 1 à 2 orbites, les températures suivent un cycle stable et répétitif.
La simulation utilise ce régime pour calculer les marges thermiques.

**Les marges thermiques** sont calculées sur le régime établi (orbites stables, après le transitoire initial) :
- 🟢 > 10 K → Design robuste
- 🟡 0–10 K → Marge faible, surveiller
- 🔴 < 0 K → Hors limites, le composant mourrait en orbite
        """)


def show_nodes_guide():
    with st.expander("🗺️ Comprendre les 9 nœuds thermiques", expanded=False):
        st.markdown("""
Le CubeSat est modélisé comme **9 zones de température uniforme** :

```
         ┌─────────┐
         │  +Z     │  ← Face haute (vers le zénith)
    ┌────┼─────────┼────┐
 -X │    │Structure│    │ +X   ← Faces latérales
    │    │ OBC/EPS │    │
    │    │ Payload │    │
    └────┼─────────┼────┘
    -Y   │  -Z     │   +Y  ← +Y porte souvent les panneaux solaires
         └─────────┘
```

**Connexions thermiques :**
- Les faces extérieures échangent de la chaleur avec la **Structure** par conduction
- La **Structure** transmet la chaleur vers **OBC/EPS** et **Payload**
- Chaque face extérieure rayonne vers l'espace et reçoit les flux solaire + terrestre

**Composants critiques :**
- 💻 **OBC/EPS** : ordinateur de bord + gestion d'énergie, principal générateur de chaleur (~0.5 W continu)
- 📷 **Payload** : caméra ou instrument scientifique, le plus sensible thermiquement
        """)


def show_glossary():
    with st.expander("📚 Glossaire", expanded=False):
        st.markdown("""
| Terme | Définition |
|---|---|
| **β (angle bêta)** | Angle entre le plan de l'orbite et la direction du Soleil. Détermine la durée et l'existence des éclipses. |
| **α (absorptivité)** | Fraction de la lumière solaire absorbée par une surface (0 = miroir, 1 = noir absolu). |
| **ε (émissivité)** | Efficacité avec laquelle une surface rayonne sa chaleur vers l'espace (0 = parfait isolant, 1 = radiateur parfait). |
| **Albédo** | Lumière solaire réfléchie par la Terre (~30%). Contribue au chauffage des faces inférieures. |
| **IR terrestre** | Rayonnement infrarouge émis par la Terre (permanent, présent même en éclipse). |
| **Nœud thermique** | Zone du satellite supposée à température uniforme dans le modèle. |
| **Marge thermique** | Écart entre la température extrême atteinte et la limite opérationnelle du composant. |
| **Régime établi** | Phase stable après les premières orbites de transitoire. |
| **LEO** | Low Earth Orbit — orbite basse, 300–800 km d'altitude. |
| **CubeSat 3U** | CubeSat de 3 unités = 10×10×30 cm, environ 4 kg. |
        """)


# ─── Interface principale ─────────────────────────────────────────────────────

def main():
    st.title("🛰️ CubeSat 3U — Simulation Thermique")
    st.caption("Modèle nodal à 9 zones · Orbite basse (LEO) · Solaire + Albédo + IR terrestre + Dissipation interne")

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Paramètres")

        # Aide générale dans la sidebar
        with st.expander("❓ Comment utiliser ce dashboard", expanded=False):
            st.markdown("""
1. **Ajustez les paramètres** ci-dessous (orbite, surfaces, puissance)
2. **Cliquez sur "Lancer"** pour calculer
3. **Explorez les onglets** : résultats, graphiques, pédagogie
4. **Observez les marges** : vert = OK, jaune = attention, rouge = danger

💡 Essayez de faire varier l'angle β entre 0° et 90° pour voir l'effet des éclipses.
            """)

        st.subheader("🌍 Orbite")
        altitude = st.slider(
            "Altitude [km]", min_value=300, max_value=800, value=550, step=50,
            help="Hauteur de l'orbite au-dessus de la Terre. La période orbitale et les flux IR/albédo dépendent de l'altitude."
        )
        beta = st.slider(
            "Angle β [°]", min_value=0, max_value=90, value=30, step=5,
            help="Angle entre le plan orbital et la direction du Soleil. β=0° → éclipses longues (froid). β≥66° → aucune éclipse (chaud)."
        )
        n_orbits = st.slider(
            "Nombre d'orbites à simuler", min_value=3, max_value=10, value=5, step=1,
            help="Plus d'orbites = transitoire initial inclus + régime établi plus précis. 5 orbites suffisent généralement."
        )

        t_orb = orbital_period_minutes(altitude)
        st.caption(f"⏱ Période orbitale estimée : **{t_orb:.1f} min**")
        if beta >= 66:
            st.info("☀️ Aucune éclipse à β ≥ 66° — satellite en soleil permanent.")
        else:
            t_ecl_approx = t_orb * 0.375
            st.caption(f"🌑 Éclipse estimée : ~{t_ecl_approx:.0f} min/orbite")

        st.subheader("🎨 Surfaces (faces latérales)")
        alpha_p = st.slider(
            "Absorptivité α", min_value=0.05, max_value=0.95, value=0.23, step=0.01,
            help="Fraction de lumière solaire absorbée. Peinture blanche ≈ 0.23 | Aluminium nu ≈ 0.37 | Panneau solaire ≈ 0.92"
        )
        epsilon_p = st.slider(
            "Émissivité ε", min_value=0.05, max_value=0.95, value=0.88, step=0.01,
            help="Efficacité de rayonnement thermique. Peinture blanche ≈ 0.88 | Aluminium nu ≈ 0.05 | Panneau solaire ≈ 0.85"
        )

        # Indicateur visuel du matériau correspondant
        if alpha_p <= 0.25 and epsilon_p >= 0.80:
            st.success("🖌️ Proche de la peinture blanche — bon radiateur")
        elif alpha_p >= 0.80:
            st.warning("⚡ Proche d'un panneau solaire — chaud mais bon rayonnement")
        elif epsilon_p <= 0.15:
            st.error("⚠️ Aluminium nu — mauvais radiateur, risque de surchauffe")
        else:
            st.info(f"📊 Ratio ε/α = {epsilon_p/alpha_p:.1f}")

        st.subheader("⚡ Puissance interne")
        p_obc = st.slider(
            "OBC/EPS [W]", min_value=0.1, max_value=2.0, value=0.5, step=0.1,
            help="Dissipation de l'ordinateur de bord et de la gestion d'énergie. Fonctionne en permanence (soleil + éclipse)."
        )
        p_payload = st.slider(
            "Payload au soleil [W]", min_value=0.0, max_value=5.0, value=2.0, step=0.1,
            help="Dissipation de la charge utile (caméra...) quand elle est active au soleil."
        )
        p_radio = st.slider(
            "Radio au soleil [W]", min_value=0.0, max_value=3.0, value=0.8, step=0.1,
            help="Dissipation du module radio (transmission de données) lors des passes au-dessus des stations sol."
        )

        total_power = p_obc + p_payload + p_radio
        st.caption(f"⚡ Total max : **{total_power:.1f} W** (tout actif simultanément)")

        st.divider()
        run_btn = st.button("▶️  Lancer la simulation", type="primary", use_container_width=True)

    # ── Lancement simulation ─────────────────────────────────────────────────
    if run_btn or "result" not in st.session_state:
        with st.spinner("⏳ Simulation en cours (résolution de 9 équations différentielles couplées)…"):
            result, config = cached_simulation(
                altitude, beta, n_orbits, alpha_p, epsilon_p, p_obc, p_payload, p_radio
            )
            st.session_state["result"] = result
            st.session_state["config"] = config
    else:
        result = st.session_state["result"]
        config = st.session_state["config"]

    summary = result.summary()
    limits  = config["thermal_limits"]
    eclipse_periods = get_eclipse_periods(result, config)

    # ── Intro pédagogique ────────────────────────────────────────────────────
    show_intro_card()

    # ── Métriques rapides ────────────────────────────────────────────────────
    st.subheader("📈 Résumé de la simulation")

    col1, col2, col3, col4, col_dt = st.columns(5)
    col1.metric(
        "Période orbitale",
        f"{result.T_orb/60:.1f} min",
        help="Durée d'un tour complet autour de la Terre à cette altitude."
    )
    delta_payload_min = summary['Payload']['T_min_C'] - limits['payload']['min_C']
    col2.metric(
        "T_min Payload",
        f"{summary['Payload']['T_min_C']:.1f} °C",
        delta=f"{delta_payload_min:+.1f} K vs limite froide",
        delta_color="normal" if delta_payload_min > 10 else "inverse",
        help="Température minimale atteinte par la charge utile. Doit rester au-dessus de la limite basse."
    )
    delta_payload_max = limits['payload']['max_C'] - summary['Payload']['T_max_C']
    col3.metric(
        "T_max Payload",
        f"{summary['Payload']['T_max_C']:.1f} °C",
        delta=f"{delta_payload_max:+.1f} K marge chaude",
        delta_color="normal" if delta_payload_max > 10 else "inverse",
        help="Température maximale atteinte par la charge utile. Doit rester sous la limite haute."
    )
    col4.metric(
        "ΔT face +Y",
        f"{summary['+Y']['delta_T']:.1f} K",
        help="Amplitude thermique de la face +Y sur un cycle orbital. Une grande amplitude = contraintes mécaniques sur les matériaux."
    )
    col_dt.metric(
        "ΔT OBC/EPS",
        f"{summary['OBC/EPS']['delta_T']:.1f} K",
        help="Amplitude thermique de l'électronique. À minimiser pour la fiabilité des composants."
    )

    # Alerte globale
    margins = result.thermal_margins(limits)
    any_critical = any(margins[n]["margin_cold_K"] < 0 or margins[n]["margin_hot_K"] < 0 for n in NODE_NAMES)
    any_warning  = any((0 <= margins[n]["margin_cold_K"] < 10) or (0 <= margins[n]["margin_hot_K"] < 10) for n in NODE_NAMES)

    if any_critical:
        st.error("🔴 **Attention : un ou plusieurs composants dépassent leurs limites thermiques !** Modifiez les paramètres pour corriger le design.")
    elif any_warning:
        st.warning("🟡 **Marges thermiques faibles sur certains composants.** Le design est à la limite — à surveiller.")
    else:
        st.success("🟢 **Tous les composants sont dans leurs limites thermiques.** Le design est thermiquement valide.")

    st.divider()

    # ── Onglets principaux ───────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Graphiques",
        "🔬 Analyse détaillée",
        "📋 Tableau des marges",
        "🎓 Comprendre la physique",
        "🌍 Vue 3D animée",
    ])

    # ── Onglet 1 : Graphiques principaux ─────────────────────────────────────
    with tab1:
        show_orbital_explainer(altitude, beta, result.T_orb / 60)
        show_graph_reading_guide()

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**6 faces extérieures** — directement exposées au Soleil et au vide")
            st.plotly_chart(plot_face_temperatures(result, eclipse_periods, limits), width='stretch')
        with col_r:
            st.markdown("**Composants internes** — protégés des faces, mais réchauffés par conduction et dissipation électronique")
            st.plotly_chart(plot_internal_temperatures(result, eclipse_periods, limits), width='stretch')

        st.markdown("---")
        st.markdown("**Carte thermique globale** — vue synthétique de l'évolution de tous les nœuds")
        st.markdown("""
<div class="info-box">
🌡️ La couleur va du <strong>bleu (froid)</strong> au <strong>rouge (chaud)</strong>.
Lisez de gauche à droite pour suivre l'évolution dans le temps.
Les alternances soleil/éclipse créent des "vagues" horizontales répétitives.
</div>
""", unsafe_allow_html=True)
        st.plotly_chart(plot_heatmap(result), width='stretch')

    # ── Onglet 2 : Analyse détaillée ─────────────────────────────────────────
    with tab2:
        st.subheader("Marges thermiques par composant")
        st.markdown("""
<div class="info-box">
La <strong>marge thermique</strong> est l'écart entre la température extrême réellement atteinte
et la limite opérationnelle du composant. C'est <em>le</em> livrable central d'une analyse thermique spatiale.<br><br>
📐 <code>Marge froide = T_min_réelle − Limite_basse</code> &nbsp;&nbsp;
📐 <code>Marge chaude = Limite_haute − T_max_réelle</code><br><br>
Une marge <strong>négative</strong> signifie que le composant mourrait en orbite.
</div>
""", unsafe_allow_html=True)
        st.plotly_chart(plot_margins(result, config), width='stretch')

        st.subheader("Vue individuelle par nœud")
        st.caption("Chaque sous-graphique montre l'évolution de la température d'un seul nœud.")
        st.plotly_chart(plot_node_overview(result, eclipse_periods), width='stretch')

        st.subheader("Propriétés de surface choisies")
        show_coating_explainer(alpha_p, epsilon_p)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Matériaux de référence**")
            df_mat = pd.DataFrame({
                "Matériau":        ["Peinture blanche", "Peinture noire", "Aluminium nu", "Or (MLI extérieur)", "Panneau solaire"],
                "α (absorb. sol.)": [0.23, 0.95, 0.37, 0.25, 0.92],
                "ε (émissivité)":   [0.88, 0.88, 0.05, 0.04, 0.85],
            })
            df_mat["ε/α"] = (df_mat["ε (émissivité)"] / df_mat["α (absorb. sol.)"]).round(2)
            st.dataframe(df_mat, width='stretch', hide_index=True)
        with col_b:
            st.markdown("**Puissance interne**")
            show_power_explainer(p_obc, p_payload, p_radio)

    # ── Onglet 3 : Tableau des marges ─────────────────────────────────────────
    with tab3:
        st.subheader("Tableau complet des marges thermiques")
        st.caption("Calculé sur le régime établi (après les orbites de transitoire initiales).")
        df_margins = build_summary_df(result, config)

        # Mise en forme conditionnelle
        def highlight_margin(val):
            if isinstance(val, float):
                if val < 0:   return "background-color: #3d0000; color: #ff8888"
                if val < 10:  return "background-color: #3d2000; color: #ffc066"
                return "background-color: #003d1a; color: #66ffaa"
            return ""

        styled = df_margins.style.map(
            highlight_margin,
            subset=["Marge froide [K]", "Marge chaude [K]"]
        )
        st.dataframe(styled, width='stretch', hide_index=True)

        st.markdown("""
**Légende des couleurs** :
🟢 Vert → marge > 10 K — design robuste &nbsp;|&nbsp;
🟡 Orange → 0–10 K — surveiller &nbsp;|&nbsp;
🔴 Rouge → < 0 K — hors limites
        """)

        # Export
        csv = df_margins.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Télécharger le tableau (CSV)",
            data=csv,
            file_name="thermal_margins_cubesat.csv",
            mime="text/csv",
        )

    # ── Onglet 4 : Pédagogie ─────────────────────────────────────────────────
    with tab4:
        st.subheader("🎓 Comprendre la thermique spatiale")

        show_nodes_guide()
        show_glossary()

        st.markdown("---")
        st.markdown("### Le problème central : pourquoi la température est critique dans l'espace")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
<div class="warn-box">
<strong>🌡️ Un cycle thermique violent</strong><br><br>
Le satellite fait le tour de la Terre en ~96 min.
Il passe alternativement :<br>
• ~60 min au soleil : jusqu'à +70°C sur les faces exposées<br>
• ~36 min dans l'ombre : jusqu'à −50°C<br><br>
Soit <strong>±120°C en moins de 2 heures</strong>, des milliers de fois sur la durée de vie.
</div>
""", unsafe_allow_html=True)
        with col2:
            st.markdown("""
<div class="physics-box">
<strong>🚫 Pas de convection dans l'espace</strong><br><br>
Sur Terre, l'air transporte la chaleur (convection). Dans le vide spatial, il n'y a pas d'air.<br><br>
<strong>Seule façon de perdre de la chaleur</strong> : rayonnement infrarouge.<br>
<strong>Sources de chaleur</strong> : Soleil, albédo Terre, IR Terre, dissipation électronique.<br><br>
Pas de ventilateur possible. Pas de liquide de refroidissement (ou presque).
</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Les 3 flux thermiques entrants")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""
<div class="info-box">
<strong>☀️ Flux solaire direct</strong><br><br>
~1361 W/m² hors atmosphère.<br>
Reçu uniquement par les faces "regardant" le Soleil.<br>
Dépend de l'angle d'incidence (cos θ).<br>
Absent pendant les éclipses.
</div>
""", unsafe_allow_html=True)
        with c2:
            st.markdown("""
<div class="info-box">
<strong>🌍 Albédo terrestre</strong><br><br>
~30% du flux solaire réfléchi par la Terre.<br>
Affecte les faces pointées vers la Terre.<br>
Présent seulement quand la Terre est éclairée.<br>
Environ 10× moins intense que le solaire direct.
</div>
""", unsafe_allow_html=True)
        with c3:
            st.markdown("""
<div class="info-box">
<strong>🌡️ IR terrestre</strong><br><br>
~240 W/m² émis par la Terre à ~255 K.<br>
<strong>Permanent</strong> : présent même en éclipse.<br>
Affecte toutes les faces avec vue sur la Terre.<br>
Chauffe les faces inférieures du satellite.
</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Comment l'ingénieur contrôle les températures")
        st.markdown("""
<div class="success-box">
<strong>🔧 Les leviers du concepteur</strong><br><br>
1. <strong>Choix des revêtements (coatings)</strong> — modifier α et ε pour chaque face.<br>
   Exemple : peinture blanche (α=0.23, ε=0.88) sur les radiateurs pour maximiser le refroidissement.<br><br>
2. <strong>Orientation du satellite</strong> — quelle face regarde le Soleil ? La Terre ? Le vide froid ?<br><br>
3. <strong>Isolation thermique (MLI)</strong> — couvertures multi-couches dorées pour limiter les échanges.<br><br>
4. <strong>Connecteurs thermiques</strong> — spreaders en cuivre/aluminium pour distribuer la chaleur uniformément.<br><br>
5. <strong>Chauffages électriques</strong> — petites résistances pour éviter le gel des composants en éclipse.<br><br>
6. <strong>Réduction des dissipations</strong> — éteindre des composants quand ils ne sont pas nécessaires.
</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Le modèle mathématique en bref")
        st.markdown("""
Pour chaque nœud i, l'équation est :

```
mᵢ · cᵢ · dTᵢ/dt = Q_solaire,i + Q_albédo,i + Q_IR,i + Q_dissipé,i
                    − εᵢ · σ · Aᵢ · Tᵢ⁴
                    + Σⱼ Gᵢⱼ · (Tⱼ − Tᵢ)   ← conduction vers les nœuds voisins
```

Avec :
- **mᵢ · cᵢ** = masse × capacité thermique du nœud (inertie thermique)
- **Q_*** = flux de chaleur reçus (dépendent de la position orbitale)
- **εᵢ · σ · Aᵢ · Tᵢ⁴** = rayonnement émis vers l'espace (loi de Stefan-Boltzmann)
- **Gᵢⱼ** = conductance thermique entre nœuds adjacents

Ce système de **9 équations couplées et non-linéaires** (à cause de T⁴) est résolu numériquement
par la méthode **Runge-Kutta 4/5** (SciPy), pas à pas dans le temps.
        """)

    # ── Onglet 5 : Vue 3D animée ─────────────────────────────────────────────
    with tab5:
        st.markdown("""
<div class="info-box">
🎬 <strong>Visualisation 3D animée</strong><br><br>
La scène de <strong>gauche</strong> montre la trajectoire orbitale autour de la Terre.
Les portions <strong>jaunes</strong> sont en plein soleil, les portions <strong>sombres</strong> correspondent aux éclipses.<br>
La scène de <strong>droite</strong> montre le CubeSat 3U en vue éclatée : chaque face et chaque composant interne
change de couleur selon sa température simulée — du <span style="color:#7595d4"><strong>bleu froid</strong></span>
au <span style="color:#e87070"><strong>rouge chaud</strong></span>.<br><br>
▶ Cliquez sur <strong>Play</strong> pour lancer l'animation, ou glissez le curseur pour naviguer manuellement.
</div>
""", unsafe_allow_html=True)

        # Clé de cache basée sur les paramètres de simulation courants
        anim_key = (altitude, beta, n_orbits, alpha_p, epsilon_p, p_obc, p_payload, p_radio)

        if st.session_state.get("anim_key") != anim_key or "anim_fig" not in st.session_state:
            with st.spinner("🔄 Construction de la visualisation 3D (calcul des positions orbitales + frames d'animation)…"):
                fig_3d = build_3d_animation(result, config, N_frames=80)
                st.session_state["anim_fig"] = fig_3d
                st.session_state["anim_key"] = anim_key
        else:
            fig_3d = st.session_state["anim_fig"]

        st.plotly_chart(fig_3d, width="stretch")

        # Légende des couleurs
        col_leg1, col_leg2, col_leg3, col_leg4, col_leg5 = st.columns(5)
        col_leg1.markdown("<div style='background:rgb(49,54,149);border-radius:4px;padding:6px 10px;text-align:center;color:white;font-size:12px'>🥶 Très froid</div>", unsafe_allow_html=True)
        col_leg2.markdown("<div style='background:rgb(116,173,209);border-radius:4px;padding:6px 10px;text-align:center;color:#111;font-size:12px'>❄️ Froid</div>", unsafe_allow_html=True)
        col_leg3.markdown("<div style='background:rgb(255,255,191);border-radius:4px;padding:6px 10px;text-align:center;color:#333;font-size:12px'>🌡️ Moyen</div>", unsafe_allow_html=True)
        col_leg4.markdown("<div style='background:rgb(253,141,60);border-radius:4px;padding:6px 10px;text-align:center;color:#111;font-size:12px'>🔥 Chaud</div>", unsafe_allow_html=True)
        col_leg5.markdown("<div style='background:rgb(215,48,39);border-radius:4px;padding:6px 10px;text-align:center;color:white;font-size:12px'>🌋 Très chaud</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
**Comment lire la visualisation :**
- 💎 Le **diamant blanc** sur l'orbite = position actuelle du satellite
- Le diamant devient **grisé** lors des éclipses (absence de Soleil)
- La trajectoire **jaune** = satellite au soleil &nbsp;|&nbsp; **sombre** = éclipse
- Les faces **+X/−X/+Y/−Y** sont les faces latérales (portent les panneaux solaires)
- **+Z/−Z** sont les faces haut (zénith) et bas (nadir, pointé vers la Terre)
- 💻 **OBC/EPS**, 🔩 **Structure**, 📷 **Payload** = composants internes
        """)

    st.caption("Simulation thermique CubeSat 3U · Modèle nodal 9 nœuds · Runge-Kutta 4/5 · SciPy")


if __name__ == "__main__":
    main()