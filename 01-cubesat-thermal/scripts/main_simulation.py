#!/usr/bin/env python3
"""
main_simulation.py — Point d'entrée CLI pour la simulation thermique CubeSat

Usage :
  python scripts/main_simulation.py
  python scripts/main_simulation.py --config config/cubesat_config.yaml
  python scripts/main_simulation.py --beta 60
"""

import sys
import argparse
import time
from pathlib import Path

import yaml
import numpy as np

# Ajoute la racine du projet au path Python
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.thermal_model import ThermalModel, NODE_NAMES
from src.solver import run_simulation


def parse_args():
    p = argparse.ArgumentParser(description="CubeSat Thermal Simulation")
    p.add_argument("--config", default="config/cubesat_config.yaml",
                   help="Chemin vers le fichier de configuration YAML")
    p.add_argument("--beta",   type=float, default=None,
                   help="Surcharge l'angle beta [degrés]")
    p.add_argument("--alt",    type=float, default=None,
                   help="Surcharge l'altitude [km]")
    p.add_argument("--orbits", type=int,   default=None,
                   help="Nombre d'orbites à simuler")
    return p.parse_args()


def print_header(config, args):
    orb = config["orbit"]
    sim = config["simulation"]
    print()
    print("=" * 56)
    print("   🛰️  CubeSat 3U — Thermal Balance Simulation")
    print("=" * 56)
    print(f"   Altitude  : {orb['altitude_km']} km")
    print(f"   Angle β   : {orb['beta_angle_deg']}°")
    print(f"   Orbites   : {sim['n_orbits']}")
    print(f"   Points    : {sim['n_points']}")
    print("=" * 56)


def print_orbital_info(result):
    from src.orbital import OrbitalParameters
    orb = OrbitalParameters(
        altitude_km = result.T_orb / 60 * 0,   # dummy — on recalcule
        beta_deg    = 0,
    )
    T_orb_min = result.T_orb / 60.0
    print()
    print("  Paramètres orbitaux :")
    print(f"    Période orbitale : {T_orb_min:.1f} min")


def print_summary(result, config):
    summary = result.summary()
    limits  = config["thermal_limits"]
    margins = result.thermal_margins(limits)

    print()
    print("=" * 72)
    print("  RÉSULTATS (régime établi — orbites 3 à 5)")
    print("=" * 72)
    print(f"  {'Nœud':<14}  {'T_min':>8}  {'T_max':>8}  {'ΔT':>7}  "
          f"{'M_froid':>8}  {'M_chaud':>8}  Statut")
    print("  " + "-" * 68)

    for name in NODE_NAMES:
        s  = summary[name]
        m  = margins[name]
        mc = m["margin_cold_K"]
        mh = m["margin_hot_K"]

        if mc < 0 or mh < 0:
            status = "🔴 HORS LIMITES"
        elif mc < 10 or mh < 10:
            status = "🟡 Marge faible"
        else:
            status = "🟢 OK"

        print(f"  {name:<14}  {s['T_min_C']:>7.1f}°C  {s['T_max_C']:>7.1f}°C  "
              f"{s['delta_T']:>6.1f}K  {mc:>+7.1f}K  {mh:>+7.1f}K  {status}")

    print("=" * 72)
    print()


def save_results(result, config):
    import pandas as pd
    import json

    run_dir = Path("results") / f"run_alt{int(config['orbit']['altitude_km'])}_b{int(config['orbit']['beta_angle_deg'])}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Températures complètes
    df = pd.DataFrame(
        result.T_C.T,
        columns=result.node_names
    )
    df.insert(0, "t_s", result.t)
    df.insert(1, "t_min", result.t_min)
    df.to_csv(run_dir / "temperatures.csv", index=False, float_format="%.3f")

    # Résumé JSON
    summary = result.summary()
    with open(run_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"  Résultats sauvegardés dans : {run_dir}/")
    return run_dir


def main():
    args = parse_args()

    # Chargement de la config
    with open(args.config) as f:
        config = yaml.safe_load(f)

    # Surcharges CLI
    if args.beta   is not None: config["orbit"]["beta_angle_deg"]  = args.beta
    if args.alt    is not None: config["orbit"]["altitude_km"]     = args.alt
    if args.orbits is not None: config["simulation"]["n_orbits"]   = args.orbits

    print_header(config, args)

    # Modèle et simulation
    model = ThermalModel(config)
    print(f"\n  Période orbitale : {model.T_orb/60:.1f} min")

    t_start = time.time()
    result  = run_simulation(model, config)
    elapsed = time.time() - t_start
    print(f"  Temps de calcul  : {elapsed:.2f} s")

    # Affichage et sauvegarde
    print_summary(result, config)
    save_results(result, config)


if __name__ == "__main__":
    main()
