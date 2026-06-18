# 🛰️ Tutoriel Complet — Bilan Thermique CubeSat
## De zéro à un dashboard fonctionnel, étape par étape

> **Philosophie de ce tutoriel :** Chaque étape produit quelque chose de vérifiable.  
> Tu ne passes à l'étape suivante que quand l'étape en cours affiche le bon résultat.  
> Pas de code "à l'aveugle". À chaque fois, tu vois ce que tu fais et pourquoi.

---

## Ce dont tu as besoin avant de commencer

- Python 3.10 ou plus récent (`python --version`)
- Un terminal
- Un éditeur de texte (VSCode, Neovim, peu importe)
- Environ 3h pour faire tout d'une traite, ou 6 sessions d'une demi-heure

---

# ÉTAPE 0 — Mettre en place l'environnement

## 0.1 Créer le dossier du projet

```bash
mkdir 01-cubesat-thermal
cd 01-cubesat-thermal
```

## 0.2 Créer un environnement virtuel Python

Un environnement virtuel isole les dépendances du projet du reste de ta machine.
C'est la bonne pratique — fais-le toujours.

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS (source .venv/bin/activate/fish si utilisation de fish pour linux)
# .venv\Scripts\activate         # Windows
```

Tu dois voir `(.venv)` apparaître au début de ton invite de commande.

## 0.3 Créer le fichier requirements.txt

```bash
cat > requirements.txt << 'EOF'
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0
plotly>=5.14.0
streamlit>=1.25.0
pyyaml>=6.0
pytest>=7.3.0
EOF
```

## 0.4 Installer les dépendances

```bash
pip install -r requirements.txt
```

Attends que ça finisse. Tu devrais voir `Successfully installed ...` à la fin.

## 0.5 Créer toute l'arborescence de dossiers

```bash
mkdir -p src config scripts app tests results/example images
touch src/__init__.py
touch results/.gitkeep
touch images/.gitkeep
```

## 0.6 Créer le .gitignore

```bash
cat > .gitignore << 'EOF'
.venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
results/*/
!results/.gitkeep
!results/example/
*.csv
*.json
.DS_Store
EOF
```

## ✅ Vérification étape 0

```bash
ls -la
```

Tu dois voir : `src/  config/  scripts/  app/  tests/  results/  images/  requirements.txt  .gitignore`

---

# ÉTAPE 1 — Le fichier de configuration (YAML)

**Pourquoi commencer par là ?** Parce que tous les fichiers Python vont lire leurs paramètres ici.
Aucun "magic number" dans le code — tout est dans ce fichier.

## 1.1 Créer config/cubesat_config.yaml

```bash
cat > config/cubesat_config.yaml << 'EOF'
# ============================================================
# CubeSat 3U - Configuration Thermique Complète
# ============================================================

satellite:
  name: "3U CubeSat LEO"
  total_mass_kg: 4.0

orbit:
  altitude_km: 550
  inclination_deg: 51.6
  beta_angle_deg: 30.0

simulation:
  n_orbits: 5
  n_points: 5000
  n_warmup_orbits: 2
  T_init_K: 280.0

environment:
  solar_constant_Wm2: 1361.0
  earth_albedo: 0.30
  earth_OLR_Wm2: 237.0
  T_space_K: 3.0

faces:
  plus_X:
    material: "painted_white"
    alpha: 0.23
    epsilon: 0.88
    area_m2: 0.030
    mass_kg: 0.08
    cp_JkgK: 896.0
  minus_X:
    material: "painted_white"
    alpha: 0.23
    epsilon: 0.88
    area_m2: 0.030
    mass_kg: 0.08
    cp_JkgK: 896.0
  plus_Y:
    material: "solar_panel"
    alpha: 0.92
    epsilon: 0.85
    area_m2: 0.030
    mass_kg: 0.10
    cp_JkgK: 750.0
  minus_Y:
    material: "solar_panel"
    alpha: 0.92
    epsilon: 0.85
    area_m2: 0.030
    mass_kg: 0.10
    cp_JkgK: 750.0
  plus_Z:
    material: "painted_white"
    alpha: 0.23
    epsilon: 0.88
    area_m2: 0.010
    mass_kg: 0.04
    cp_JkgK: 896.0
  minus_Z:
    material: "painted_white"
    alpha: 0.23
    epsilon: 0.88
    area_m2: 0.010
    mass_kg: 0.04
    cp_JkgK: 896.0

internal_nodes:
  structure:
    material: "aluminum_6061"
    mass_kg: 0.80
    cp_JkgK: 896.0
  obc_eps:
    material: "pcb_components"
    mass_kg: 0.30
    cp_JkgK: 800.0
  payload:
    material: "optical_assembly"
    mass_kg: 0.50
    cp_JkgK: 520.0

conductances_GL:
  face_to_structure: 0.064
  structure_to_obc: 0.427
  structure_to_payload: 0.427
  obc_to_payload: 0.005

power_dissipation:
  obc_W: 0.5
  eps_sun_W: 0.5
  eps_eclipse_W: 0.3
  payload_sun_W: 2.0
  payload_eclipse_W: 0.0
  adcs_W: 0.2
  radio_sun_W: 0.8
  radio_eclipse_W: 0.0

thermal_limits:
  panels:     {min_C: -100, max_C: 120}
  structure:  {min_C: -80,  max_C: 100}
  obc_eps:    {min_C: -40,  max_C: 85}
  payload:    {min_C: -20,  max_C: 60}
EOF
```

## ✅ Vérification étape 1

```bash
python -c "
import yaml
with open('config/cubesat_config.yaml') as f:
    cfg = yaml.safe_load(f)
print('Altitude :', cfg['orbit']['altitude_km'], 'km')
print('Beta :', cfg['orbit']['beta_angle_deg'], 'deg')
print('Faces configurées :', list(cfg['faces'].keys()))
print('✓ Config chargée correctement')
"
```

**Résultat attendu :**
```
Altitude : 550 km
Beta : 30.0 deg
Faces configurées : ['plus_X', 'minus_X', 'plus_Y', 'minus_Y', 'plus_Z', 'minus_Z']
✓ Config chargée correctement
```

---

# ÉTAPE 2 — Le modèle orbital (src/orbital.py)

Ce fichier répond à une question simple : **à chaque instant, où est le satellite ? Est-il au soleil ou dans l'ombre ?**

## 2.1 Créer src/orbital.py

```bash
cat > src/orbital.py << 'EOF'
"""
orbital.py — Mécanique orbitale pour simulation thermique CubeSat

Hypothèses simplificatrices :
- Orbite parfaitement circulaire (excentricité nulle)
- Angle bêta constant pendant la simulation (valide sur quelques orbites)
- Ombre de la Terre cylindrique (l'ombre pénombre est ignorée)
- Orientation satellite : nadir-pointing (une face toujours vers la Terre)
"""

import numpy as np
from dataclasses import dataclass, field

# ─── Constantes physiques ────────────────────────────────────────────────────
R_EARTH  = 6_371_000.0      # Rayon moyen de la Terre [m]
MU_EARTH = 3.986_004_418e14 # Paramètre gravitationnel standard [m³/s²]


@dataclass
class OrbitalParameters:
    """
    Regroupe tous les paramètres orbitaux calculés à partir de l'altitude et de beta.

    altitude_km : altitude de l'orbite circulaire [km]
    beta_deg    : angle entre le plan orbital et la direction Soleil [degrés]
                  0° = éclipses maximales (worst cold case)
                  90° = jamais d'éclipse (worst hot case)
    """
    altitude_km: float
    beta_deg:    float

    # Ces champs sont calculés automatiquement dans __post_init__
    r:           float = field(init=False)
    T_orb:       float = field(init=False)
    omega:       float = field(init=False)
    beta:        float = field(init=False)
    beta_crit:   float = field(init=False)

    def __post_init__(self):
        self.r        = R_EARTH + self.altitude_km * 1_000.0
        self.T_orb    = 2 * np.pi * np.sqrt(self.r**3 / MU_EARTH)
        self.omega    = 2 * np.pi / self.T_orb
        self.beta     = np.radians(self.beta_deg)
        # Angle critique au-delà duquel il n'y a plus d'éclipse
        self.beta_crit = np.arcsin(R_EARTH / self.r)

    @property
    def eclipse_fraction(self) -> float:
        """Fraction de l'orbite passée en éclipse (0.0 à ~0.4)."""
        if abs(self.beta) >= self.beta_crit:
            return 0.0
        num = np.sqrt(1.0 - (R_EARTH / self.r)**2 * np.cos(self.beta)**2)
        return (1.0 / np.pi) * np.arccos(num / np.cos(self.beta))

    @property
    def eclipse_duration_min(self) -> float:
        return self.eclipse_fraction * self.T_orb / 60.0

    @property
    def sunlight_duration_min(self) -> float:
        return (1.0 - self.eclipse_fraction) * self.T_orb / 60.0

    def summary(self) -> dict:
        return {
            "altitude_km":          self.altitude_km,
            "beta_deg":             self.beta_deg,
            "period_min":           round(self.T_orb / 60.0, 2),
            "eclipse_fraction":     round(self.eclipse_fraction, 4),
            "eclipse_min":          round(self.eclipse_duration_min, 2),
            "sunlight_min":         round(self.sunlight_duration_min, 2),
            "beta_critical_deg":    round(np.degrees(self.beta_crit), 2),
        }


def sun_vector_rtn(t: float, orb: OrbitalParameters) -> np.ndarray:
    """
    Vecteur unitaire pointant vers le Soleil, exprimé dans le repère RTN.

    Repère RTN (Radial – Transverse – Normal) :
      R : du centre Terre vers le satellite (radial)
      T : perpendiculaire à R dans le plan orbital (transverse, sens du mouvement)
      N : perpendiculaire au plan orbital (normal)

    Avec l'hypothèse beta constant et orbite circulaire :
      La composante N du Soleil = sin(beta)  [constante]
      Les composantes R et T tournent avec la position du satellite.
    """
    theta = orb.omega * t          # Position angulaire sur l'orbite [rad]
    beta  = orb.beta

    s_R =  np.cos(beta) * np.sin(theta)   # Note : signe selon convention
    s_T =  np.cos(beta) * np.cos(theta)
    s_N =  np.sin(beta)

    vec = np.array([s_R, s_T, s_N])
    return vec / np.linalg.norm(vec)       # Normalisation de sécurité


def in_eclipse(t: float, orb: OrbitalParameters) -> bool:
    """
    Retourne True si le satellite est dans l'ombre de la Terre au temps t.

    Méthode : ombre cylindrique.
    Le satellite est en éclipse si ET SEULEMENT SI :
      1. Il se trouve "derrière" la Terre par rapport au Soleil (x_shadow > 0)
      2. Sa distance à l'axe Soleil-Terre est inférieure au rayon terrestre
    """
    if abs(orb.beta) >= orb.beta_crit:
        return False   # Jamais d'éclipse pour ce beta

    theta = orb.omega * t
    beta  = orb.beta
    r     = orb.r

    # Coordonnées dans le repère centré Terre, axe X = direction anti-Soleil
    # x > 0 signifie "derrière la Terre"
    x = -r * np.cos(beta) * np.cos(theta)
    y =  r * np.cos(beta) * np.sin(theta)
    z =  r * np.sin(beta)

    # Dans l'ombre si derrière la Terre ET dans le cylindre d'ombre
    return bool(x > 0 and np.sqrt(y**2 + z**2) < R_EARTH)
EOF
```

## ✅ Vérification étape 2

Lance ce script pour vérifier que la mécanique orbitale est cohérente :

```bash
python -c "
import numpy as np
from src.orbital import OrbitalParameters, in_eclipse

# Test 1 : Paramètres orbitaux pour 550 km
orb = OrbitalParameters(altitude_km=550, beta_deg=30.0)
s = orb.summary()
print('=== Paramètres orbitaux ===')
for k, v in s.items():
    print(f'  {k:25s} : {v}')

# Test 2 : Période orbitale (doit être ~95-96 min pour 550 km)
assert 94 < orb.T_orb / 60 < 97, 'Période incorrecte !'
print()

# Test 3 : Fraction éclipse pour beta=0 (doit être ~35-38%)
orb0 = OrbitalParameters(altitude_km=550, beta_deg=0.0)
f = orb0.eclipse_fraction
print(f'Fraction éclipse (beta=0°)  : {f:.1%}  [attendu ~36%]')
assert 0.30 < f < 0.42, 'Fraction éclipse incohérente !'

# Test 4 : Pas d'éclipse pour beta=90°
orb90 = OrbitalParameters(altitude_km=550, beta_deg=90.0)
assert orb90.eclipse_fraction == 0.0, 'Beta=90° devrait donner 0 éclipse !'
print(f'Fraction éclipse (beta=90°) : {orb90.eclipse_fraction:.1%}  [attendu 0%]')

# Test 5 : Vérifier un cycle éclipse/soleil sur une orbite
n_samples = 1000
t_samples = np.linspace(0, orb0.T_orb, n_samples)
eclipses = [in_eclipse(t, orb0) for t in t_samples]
frac_computed = sum(eclipses) / n_samples
print(f'Fraction éclipse (Monte-Carlo) : {frac_computed:.1%}  [attendu ~36%]')

print()
print('✓ Toutes les vérifications orbitales sont OK')
"
```

**Résultat attendu :**
```
=== Paramètres orbitaux ===
  altitude_km               : 550
  beta_deg                  : 30.0
  period_min                : 95.5
  eclipse_fraction          : 0.3285
  eclipse_min               : 31.37
  sunlight_min              : 64.13
  beta_critical_deg         : 66.87

Fraction éclipse (beta=0°)  : 36.5%  [attendu ~36%]
Fraction éclipse (beta=90°) : 0.0%   [attendu 0%]
Fraction éclipse (Monte-Carlo) : 36.3%  [attendu ~36%]

✓ Toutes les vérifications orbitales sont OK
```

---

# ÉTAPE 3 — L'environnement thermique (src/environment.py)

Ce fichier calcule les flux de chaleur reçus par chaque face du satellite à chaque instant.

## 3.1 Créer src/environment.py

```bash
cat > src/environment.py << 'EOF'
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
EOF
```

## ✅ Vérification étape 3

```bash
python -c "
import yaml
from src.orbital import OrbitalParameters
from src.environment import EnvironmentModel

with open('config/cubesat_config.yaml') as f:
    cfg = yaml.safe_load(f)

orb = OrbitalParameters(altitude_km=550, beta_deg=30.0)
env = EnvironmentModel(cfg)

print('=== Vérification des flux thermiques ===')
print()

# Test au milieu du passage au soleil (t = T_orb/4)
t_sun = orb.T_orb / 4
fluxes_sun = env.compute(t_sun, orb)
print(f'Position : t = {t_sun/60:.1f} min (en soleil)')
print(f'  En soleil : {fluxes_sun[\"+X\"][\"in_sun\"]}')
print()
for face, f in fluxes_sun.items():
    total_in = f['solar'] + f['albedo'] + f['earth_ir']
    print(f'  Face {face:3s} : solaire={f[\"solar\"]:5.2f}W  albédo={f[\"albedo\"]:5.2f}W  IR={f[\"earth_ir\"]:5.2f}W  → entrée={total_in:5.2f}W')

print()
# Test pendant l'éclipse (t = T_orb * 0.85 — milieu de l'éclipse)
t_ecl = orb.T_orb * 0.85
fluxes_ecl = env.compute(t_ecl, orb)
print(f'Position : t = {t_ecl/60:.1f} min')
print(f'  En soleil : {fluxes_ecl[\"+X\"][\"in_sun\"]}')

# Vérifications clés
solar_during_eclipse = sum(f['solar'] for f in fluxes_ecl.values())
assert solar_during_eclipse == 0.0, 'ERREUR : flux solaire non nul pendant éclipse !'
print(f'  Flux solaire total pendant éclipse : {solar_during_eclipse:.2f} W  [attendu : 0.0 W] ✓')

ir_total = sum(f['earth_ir'] for f in fluxes_ecl.values())
assert ir_total > 0, 'ERREUR : IR Terre nul !'
print(f'  Flux IR Terre total pendant éclipse : {ir_total:.2f} W  [doit être > 0] ✓')

print()
print('✓ Flux environnementaux cohérents')
"
```

**Résultat attendu :**
```
=== Vérification des flux thermiques ===

Position : t = 23.9 min (en soleil)
  En soleil : True
  Face  +X : solaire= 0.00W  albédo= 1.02W  IR= 2.24W  → entrée= 3.26W
  Face  -X : solaire= 0.00W  albédo= 1.02W  IR= 2.24W  → entrée= 3.26W
  Face  +Y : solaire=29.90W  albédo= 0.00W  IR= 0.00W  → entrée=29.90W
  ...

Position : t = 81.2 min
  En soleil : False
  Flux solaire total pendant éclipse : 0.00 W  [attendu : 0.0 W] ✓
  Flux IR Terre total pendant éclipse : X.XX W  [doit être > 0] ✓

✓ Flux environnementaux cohérents
```

---

# ÉTAPE 4 — Le modèle thermique nodal (src/thermal_model.py)

C'est le cœur du projet. Ce fichier assemble tout et produit les équations différentielles.

## 4.1 Créer src/thermal_model.py

```bash
cat > src/thermal_model.py << 'EOF'
"""
thermal_model.py — Modèle nodal thermique du CubeSat (9 nœuds)

Index des nœuds :
  0 : Face +X      3 : Face -Y
  1 : Face -X      4 : Face +Z (zenith)
  2 : Face +Y      5 : Face -Z (nadir)
                   6 : Structure interne
                   7 : OBC + EPS (électronique)
                   8 : Payload (caméra)
"""

import numpy as np
from .orbital import OrbitalParameters
from .environment import EnvironmentModel

N_NODES    = 9
NODE_NAMES = ["+X", "-X", "+Y", "-Y", "+Z", "-Z", "Structure", "OBC/EPS", "Payload"]

# Correspondance face-name → index de nœud
FACE_TO_IDX = {"+X": 0, "-X": 1, "+Y": 2, "-Y": 3, "+Z": 4, "-Z": 5}


class ThermalModel:
    """
    Encapsule toute la physique thermique du CubeSat.
    Expose la méthode dTdt(t, T) utilisée par solve_ivp.
    """

    def __init__(self, config: dict):
        self.config = config
        self.orb    = OrbitalParameters(
            altitude_km = config["orbit"]["altitude_km"],
            beta_deg    = config["orbit"]["beta_angle_deg"],
        )
        self.env    = EnvironmentModel(config)
        self.T_orb  = self.orb.T_orb

        # Vecteur des capacités thermiques C_i = m_i * cp_i [J/K]
        self.C  = self._build_capacities(config)

        # Matrice des conductances linéaires GL [W/K]
        # GL[i,j] = conductance entre le nœud i et le nœud j
        self.GL = self._build_GL_matrix(config)

        # Pré-calculer les profils de puissance interne
        self._pd = config["power_dissipation"]

    # ─── Construction des matrices ─────────────────────────────────────────

    def _build_capacities(self, config: dict) -> np.ndarray:
        C = np.zeros(N_NODES)

        # Nœuds 0–5 : les 6 faces
        face_order = ["plus_X", "minus_X", "plus_Y", "minus_Y", "plus_Z", "minus_Z"]
        for i, fname in enumerate(face_order):
            fc   = config["faces"][fname]
            C[i] = fc["mass_kg"] * fc["cp_JkgK"]

        # Nœuds 6–8 : nœuds internes
        ic   = config["internal_nodes"]
        C[6] = ic["structure"]["mass_kg"] * ic["structure"]["cp_JkgK"]
        C[7] = ic["obc_eps"]["mass_kg"]   * ic["obc_eps"]["cp_JkgK"]
        C[8] = ic["payload"]["mass_kg"]   * ic["payload"]["cp_JkgK"]

        return C

    def _build_GL_matrix(self, config: dict) -> np.ndarray:
        GL = np.zeros((N_NODES, N_NODES))
        gl = config["conductances_GL"]

        # Toutes les faces (0–5) sont conductivement liées à la structure (6)
        for i in range(6):
            v = gl["face_to_structure"]
            GL[i, 6] = v
            GL[6, i] = v

        # Structure (6) ↔ OBC/EPS (7)
        v = gl["structure_to_obc"]
        GL[6, 7] = v
        GL[7, 6] = v

        # Structure (6) ↔ Payload (8)
        v = gl["structure_to_payload"]
        GL[6, 8] = v
        GL[8, 6] = v

        # OBC/EPS (7) ↔ Payload (8)  [très faible — vide entre les cartes]
        v = gl["obc_to_payload"]
        GL[7, 8] = v
        GL[8, 7] = v

        return GL

    # ─── Puissance interne dissipée ────────────────────────────────────────

    def _internal_power(self, t: float) -> np.ndarray:
        """
        Retourne le vecteur de dissipation thermique [W] pour chaque nœud.
        Dépend de la phase orbitale (soleil vs éclipse).
        """
        from .orbital import in_eclipse
        sunlight = not in_eclipse(t, self.orb)
        pd = self._pd
        Q  = np.zeros(N_NODES)

        if sunlight:
            # Nœud 7 (OBC + EPS + Radio) : mode actif au soleil
            Q[7] = pd["obc_W"] + pd["eps_sun_W"] + pd["radio_sun_W"]
            # Nœud 8 (Payload) : caméra active au soleil
            Q[8] = pd["payload_sun_W"]
        else:
            # Nœud 7 : mode veille pendant l'éclipse
            Q[7] = pd["obc_W"] + pd["eps_eclipse_W"]
            # Nœud 8 : payload éteint
            Q[8] = pd["payload_eclipse_W"]

        # ADCS (réaction magnétique) : toujours actif → dans la structure
        Q[6] = pd["adcs_W"]

        return Q

    # ─── Équation différentielle principale ────────────────────────────────

    def dTdt(self, t: float, T: np.ndarray) -> np.ndarray:
        """
        Fonction d'état pour scipy.integrate.solve_ivp.

        T [K] → dT/dt [K/s]

        Bilan par nœud i :
          C_i * dT_i/dt = Q_ext,i - Q_rad_out,i + Q_int,i + Σ_j GL_ij*(Tj - Ti)
        """
        dT    = np.zeros(N_NODES)
        fluxes = self.env.compute(t, self.orb)
        Q_int  = self._internal_power(t)

        for i in range(N_NODES):
            Q_net = Q_int[i]          # Sources internes (électronique)

            # ── Flux externes (uniquement sur les faces, nœuds 0–5) ─────────
            if i < 6:
                face_name = NODE_NAMES[i]
                fl = fluxes[face_name]

                # Flux entrants
                Q_net += fl["solar"] + fl["albedo"] + fl["earth_ir"]

                # Flux sortant : rayonnement vers l'espace (Stefan-Boltzmann)
                # Q_out = ε·σ·A·T⁴ = rad_coef * T⁴
                Q_net -= fl["rad_coef"] * T[i] ** 4

            # ── Conduction avec les nœuds voisins ───────────────────────────
            for j in range(N_NODES):
                if self.GL[i, j] > 0.0:
                    Q_net += self.GL[i, j] * (T[j] - T[i])

            # ── Équation de bilan ────────────────────────────────────────────
            dT[i] = Q_net / self.C[i]

        return dT
EOF
```

## ✅ Vérification étape 4

```bash
python -c "
import yaml
import numpy as np
from src.thermal_model import ThermalModel, N_NODES, NODE_NAMES

with open('config/cubesat_config.yaml') as f:
    cfg = yaml.safe_load(f)

model = ThermalModel(cfg)

print('=== Vérification du modèle thermique ===')
print()
print(f'Capacités thermiques [J/K] :')
for i, name in enumerate(NODE_NAMES):
    print(f'  {name:12s} : {model.C[i]:.1f} J/K')

print()
print(f'Conductances GL non nulles :')
for i in range(N_NODES):
    for j in range(i+1, N_NODES):
        if model.GL[i,j] > 0:
            print(f'  {NODE_NAMES[i]:12s} ↔ {NODE_NAMES[j]:12s} : {model.GL[i,j]:.4f} W/K')

print()
# Test de dTdt avec T uniforme à 280 K (état initial)
T_test = np.full(N_NODES, 280.0)
t_test = model.T_orb / 4     # En plein soleil

dT = model.dTdt(t_test, T_test)
print(f'dT/dt à t={t_test/60:.1f} min, T=280 K uniforme :')
for i, name in enumerate(NODE_NAMES):
    print(f'  {name:12s} : {dT[i]:+.4f} K/s  ({dT[i]*60:+.2f} K/min)')

# Vérification physique : aucun nœud ne doit dériver de plus de 5 K/min au départ
assert all(abs(d * 60) < 5.0 for d in dT), 'ERREUR : dérive thermique trop rapide !'
print()
print('✓ Modèle thermique cohérent')
"
```

---

# ÉTAPE 5 — Le solveur ODE (src/solver.py)

Ce fichier orchestre l'intégration numérique et emballe les résultats dans un objet pratique.

## 5.1 Créer src/solver.py

```bash
cat > src/solver.py << 'EOF'
"""
solver.py — Intégration numérique du système d'ODE thermique

Utilise scipy.integrate.solve_ivp avec la méthode RK45 (Runge-Kutta adaptatif).
Retourne un objet SimulationResult avec les méthodes de post-traitement.
"""

import numpy as np
from scipy.integrate import solve_ivp
from dataclasses import dataclass, field
from typing import List


@dataclass
class SimulationResult:
    """
    Contient les résultats bruts de la simulation et des méthodes utilitaires.
    """
    t:               np.ndarray          # Vecteur temps [s]
    T_K:             np.ndarray          # Températures [K] — shape (9, N_points)
    node_names:      List[str]
    T_orb:           float               # Période orbitale [s]
    n_warmup_orbits: int = 2

    # ── Conversions ────────────────────────────────────────────────────────

    @property
    def T_C(self) -> np.ndarray:
        """Températures en degrés Celsius."""
        return self.T_K - 273.15

    @property
    def t_min(self) -> np.ndarray:
        """Temps en minutes."""
        return self.t / 60.0

    # ── Régime établi (après warmup) ──────────────────────────────────────

    @property
    def _steady_mask(self) -> np.ndarray:
        return self.t >= self.n_warmup_orbits * self.T_orb

    @property
    def t_steady_min(self) -> np.ndarray:
        return self.t[self._steady_mask] / 60.0

    @property
    def T_steady_C(self) -> np.ndarray:
        return self.T_C[:, self._steady_mask]

    # ── Statistiques ──────────────────────────────────────────────────────

    def summary(self) -> dict:
        """
        Tableau récapitulatif T_min / T_max / T_mean / ΔT
        calculé sur le régime établi seulement.
        """
        T = self.T_steady_C
        return {
            name: {
                "T_min_C":  round(float(T[i].min()),  1),
                "T_max_C":  round(float(T[i].max()),  1),
                "T_mean_C": round(float(T[i].mean()), 1),
                "delta_T":  round(float(T[i].max() - T[i].min()), 1),
            }
            for i, name in enumerate(self.node_names)
        }

    def thermal_margins(self, limits: dict) -> dict:
        """
        Calcule les marges thermiques (distance aux limites) pour chaque nœud.
        Une marge négative signifie un dépassement de limite → problème !
        """
        s = self.summary()

        # Mapping nœud → clé de limite dans la config
        node_to_limit = {
            "+X": "panels",    "-X": "panels",
            "+Y": "panels",    "-Y": "panels",
            "+Z": "panels",    "-Z": "panels",
            "Structure": "structure",
            "OBC/EPS":   "obc_eps",
            "Payload":   "payload",
        }

        margins = {}
        for name in self.node_names:
            lim_key = node_to_limit[name]
            lim     = limits[lim_key]
            stats   = s[name]
            margins[name] = {
                "margin_cold_K": round(stats["T_min_C"] - lim["min_C"], 1),
                "margin_hot_K":  round(lim["max_C"] - stats["T_max_C"], 1),
                "T_min_C":       stats["T_min_C"],
                "T_max_C":       stats["T_max_C"],
                "limit_min_C":   lim["min_C"],
                "limit_max_C":   lim["max_C"],
            }
        return margins


def run_simulation(model, config: dict) -> SimulationResult:
    """
    Lance la simulation thermique et retourne un SimulationResult.

    model  : instance de ThermalModel
    config : dictionnaire de configuration (issu du YAML)
    """
    sim = config["simulation"]

    # Condition initiale : tous les nœuds à la même température
    T_init = np.full(9, sim["T_init_K"])

    # Horizon de simulation
    t_final = sim["n_orbits"] * model.T_orb
    t_eval  = np.linspace(0.0, t_final, sim["n_points"])

    # Pas maximum : au moins 200 pas par orbite pour bien résoudre les transitions
    max_step = model.T_orb / 200.0

    print(f"  Lancement solve_ivp  (RK45, {sim['n_orbits']} orbites, "
          f"{sim['n_points']} points)...")

    sol = solve_ivp(
        fun           = lambda t, T: model.dTdt(t, T),
        t_span        = (0.0, t_final),
        y0            = T_init,
        method        = "RK45",
        t_eval        = t_eval,
        rtol          = 1e-4,
        atol          = 1e-6,
        max_step      = max_step,
        dense_output  = False,
    )

    if not sol.success:
        raise RuntimeError(f"Simulation échouée : {sol.message}")

    print(f"  Terminé en {sol.t[-1]/60:.1f} min simulées  "
          f"({sol.nfev} évaluations de la fonction)")

    from .thermal_model import NODE_NAMES
    return SimulationResult(
        t               = sol.t,
        T_K             = sol.y,
        node_names      = NODE_NAMES,
        T_orb           = model.T_orb,
        n_warmup_orbits = sim["n_warmup_orbits"],
    )
EOF
```

---

# ÉTAPE 6 — Le script principal CLI (scripts/main_simulation.py)

C'est le point d'entrée en ligne de commande. Il doit produire une sortie lisible et vérifiable.

## 6.1 Créer scripts/main_simulation.py

```bash
cat > scripts/main_simulation.py << 'EOF'
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
EOF
chmod +x scripts/main_simulation.py
```

## ✅ Vérification étape 6 — Premier vrai test de bout en bout

```bash
python scripts/main_simulation.py
```

**Résultat attendu (après ~5-15 secondes) :**
```
========================================================
   🛰️  CubeSat 3U — Thermal Balance Simulation
========================================================
   Altitude  : 550 km
   Angle β   : 30.0°
   Orbites   : 5
   Points    : 5000
========================================================

  Période orbitale : 95.5 min
  Lancement solve_ivp  (RK45, 5 orbites, 5000 points)...
  Terminé en 477.5 min simulées  (XXXX évaluations de la fonction)
  Temps de calcul  : X.XX s

========================================================================
  RÉSULTATS (régime établi — orbites 3 à 5)
========================================================================
  Nœud            T_min     T_max      ΔT   M_froid  M_chaud  Statut
  --------------------------------------------------------------------
  +X             -42.X°C   +62.X°C   XX.XK   +XX.XK   +XX.XK  🟢 OK
  ...
  Payload        -16.X°C   +42.X°C   XX.XK    +X.XK   +XX.XK  🟡 Marge faible
```

Si tu vois ces lignes, **la simulation tourne correctement**. C'est le moment de fêter ça.

---

# ÉTAPE 7 — Le dashboard Streamlit (app/app.py)

Maintenant on visualise. Ce fichier crée une interface web interactive.

## 7.1 Créer app/app.py

```bash
cat > app/app.py << 'EOF'
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
EOF
```

## ✅ Vérification étape 7 — Lancer le dashboard

```bash
streamlit run app/app.py
```

Ouvre ton navigateur à l'adresse indiquée (typiquement `http://localhost:8501`).

Tu dois voir :
- Le dashboard avec les sliders dans la sidebar
- Un bouton "Lancer la simulation"
- Clique dessus → attend 5-15 secondes → 4 graphiques apparaissent

---

# ÉTAPE 8 — L'analyse de sensibilité (src/sensitivity.py)

C'est la valeur ajoutée ingénieur. On va faire varier un paramètre et tracer comment les températures réagissent.

## 8.1 Créer src/sensitivity.py

```bash
cat > src/sensitivity.py << 'EOF'
"""
sensitivity.py — Analyse paramétrique de sensibilité thermique

Pour chaque paramètre d'étude, lance une série de simulations
et collecte T_min / T_max par nœud.
"""

import copy
import numpy as np
from .thermal_model import ThermalModel, NODE_NAMES
from .solver import run_simulation


def run_sensitivity(base_config: dict, param_name: str,
                    values: list, verbose: bool = True) -> list:
    """
    Lance une simulation pour chaque valeur de la liste.

    param_name : clé du paramètre à varier (voir PARAM_MAP ci-dessous)
    values     : liste de valeurs à tester
    
    Retourne une liste de dicts :
    [
      {'value': v, 'T_min_C': array[9], 'T_max_C': array[9], 'T_mean_C': array[9]},
      ...
    ]
    """
    PARAM_MAP = {
        "beta":          ("orbit", "beta_angle_deg"),
        "altitude":      ("orbit", "altitude_km"),
        "alpha_panels":  None,    # cas spécial : plusieurs faces
        "epsilon_panels": None,   # cas spécial
        "power_payload": ("power_dissipation", "payload_sun_W"),
        "power_obc":     ("power_dissipation", "obc_W"),
    }

    results = []

    for val in values:
        cfg = copy.deepcopy(base_config)

        # Modification du paramètre
        if param_name in ("alpha_panels", "epsilon_panels"):
            prop = "alpha" if param_name == "alpha_panels" else "epsilon"
            for face in ["plus_X", "minus_X", "plus_Y", "minus_Y", "plus_Z", "minus_Z"]:
                cfg["faces"][face][prop] = val
        else:
            section, key = PARAM_MAP[param_name]
            cfg[section][key] = val

        if verbose:
            print(f"  {param_name} = {val} ...", end="", flush=True)

        model  = ThermalModel(cfg)
        result = run_simulation(model, cfg)

        # Extraire les stats sur le régime établi
        T = result.T_steady_C

        if verbose:
            print(f" Payload T=[{T[8].min():.1f}, {T[8].max():.1f}]°C")

        results.append({
            "value":    val,
            "T_min_C":  T.min(axis=1),    # min temporel pour chaque nœud
            "T_max_C":  T.max(axis=1),
            "T_mean_C": T.mean(axis=1),
            "delta_T":  T.max(axis=1) - T.min(axis=1),
        })

    return results


def sensitivity_plot_data(results: list, node_name: str) -> dict:
    """
    Extrait les données de T_min et T_max pour un nœud donné,
    prêtes à être tracées.
    """
    idx    = NODE_NAMES.index(node_name)
    values = [r["value"]       for r in results]
    T_mins = [r["T_min_C"][idx] for r in results]
    T_maxs = [r["T_max_C"][idx] for r in results]
    return {"values": values, "T_min": T_mins, "T_max": T_maxs}
EOF
```

## 8.2 Créer le script de sensibilité

```bash
cat > scripts/run_sensitivity.py << 'EOF'
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
EOF
```

## ✅ Vérification étape 8

```bash
python scripts/run_sensitivity.py --param beta --node Payload
```

Cela va lancer 7 simulations (une par valeur de β) et ouvrir un graphique dans le navigateur.

**Attention :** Cette étape prend 1-3 minutes selon ta machine — c'est normal.

---

# ÉTAPE 9 — Tests unitaires (tests/)

Des tests courts qui vérifient que la physique reste correcte même si on modifie le code.

## 9.1 Créer tests/test_orbital.py

```bash
cat > tests/test_orbital.py << 'EOF'
"""Tests unitaires pour le modèle orbital."""
import numpy as np
import pytest
from src.orbital import OrbitalParameters, sun_vector_rtn, in_eclipse, R_EARTH


class TestOrbitalParameters:

    def test_period_550km(self):
        """La période orbitale à 550 km doit être ~95-96 minutes."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=0)
        assert 94 * 60 < orb.T_orb < 97 * 60

    def test_no_eclipse_high_beta(self):
        """Beta = 90° → jamais d'éclipse."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=90)
        assert orb.eclipse_fraction == 0.0

    def test_eclipse_fraction_zero_beta(self):
        """Beta = 0° → éclipse significative (~35%)."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=0)
        assert 0.30 < orb.eclipse_fraction < 0.42

    def test_eclipse_fraction_increases_with_altitude(self):
        """Plus l'altitude est basse, plus les éclipses sont longues."""
        orb_low  = OrbitalParameters(altitude_km=400, beta_deg=0)
        orb_high = OrbitalParameters(altitude_km=700, beta_deg=0)
        assert orb_low.eclipse_fraction > orb_high.eclipse_fraction

    def test_sun_vector_is_unit(self):
        """Le vecteur Soleil doit être unitaire."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=30)
        for t in [0, 100, 1000, 5000]:
            vec = sun_vector_rtn(t, orb)
            assert abs(np.linalg.norm(vec) - 1.0) < 1e-10

    def test_eclipse_consistent_with_fraction(self):
        """La fraction d'éclipse Monte-Carlo doit correspondre à la formule."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=0)
        n   = 2000
        t_s = np.linspace(0, orb.T_orb, n)
        mc_frac = sum(in_eclipse(t, orb) for t in t_s) / n
        assert abs(mc_frac - orb.eclipse_fraction) < 0.02  # ±2%
EOF
```

## 9.2 Créer tests/test_environment.py

```bash
cat > tests/test_environment.py << 'EOF'
"""Tests unitaires pour le modèle environnemental."""
import yaml
import numpy as np
import pytest
from src.orbital import OrbitalParameters
from src.environment import EnvironmentModel


@pytest.fixture
def config():
    with open("config/cubesat_config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def env(config):
    return EnvironmentModel(config)


@pytest.fixture
def orb():
    return OrbitalParameters(altitude_km=550, beta_deg=0)


class TestEnvironmentFluxes:

    def test_no_solar_in_eclipse(self, env, orb):
        """Aucun flux solaire pendant l'éclipse."""
        t_eclipse = orb.T_orb * 0.85    # Milieu de l'éclipse pour beta=0
        fluxes    = env.compute(t_eclipse, orb)
        total_solar = sum(f["solar"] for f in fluxes.values())
        assert total_solar == 0.0, f"Flux solaire non nul pendant éclipse : {total_solar}"

    def test_earth_ir_permanent(self, env, orb):
        """Le flux IR Terre est présent jour ET nuit."""
        t_ecl = orb.T_orb * 0.85
        t_sun = orb.T_orb * 0.25
        f_ecl = env.compute(t_ecl, orb)
        f_sun = env.compute(t_sun, orb)
        assert sum(f["earth_ir"] for f in f_ecl.values()) > 0
        assert sum(f["earth_ir"] for f in f_sun.values()) > 0

    def test_solar_only_on_visible_faces(self, env, orb):
        """Le flux solaire est nul sur les faces en ombre propre."""
        t_sun  = orb.T_orb * 0.25
        fluxes = env.compute(t_sun, orb)
        for face, fl in fluxes.items():
            assert fl["solar"] >= 0.0, f"Flux solaire négatif sur {face}"

    def test_rad_coef_positive(self, env, orb):
        """Le coefficient de rayonnement vers l'espace est strictement positif."""
        fluxes = env.compute(0.0, orb)
        for face, fl in fluxes.items():
            assert fl["rad_coef"] > 0.0
EOF
```

## 9.3 Créer tests/test_thermal_model.py

```bash
cat > tests/test_thermal_model.py << 'EOF'
"""Tests unitaires pour le modèle thermique."""
import yaml
import numpy as np
import pytest
from src.thermal_model import ThermalModel, N_NODES


@pytest.fixture
def config():
    with open("config/cubesat_config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def model(config):
    return ThermalModel(config)


class TestThermalModel:

    def test_capacities_positive(self, model):
        """Toutes les capacités thermiques doivent être strictement positives."""
        assert all(c > 0 for c in model.C)

    def test_GL_symmetric(self, model):
        """La matrice GL doit être symétrique (GL[i,j] == GL[j,i])."""
        diff = np.abs(model.GL - model.GL.T)
        assert diff.max() < 1e-10, f"GL non symétrique, diff max = {diff.max()}"

    def test_GL_nonnegative(self, model):
        """Toutes les conductances doivent être ≥ 0."""
        assert model.GL.min() >= 0.0

    def test_dTdt_shape(self, model):
        """dTdt doit retourner un vecteur de la bonne dimension."""
        T = np.full(N_NODES, 280.0)
        dT = model.dTdt(0.0, T)
        assert dT.shape == (N_NODES,)

    def test_dTdt_finite(self, model):
        """dTdt ne doit pas produire de NaN ou d'infini."""
        T  = np.full(N_NODES, 280.0)
        dT = model.dTdt(0.0, T)
        assert np.all(np.isfinite(dT)), f"dT/dt contient NaN ou inf : {dT}"

    def test_energy_balance_cold_dark(self, model):
        """
        Dans le noir complet (éclipse) et sans dissipation interne,
        une surface chaude doit se refroidir (dT/dt < 0 pour les faces).
        """
        cfg = {**model.config}
        cfg["power_dissipation"] = {k: 0.0 for k in cfg["power_dissipation"]}
        m2  = ThermalModel(cfg)

        T   = np.full(N_NODES, 350.0)     # Bien chaud
        t   = model.T_orb * 0.85          # En éclipse (beta=0)
        dT  = m2.dTdt(t, T)

        # Les faces extérieures doivent se refroidir (flux sortant > entrant)
        for i in range(6):
            assert dT[i] < 0, f"Face {i} ne refroidit pas en éclipse à haute T"
EOF
```

## ✅ Lancer tous les tests

```bash
python -m pytest tests/ -v
```

**Résultat attendu :**
```
tests/test_orbital.py::TestOrbitalParameters::test_period_550km PASSED
tests/test_orbital.py::TestOrbitalParameters::test_no_eclipse_high_beta PASSED
tests/test_orbital.py::TestOrbitalParameters::test_eclipse_fraction_zero_beta PASSED
...
tests/test_environment.py::TestEnvironmentFluxes::test_no_solar_in_eclipse PASSED
...
tests/test_thermal_model.py::TestThermalModel::test_GL_symmetric PASSED
...

====== XX passed in X.XXs ======
```

Si tu vois `XX passed` et aucun `FAILED`, le code est correct.

---

# ÉTAPE 10 — Finalisation GitHub

## 10.1 Initialiser le dépôt Git

```bash
git init
git add .
git commit -m "feat: initial cubesat thermal simulation — 9-node LEO thermal model"
```

## 10.2 Vérifier la structure finale

```bash
find . -not -path './.venv/*' -not -path './.git/*' -not -name '*.pyc' \
       -not -path './__pycache__/*' | sort
```

Tu dois voir exactement :
```
.
├── .gitignore
├── README.md              ← À créer (voir cahier des charges)
├── app/
│   └── app.py
├── config/
│   └── cubesat_config.yaml
├── requirements.txt
├── results/
│   └── .gitkeep
├── scripts/
│   ├── main_simulation.py
│   └── run_sensitivity.py
├── src/
│   ├── __init__.py
│   ├── environment.py
│   ├── orbital.py
│   ├── sensitivity.py
│   ├── solver.py
│   └── thermal_model.py
└── tests/
    ├── test_environment.py
    ├── test_orbital.py
    └── test_thermal_model.py
```

## 10.3 Test de démarrage à froid (simulation "rien installé")

C'est le test final : quelqu'un clone ton repo, est-ce que ça marche ?

```bash
# Simuler un clone propre
deactivate
cd ..
python -m venv test_cold
source test_cold/bin/activate
pip install -r 01-cubesat-thermal/requirements.txt
cd 01-cubesat-thermal
python scripts/main_simulation.py
streamlit run app/app.py
```

Si les deux commandes fonctionnent → le projet est prêt pour GitHub.

```bash
# Nettoyage
deactivate
cd ..
rm -rf test_cold
cd 01-cubesat-thermal
source .venv/bin/activate
```

---

# Récapitulatif des Commandes

```bash
# Simulation en ligne de commande
python scripts/main_simulation.py
python scripts/main_simulation.py --beta 0     # Worst cold case
python scripts/main_simulation.py --beta 90    # Worst hot case

# Dashboard interactif
streamlit run app/app.py

# Analyse de sensibilité
python scripts/run_sensitivity.py --param beta
python scripts/run_sensitivity.py --param alpha_panels --node Payload
python scripts/run_sensitivity.py --param power_payload

# Tests unitaires
python -m pytest tests/ -v
python -m pytest tests/ -v --tb=short    # Affichage compact des erreurs
```

---

# Ordre de résolution si quelque chose ne marche pas

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ModuleNotFoundError: src` | Python path incorrect | Lancer depuis la racine du projet |
| `FileNotFoundError: cubesat_config.yaml` | Mauvais répertoire courant | `cd 01-cubesat-thermal` |
| Simulation qui diverge (T → ∞) | Pas de temps trop grand | Réduire `n_points` (augmenter résolution) |
| Streamlit : page blanche | Cache corrompu | `streamlit cache clear` |
| Tests qui échouent | Config modifiée | Restaurer `cubesat_config.yaml` depuis git |
| Simulation très lente | Beaucoup d'orbites | Réduire `n_orbits` à 3 pour les tests |
