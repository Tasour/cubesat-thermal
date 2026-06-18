"""
environment.py — Flux thermiques environnementaux sur les faces du CubeSat

Pour chaque face et chaque instant t, calcule :
  - Flux solaire direct absorbé       [W]
  - Flux albédo Terre absorbé         [W]
  - Flux infrarouge Terre absorbé     [W]
  - Coefficient de rayonnement sortant [W/K⁴]  (utilisé par thermal_model)
"""

import numpy as np
from .orbital import OrbitalParameters, sun_vector_rtn, in_eclipse

SIGMA   = 5.670_374_4e-8   # Constante de Stefan-Boltzmann [W/(m²·K⁴)]
R_EARTH = 6_371_000.0       # Rayon terrestre [m]

# ─── Vecteurs normaux des 6 faces en repère RTN ──────────────────────────────
# Orientation satellite : nadir-pointing (face -Z toujours vers la Terre)
#
# Repère RTN : R = radial (vers l'espace), T = transverse, N = normal orbital
# La face -Z regarde vers le nadir (-R), la face +Z regarde le zenith (+R)
# Les faces ±X et ±Y sont les faces latérales longues (10×30 cm)

FACE_NORMALS_RTN = {
    "+X": np.array([ 0.0,  1.0,  0.0]),   # Latérale, direction de vol
    "-X": np.array([ 0.0, -1.0,  0.0]),   # Latérale, arrière
    "+Y": np.array([ 0.0,  0.0,  1.0]),   # Latérale, normale orbitale
    "-Y": np.array([ 0.0,  0.0, -1.0]),   # Latérale, normale orbitale opposée
    "+Z": np.array([ 1.0,  0.0,  0.0]),   # Zenith (vers l'espace)
    "-Z": np.array([-1.0,  0.0,  0.0]),   # Nadir (vers la Terre)
}

# Vecteur nadir (direction de la Terre depuis le satellite) en RTN
NADIR_RTN = np.array([-1.0, 0.0, 0.0])


def view_factor_earth(altitude_km: float) -> float:
    """
    Facteur de vue géométrique d'une surface plane vers la Terre.

    Formule pour une sphère à distance r du centre :
    F = 0.5 * (1 - sqrt(1 - (R_Earth/r)²))

    Pour h=550 km : F ≈ 0.32 — environ 32% de l'hémisphère est occupé par la Terre.
    """
    r = R_EARTH + altitude_km * 1_000.0
    return 0.5 * (1.0 - np.sqrt(1.0 - (R_EARTH / r) ** 2))


class EnvironmentModel:
    """
    Calcule tous les flux thermiques externes sur les 6 faces du CubeSat.
    Les résultats sont retournés dans un dict indexé par le nom de la face.
    """

    def __init__(self, config: dict):
        env = config["environment"]
        self.S0      = env["solar_constant_Wm2"]
        self.a_E     = env["earth_albedo"]
        self.OLR     = env["earth_OLR_Wm2"]
        self.T_space = env["T_space_K"]
        self.alt     = config["orbit"]["altitude_km"]
        self.F_earth = view_factor_earth(self.alt)

        # Propriétés thermo-optiques et aires par face (lues depuis config)
        # Mapping entre les clés YAML ('plus_X') et les clés internes ('+X')
        yaml_to_key = {
            "plus_X": "+X", "minus_X": "-X",
            "plus_Y": "+Y", "minus_Y": "-Y",
            "plus_Z": "+Z", "minus_Z": "-Z",
        }
        self.face_props = {
            yaml_to_key[k]: {
                "alpha":   v["alpha"],
                "epsilon": v["epsilon"],
                "area":    v["area_m2"],
            }
            for k, v in config["faces"].items()
        }

    def compute(self, t: float, orb: OrbitalParameters) -> dict:
        """
        Calcule les flux [W] et le coefficient radiatif pour chaque face au temps t.

        Retourne un dict de la forme :
        {
          '+X': {
            'solar':    float [W],
            'albedo':   float [W],
            'earth_ir': float [W],
            'rad_coef': float [W/K⁴],   # Q_out = rad_coef * T^4
            'in_sun':   bool,
          },
          ...
        }
        """
        sun_vec  = sun_vector_rtn(t, orb)
        sunlight = not in_eclipse(t, orb)

        result = {}
        for face, normal in FACE_NORMALS_RTN.items():
            p   = self.face_props[face]
            alp = p["alpha"]
            eps = p["epsilon"]
            A   = p["area"]

            # Angle d'incidence : cos(θ) entre la normale de face et le vecteur Soleil
            cos_sun   = float(np.dot(normal, sun_vec))
            cos_sun   = max(0.0, cos_sun)     # Négatif → face dans l'ombre propre

            # Angle d'incidence vers la Terre (nadir)
            cos_nadir = float(np.dot(normal, -NADIR_RTN))
            cos_nadir = max(0.0, cos_nadir)   # Seules les faces "regardant" la Terre

            # ── Flux solaire direct ──────────────────────────────────────────
            # Nul si éclipse OU si la face regarde dans la mauvaise direction
            Q_solar = alp * self.S0 * A * cos_sun * (1.0 if sunlight else 0.0)

            # ── Flux albédo ──────────────────────────────────────────────────
            # La Terre réfléchit a_E * S0 vers le satellite
            # Nul si éclipse (Terre dans l'ombre du Soleil = pas d'albédo)
            Q_albedo = (alp * self.a_E * self.S0 * A
                        * self.F_earth * cos_nadir
                        * (1.0 if sunlight else 0.0))

            # ── Flux IR Terre ────────────────────────────────────────────────
            # Permanent (jour ET nuit) : la Terre émet son propre rayonnement
            Q_earth_ir = eps * self.OLR * A * self.F_earth * cos_nadir

            # ── Coefficient de rayonnement vers l'espace ─────────────────────
            # Q_out = rad_coef * T^4   (avec T en Kelvin)
            # On soustrait la contribution de l'espace (3 K) mais c'est négligeable
            rad_coef = eps * SIGMA * A

            result[face] = {
                "solar":    Q_solar,
                "albedo":   Q_albedo,
                "earth_ir": Q_earth_ir,
                "rad_coef": rad_coef,
                "in_sun":   sunlight,
            }

        return result
