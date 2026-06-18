#!/usr/bin/env python3
"""
run_sensitivity.py — Lance l'analyse de sensibilité et génère les graphiques

Usage :
  python scripts/run_sensitivity.py
  python scripts/run_sensitivity.py --param beta
"""

import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import plotly.graph_objects as go
import plotly.io as pio

from src.sensitivity import run_sensitivity, sensitivity_plot_data
from src.thermal_model import NODE_NAMES

PARAMS = {
    "beta": {
        "values": [0, 15, 30, 45, 60, 75, 90],
        "label":  "Angle β [°]",
        "desc":   "Influence de l'angle beta orbital",
    },
    "alpha_panels": {
        "values": [0.10, 0.23, 0.37, 0.60, 0.80, 0.93],
        "label":  "Absorptivité α (faces)",
        "desc":   "Influence du coating (absorptivité solaire)",
    },
    "epsilon_panels": {
        "values": [0.10, 0.30, 0.50, 0.70, 0.85, 0.92],
        "label":  "Émissivité ε (faces)",
        "desc":   "Influence du coating (émissivité thermique)",
    },
    "power_payload": {
        "values": [0.5, 1.0, 2.0, 3.0, 4.0, 5.0],
        "label":  "Puissance payload [W]",
        "desc":   "Influence de la consommation de la caméra",
    },
}

def make_sensitivity_plot(results, param_info, node_name, limits):
    """Génère un graphique de sensibilité pour un paramètre et un nœud."""
    data = sensitivity_plot_data(results, node_name)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data["values"], y=data["T_max"],
        name="T_max", mode="lines+markers",
        line=dict(color="#E74C3C", width=2),
        marker=dict(size=8),
    ))
    fig.add_trace(go.Scatter(
        x=data["values"], y=data["T_min"],
        name="T_min", mode="lines+markers",
        line=dict(color="#3498DB", width=2, dash="dot"),
        marker=dict(size=8),
    ))

    # Zone de fonctionnement acceptable
    node_to_limit = {
        "+X": "panels",   "-X": "panels",
        "+Y": "panels",   "-Y": "panels",
        "+Z": "panels",   "-Z": "panels",
        "Structure": "structure",
        "OBC/EPS":   "obc_eps",
        "Payload":   "payload",
    }
    lim_key = node_to_limit[node_name]
    lim     = limits[lim_key]

    fig.add_hline(y=lim["max_C"], line=dict(color="red", dash="dash"),
                  annotation_text=f"Limite max {lim['max_C']}°C")
    fig.add_hline(y=lim["min_C"], line=dict(color="blue", dash="dash"),
                  annotation_text=f"Limite min {lim['min_C']}°C")

    fig.add_hrect(
        y0=lim["min_C"], y1=lim["max_C"],
        fillcolor="rgba(39,174,96,0.08)",
        line_width=0,
        annotation_text="Zone opérationnelle",
    )

    fig.update_layout(
        title       = f"Sensibilité {node_name} — {param_info['desc']}",
        xaxis_title = param_info["label"],
        yaxis_title = "Température [°C]",
        hovermode   = "x unified",
        height      = 450,
    )
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--param", default="beta", choices=list(PARAMS.keys()),
                        help="Paramètre à étudier")
    parser.add_argument("--node",  default="Payload",
                        help="Nœud à analyser")
    args = parser.parse_args()

    with open("config/cubesat_config.yaml") as f:
        config = yaml.safe_load(f)

    # Réduire les orbites pour accélérer la sensibilité
    config["simulation"]["n_orbits"] = 4
    config["simulation"]["n_points"] = 3000

    param_info = PARAMS[args.param]

    print(f"\n=== Analyse de sensibilité : {param_info['desc']} ===")
    print(f"Valeurs testées : {param_info['values']}")
    print()

    results = run_sensitivity(config, args.param, param_info["values"], verbose=True)

    print(f"\nGénération du graphique pour le nœud '{args.node}'...")
    fig = make_sensitivity_plot(results, param_info, args.node, config["thermal_limits"])

    out_path = f"results/sensitivity_{args.param}_{args.node.replace('/', '_')}.html"
    fig.write_html(out_path)
    print(f"Graphique sauvegardé : {out_path}")
    fig.show()


if __name__ == "__main__":
    main()
