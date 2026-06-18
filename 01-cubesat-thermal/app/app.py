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

    col1, col2, col3, col4, col5 = st.columns(5)
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
    col5.metric(
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
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Graphiques",
        "🔬 Analyse détaillée",
        "📋 Tableau des marges",
        "🎓 Comprendre la physique",
    ])

    # ── Onglet 1 : Graphiques principaux ─────────────────────────────────────
    with tab1:
        show_orbital_explainer(altitude, beta, result.T_orb / 60)
        show_graph_reading_guide()

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**6 faces extérieures** — directement exposées au Soleil et au vide")
            st.plotly_chart(plot_face_temperatures(result, eclipse_periods, limits), use_container_width=True)
        with col_r:
            st.markdown("**Composants internes** — protégés des faces, mais réchauffés par conduction et dissipation électronique")
            st.plotly_chart(plot_internal_temperatures(result, eclipse_periods, limits), use_container_width=True)

        st.markdown("---")
        st.markdown("**Carte thermique globale** — vue synthétique de l'évolution de tous les nœuds")
        st.markdown("""
<div class="info-box">
🌡️ La couleur va du <strong>bleu (froid)</strong> au <strong>rouge (chaud)</strong>.
Lisez de gauche à droite pour suivre l'évolution dans le temps.
Les alternances soleil/éclipse créent des "vagues" horizontales répétitives.
</div>
""", unsafe_allow_html=True)
        st.plotly_chart(plot_heatmap(result), use_container_width=True)

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
        st.plotly_chart(plot_margins(result, config), use_container_width=True)

        st.subheader("Vue individuelle par nœud")
        st.caption("Chaque sous-graphique montre l'évolution de la température d'un seul nœud.")
        st.plotly_chart(plot_node_overview(result, eclipse_periods), use_container_width=True)

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
            st.dataframe(df_mat, use_container_width=True, hide_index=True)
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

        styled = df_margins.style.applymap(
            highlight_margin,
            subset=["Marge froide [K]", "Marge chaude [K]"]
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

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

    st.caption("Simulation thermique CubeSat 3U · Modèle nodal 9 nœuds · Runge-Kutta 4/5 · SciPy")


if __name__ == "__main__":
    main()