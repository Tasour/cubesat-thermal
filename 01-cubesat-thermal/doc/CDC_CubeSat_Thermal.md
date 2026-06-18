# Cahier des Charges Détaillé
# Projet 01 — Bilan Thermique 3U CubeSat (LEO)
# Transposition Nucléaire → Spatial

**Version :** 1.0  
**Auteur :** [Ton Nom]  
**Date :** Juin 2026  
**Durée estimée :** 3–4 semaines (soir/week-end)

---

## Table des Matières

1. [Contexte & Positionnement Portfolio](#1-contexte--positionnement-portfolio)
2. [Architecture du Projet](#2-architecture-du-projet)
3. [Théorie Physique Complète](#3-théorie-physique-complète)
4. [Modèle Nodal — Conception Détaillée](#4-modèle-nodal--conception-détaillée)
5. [Modèle Orbital](#5-modèle-orbital)
6. [Environnement Thermique Spatial](#6-environnement-thermique-spatial)
7. [Couplages Thermiques Internes](#7-couplages-thermiques-internes)
8. [Intégration Numérique ODE](#8-intégration-numérique-ode)
9. [Dashboard Streamlit](#9-dashboard-streamlit)
10. [Analyse de Sensibilité](#10-analyse-de-sensibilité)
11. [Structure du Code — Recette Fichier par Fichier](#11-structure-du-code--recette-fichier-par-fichier)
12. [Données d'Entrée & Paramètres](#12-données-dentrée--paramètres)
13. [Livrables & Sorties Attendues](#13-livrables--sorties-attendues)
14. [Plan d'Exécution Phase par Phase](#14-plan-dexécution-phase-par-phase)
15. [README GitHub](#15-readme-github)

---

## 1. Contexte & Positionnement Portfolio

### 1.1 Pont Métier : EPR2 → Spatial

Ce projet n'est pas un exercice académique générique. C'est une **transposition directe et documentée** de méthodes industrielles :

| Compétence EPR2 (Edvance) | Équivalent CubeSat (ce projet) |
|---|---|
| Extraction de données 3DX → Python | Extraction de l'environnement orbital → Python |
| Bilan thermique ventilation/chauffage | Bilan thermique rayonnement/conduction spatial |
| Modèle nodal de bâtiment | Modèle nodal de satellite (nœuds = composants) |
| Analyse de sensibilité coefficients | Analyse de sensibilité coatings / puissance / β |
| Scripts d'automatisation industriels | Pipeline simulation → dashboard automatisé |
| Livrables ingénieur (fiches de calcul) | Rapport PDF + dashboard interactif |

### 1.2 Valeur Ajoutée Démontrée

Ce projet prouve **trois choses simultanément** à un recruteur spatial :

1. **Physique** : Maîtrise des environnements thermiques extrêmes (vide, cycles Eclipse/Sunlight)
2. **Méthode** : Approche ingénieur structurée (hypothèses claires, vérification dimensionnelle, cas limites)
3. **Outil** : Python scientifique professionnel (SciPy, Plotly, Streamlit, YAML config)

### 1.3 Périmètre

- **Objet simulé :** CubeSat 3U standard (10 × 10 × 30 cm, ~4 kg)
- **Orbite :** LEO circulaire, altitude 550 km, inclinaison 51.6° (ISS-like)
- **Durée simulée :** 3 orbites complètes (~270 minutes)
- **Modèle :** Lumped Parameter (nodal) — 9 nœuds thermiques
- **Out of scope :** FMEA thermique, rayonnement ionisant, propriétés thermo-mécaniques

---

## 2. Architecture du Projet

### 2.1 Arborescence Complète

```
01-cubesat-thermal/
│
├── README.md                        # Documentation principale GitHub
├── requirements.txt                 # Dépendances Python exactes avec versions
├── .gitignore
│
├── config/
│   └── cubesat_config.yaml          # TOUS les paramètres (zéro magic numbers dans le code)
│
├── src/
│   ├── __init__.py
│   ├── geometry.py                  # Géométrie 3U, faces, vecteurs normaux
│   ├── materials.py                 # Base de données matériaux (α, ε, k, ρ, Cp)
│   ├── orbital.py                   # Mécanique orbitale simplifiée (Kepler)
│   ├── environment.py               # Flux solaire, albédo, IR Terre, éclipses
│   ├── thermal_model.py             # Équations ODE, matrice de conductances
│   ├── solver.py                    # Intégration scipy.integrate.solve_ivp
│   └── sensitivity.py              # Analyse de sensibilité paramétrique
│
├── app/
│   └── app.py                       # Dashboard Streamlit interactif
│
├── scripts/
│   ├── main_simulation.py           # Point d'entrée CLI (sans Streamlit)
│   └── generate_report.py          # Export PDF du rapport de synthèse
│
├── notebooks/
│   └── 01_physics_validation.ipynb  # Vérification des équations step by step
│
├── tests/
│   ├── test_orbital.py
│   ├── test_environment.py
│   └── test_thermal_model.py
│
├── results/                         # Gitignored sauf exemples
│   ├── .gitkeep
│   └── example_run/
│       ├── temperatures.csv
│       └── summary.json
│
└── images/                          # Captures pour README
    ├── architecture_nodale.png
    ├── dashboard_screenshot.png
    └── temperatures_orbit.png
```

### 2.2 Flux de Données

```
cubesat_config.yaml
       │
       ▼
orbital.py  ──────────────────────────────────────────────────────┐
  │  (position satellite, vecteur soleil, flag éclipse)           │
  ▼                                                               │
environment.py                                                     │
  │  (Q_sol[t], Q_alb[t], Q_IR[t] pour chaque face)              │
  ▼                                                               │
thermal_model.py  ◄──── materials.py                              │
  │  (système d'ODE, matrice GL, GR)     geometry.py ────────────┘
  ▼
solver.py
  │  (solve_ivp → T_nodes[t] pour t in [0, t_final])
  ▼
sensitivity.py (optionnel)
  │  (boucle sur paramètres → T_min/T_max par nœud)
  ▼
app.py / generate_report.py
     (visualisation & export)
```

---

## 3. Théorie Physique Complète

### 3.1 Équation Fondamentale du Bilan Thermique Nodal

Pour chaque nœud thermique *i* :

$$m_i \cdot c_{p,i} \cdot \frac{dT_i}{dt} = \dot{Q}_{solaire,i} + \dot{Q}_{albédo,i} + \dot{Q}_{IR,i} + \dot{Q}_{interne,i} - \dot{Q}_{rayonné,i} + \sum_{j \neq i} \dot{Q}_{cond,ij} + \sum_{j \neq i} \dot{Q}_{rad,ij}$$

**Signification physique de chaque terme :**

| Terme | Unité | Description |
|---|---|---|
| $m_i \cdot c_{p,i} \cdot dT_i/dt$ | W | Variation d'énergie interne du nœud |
| $\dot{Q}_{solaire,i}$ | W | Flux solaire direct absorbé |
| $\dot{Q}_{albédo,i}$ | W | Flux solaire réfléchi par la Terre absorbé |
| $\dot{Q}_{IR,i}$ | W | Rayonnement infrarouge terrestre absorbé |
| $\dot{Q}_{interne,i}$ | W | Dissipation électronique interne |
| $\dot{Q}_{rayonné,i}$ | W | Flux émis vers l'espace (pertes) |
| $\sum \dot{Q}_{cond,ij}$ | W | Flux conductif avec nœuds voisins |
| $\sum \dot{Q}_{rad,ij}$ | W | Flux radiatif interne entre nœuds |

**Note clé (différence EPR2 ↔ Spatial) :** En bâtiment nucléaire, la convection est dominante. Dans l'espace, il n'y a PAS de convection (vide). Seuls la conduction (structures internes) et le rayonnement (surfaces externes vers le vide) opèrent.

### 3.2 Propriétés Thermo-Optiques

Chaque surface est caractérisée par deux propriétés adimensionnelles :

- **α (absorptivité solaire)** : fraction du flux solaire (courte longueur d'onde, ~0.3–2 µm) absorbée
- **ε (émissivité thermique)** : efficacité d'émission du rayonnement propre (grande longueur d'onde, ~8–12 µm)

**Loi de Kirchhoff :** Pour les grandes longueurs d'onde, ε = α_IR ≠ α_solaire  
**Pourquoi c'est important :** On peut choisir des coatings qui absorbent peu (α faible) mais émettent bien (ε élevé) → surface froide. Ou l'inverse.

#### Table de Référence Matériaux Spatiaux

| Matériau / Coating | α solaire | ε thermique | Usage typique |
|---|---|---|---|
| Aluminium nu (6061) | 0.37 | 0.05 | Structure (mauvais émetteur !) |
| Aluminium anodisé noir | 0.93 | 0.85 | Face chauffée intentionnellement |
| Peinture blanche (MAP-PU) | 0.23 | 0.88 | Radiateur passif standard |
| Multilayer Insulation (MLI) | 0.05 | 0.02 | Isolation thermique premium |
| Panneaux solaires (GaAs) | 0.92 | 0.85 | Face exposée au soleil |
| Kapton doré | 0.30 | 0.67 | Enveloppe thermique courante |
| OSR (Optical Solar Reflector) | 0.08 | 0.80 | Radiateur haute performance |

### 3.3 Loi de Stefan-Boltzmann

$$\dot{Q}_{rayonné} = \varepsilon \cdot \sigma \cdot A \cdot T^4$$

Avec :
- σ = 5.67 × 10⁻⁸ W/(m²·K⁴) — constante de Stefan-Boltzmann
- T en **Kelvin** (TOUJOURS — erreur classique de débutant)
- A = aire de la surface [m²]

**Vérification ordre de grandeur :** Une face de 10×10 cm (A = 0.01 m²), ε = 0.85, T = 300 K :  
Q = 0.85 × 5.67e-8 × 0.01 × 300⁴ ≈ **1.3 W** — raisonnable pour un CubeSat

### 3.4 Rayonnement à l'Équilibre Thermique (Temperature d'équilibre sans source interne)

En régime permanent et sans dissipation interne :

$$\alpha \cdot S \cdot A_{projetée} = \varepsilon \cdot \sigma \cdot A_{totale} \cdot T_{éq}^4$$

$$T_{éq} = \left( \frac{\alpha \cdot S}{4 \cdot \varepsilon \cdot \sigma} \right)^{1/4}$$

Le facteur 4 vient du ratio sphère : A_projetée / A_totale = 1/4.

**Application numérique :** Pour α = 0.3, ε = 0.85, S = 1361 W/m² :  
T_éq = (0.3 × 1361 / (4 × 0.85 × 5.67e-8))^0.25 ≈ **220 K = −53°C**

C'est la température d'équilibre d'un corps sphérique passif — point de départ pour valider le modèle.

---

## 4. Modèle Nodal — Conception Détaillée

### 4.1 Définition des 9 Nœuds

Un CubeSat 3U est modélisé par **9 nœuds thermiques** :

```
         +Z (top, face soleil selon orientation)
          │
    ┌─────┴─────┐
    │           │   ← Face +Y
-X──┤  STRUCT   ├──+X
    │  (nœud 7) │   ← Face -Y
    └─────┬─────┘
          │
         -Z (bottom)

Nœuds externes (faces du CubeSat) :
  N1 : Face +X  (10×30 cm = 0.030 m²)
  N2 : Face -X  (10×30 cm = 0.030 m²)
  N3 : Face +Y  (10×30 cm = 0.030 m²)
  N4 : Face -Y  (10×30 cm = 0.030 m²)
  N5 : Face +Z  (10×10 cm = 0.010 m²)  ← "top"
  N6 : Face -Z  (10×10 cm = 0.010 m²)  ← "bottom"

Nœuds internes :
  N7 : Structure (châssis aluminium, masse ~0.8 kg)
  N8 : OBC + EPS (carte électronique principale, ~0.3 kg)
  N9 : Payload / Caméra (composant le plus sensible, ~0.5 kg)
```

### 4.2 Masses et Capacités Thermiques

$$C_i = m_i \cdot c_{p,i}$$

| Nœud | Matériau | Masse (kg) | cp (J/kg·K) | Capacité (J/K) |
|---|---|---|---|---|
| N1–N6 (panneaux) | Alu 6061 (1 mm) | 0.08 chacun | 896 | 71.7 |
| N7 (structure) | Alu 6061 (rails) | 0.80 | 896 | 716 |
| N8 (OBC+EPS) | PCB FR4 + composants | 0.30 | 800 | 240 |
| N9 (payload) | Titane + optique | 0.50 | 520 | 260 |

**Total CubeSat :** ~4 kg — cohérent avec les standards 3U (≤ 4 kg)

### 4.3 Représentation Matricielle du Système

Le système de 9 ODE couplées s'écrit :

$$\mathbf{C} \cdot \dot{\mathbf{T}} = \mathbf{Q}_{ext}(t, \mathbf{T}) + \mathbf{G}_L \cdot \mathbf{T} - \mathbf{G}_L \cdot \mathbf{T} + \mathbf{Q}_{rad,int}(\mathbf{T})$$

En notation compacte pour `solve_ivp` :

```python
def dTdt(t, T, model):
    """
    T : vecteur état [T1, T2, ..., T9] en Kelvin
    Retourne dT/dt [K/s] pour chaque nœud
    """
    dT = np.zeros(9)
    for i in range(9):
        Q_ext = model.external_fluxes(t, T, i)    # Solaire + Albédo + IR + Interne
        Q_rad_out = model.radiation_to_space(T, i) # Émission vers l'espace
        Q_cond = model.conduction_fluxes(T, i)     # Σ GL_ij * (Tj - Ti)
        Q_rad_int = model.internal_radiation(T, i) # Σ GR_ij * (Tj⁴ - Ti⁴)
        
        dT[i] = (Q_ext - Q_rad_out + Q_cond + Q_rad_int) / model.C[i]
    
    return dT
```

---

## 5. Modèle Orbital

### 5.1 Paramètres Orbitaux d'Entrée

```yaml
# Dans cubesat_config.yaml
orbit:
  altitude_km: 550          # Altitude de l'orbite circulaire
  inclination_deg: 51.6     # Inclinaison (ISS-like)
  beta_angle_deg: 30.0      # Angle β (angle soleil/plan orbital) — paramètre clé
  raan_deg: 0.0             # Right Ascension Ascending Node (initialisation)
```

### 5.2 Calcul des Paramètres Dérivés

```python
# Dans orbital.py

R_EARTH = 6371e3           # m
MU_EARTH = 3.986e14        # m³/s² — paramètre gravitationnel standard

def compute_orbital_parameters(altitude_km):
    r = R_EARTH + altitude_km * 1e3    # Rayon orbital [m]
    T_orb = 2 * np.pi * np.sqrt(r**3 / MU_EARTH)  # Période [s]
    v_orb = np.sqrt(MU_EARTH / r)                  # Vitesse [m/s]
    omega = 2 * np.pi / T_orb                      # Vitesse angulaire [rad/s]
    return r, T_orb, v_orb, omega
```

**Vérification :** Pour 550 km → T_orb ≈ 5765 s ≈ 96 minutes ✓

### 5.3 Angle Bêta (β) — Concept Clé

L'angle β est l'angle entre le vecteur Soleil et le plan orbital. C'est **LE paramètre** qui gouverne le régime thermique :

```
β = 0°  → Satellite passe au-dessus et en-dessous du terminateur
           → Éclipses maximales (~36 min sur 96 min)
           → Cas thermique FROID (worst cold case)

β = 90° → Satellite toujours illuminé (orbite polaire en plein été)
           → Aucune éclipse
           → Cas thermique CHAUD (worst hot case)

β_crit  → Angle limite au-delà duquel il n'y a plus d'éclipse
         β_crit = arcsin(R_Earth / (R_Earth + altitude))
         Pour 550 km : β_crit = arcsin(6371/6921) ≈ 66.8°
```

### 5.4 Fraction d'Éclipse

La fraction de l'orbite en éclipse (pour β ≤ β_crit) :

$$F_{éclipse} = \frac{1}{\pi} \arccos\left(\frac{\sqrt{1 - (R_E / r)^2 \cos^2\beta}}{\cos\beta}\right)$$

$$t_{éclipse} = F_{éclipse} \cdot T_{orb}$$

```python
def compute_eclipse_fraction(altitude_km, beta_deg):
    r = R_EARTH + altitude_km * 1e3
    beta = np.radians(beta_deg)
    beta_crit = np.arcsin(R_EARTH / r)
    
    if abs(beta) >= beta_crit:
        return 0.0  # Pas d'éclipse
    
    cos_theta = np.sqrt(1 - (R_EARTH / r)**2 * np.cos(beta)**2) / np.cos(beta)
    f_eclipse = (1/np.pi) * np.arccos(cos_theta)
    return f_eclipse
```

### 5.5 Position Angulaire sur l'Orbite

On paramètre la position par l'anomalie vraie θ ∈ [0, 2π] :

```python
def is_in_eclipse(theta, altitude_km, beta_deg):
    """
    theta : anomalie vraie [rad], 0 = passage au nœud ascendant
    Retourne True si le satellite est en éclipse
    """
    r = R_EARTH + altitude_km * 1e3
    beta = np.radians(beta_deg)
    
    # Projection dans le plan perpendiculaire à la direction Soleil
    rho = r * np.cos(beta) * np.cos(theta - np.pi)  # Distance à l'ombre
    
    # Critère d'entrée dans le cône d'ombre (simplification géométrique)
    xi = r * np.cos(beta)
    eta = r * np.sin(beta) * np.sin(theta)
    
    return (xi < 0) and (np.sqrt(r**2 - xi**2 - eta**2 + ...) < R_EARTH)
```

*Note : La formulation exacte est dans la section code — ici on donne le concept.*

### 5.6 Vecteurs de Normale aux Faces en Fonction de l'Orientation

Le CubeSat est supposé en **orientation nadir-pointing** (une face toujours vers la Terre) :

```python
# Vecteurs normaux des 6 faces dans le repère orbital (RTN : Radial, Transverse, Normal)
# Orientation nadir-pointing : face -Z toujours vers Terre

FACE_NORMALS = {
    '+X': np.array([1, 0, 0]),   # Transverse (direction de vol)
    '-X': np.array([-1, 0, 0]),  # Arrière
    '+Y': np.array([0, 1, 0]),   # Normal (perpendiculaire plan orbital)
    '-Y': np.array([0, -1, 0]),  # Normal (autre côté)
    '+Z': np.array([0, 0, 1]),   # Zenith (vers l'espace)
    '-Z': np.array([0, 0, -1]),  # Nadir (vers la Terre)
}
```

---

## 6. Environnement Thermique Spatial

### 6.1 Constante Solaire et Variation

$$S_0 = 1361 \text{ W/m}^2 \quad \text{(valeur nominale à 1 UA)}$$

Variation annuelle (excentricité orbitale terrestre) :
$$S(d) = S_0 \left(1 + 0.033 \cos\left(\frac{2\pi d}{365}\right)\right)$$

Pour la simulation : on prend **S = 1361 W/m²** (nominal).

### 6.2 Flux Solaire Direct sur Chaque Face

$$\dot{Q}_{sol,i} = \alpha_i \cdot S \cdot A_i \cdot \max(0, \hat{n}_i \cdot \hat{s}) \cdot F_{sun}(t)$$

Avec :
- $\hat{n}_i$ : vecteur unitaire normal à la face i
- $\hat{s}$ : vecteur unitaire direction Soleil dans le repère satellite
- $F_{sun}(t)$ : 1 si en plein soleil, 0 si éclipse (fonction de θ(t))
- $\max(0, \cdot)$ : annule le flux si la face est en ombre (angle > 90°)

```python
def solar_flux(face_normal, sun_vector, alpha, area, solar_constant, in_sunlight):
    if not in_sunlight:
        return 0.0
    cos_angle = np.dot(face_normal, sun_vector)
    return alpha * solar_constant * area * max(0.0, cos_angle)
```

### 6.3 Albédo Terrestre

La Terre réfléchit ~30% de l'énergie solaire (albédo a_E ≈ 0.30).

**Modèle simplifié (facteur de vue Lambertien) :**

$$\dot{Q}_{alb,i} = \alpha_i \cdot a_E \cdot S \cdot A_i \cdot F_{alb,i} \cdot F_{sun}(t)$$

Le facteur de vue $F_{alb,i}$ dépend de la géométrie :
- Face nadir (+Z en Earth-facing) : facteur maximal
- Faces latérales : facteur partiel
- Face zenith : facteur quasi-nul

**Calcul du facteur de vue Albédo (approx. sphère à altitude h) :**

$$F_{alb} = \frac{1}{2}\left(1 - \sqrt{1 - \left(\frac{R_E}{R_E + h}\right)^2}\right)$$

Pour h = 550 km → F_alb ≈ 0.32 (facteur global)

```python
def albedo_flux(face_normal, nadir_vector, alpha, area, solar_const, 
                altitude_km, in_sunlight, albedo_coeff=0.30):
    if not in_sunlight:
        return 0.0  # Pas d'albédo si la Terre est dans l'ombre du Soleil
    
    R_E = 6371e3
    h = altitude_km * 1e3
    F_view = 0.5 * (1 - np.sqrt(1 - (R_E / (R_E + h))**2))
    
    # Cos(angle face/nadir) — seules les faces "regardant" la Terre reçoivent l'albédo
    cos_nadir = np.dot(face_normal, -nadir_vector)  # nadir pointe vers bas
    F_directional = max(0.0, cos_nadir)
    
    return alpha * albedo_coeff * solar_const * area * F_view * F_directional
```

### 6.4 Rayonnement Infrarouge Terrestre (OLR)

La Terre émet en propre comme un corps à ~255 K :

$$\Phi_{IR,Terre} \approx 237 \text{ W/m}^2 \quad \text{(flux moyen global)}$$

$$\dot{Q}_{IR,i} = \varepsilon_i \cdot \Phi_{IR} \cdot A_i \cdot F_{view,i} \cdot \max(0, \hat{n}_i \cdot \hat{n}_{nadir})$$

**Important :** Ce flux est **permanent** (jour et nuit) car la Terre émet son propre rayonnement thermique indépendamment du Soleil.

```python
def earth_ir_flux(face_normal, nadir_vector, epsilon, area,
                  altitude_km, OLR=237.0):
    R_E = 6371e3
    h = altitude_km * 1e3
    F_view = 0.5 * (1 - np.sqrt(1 - (R_E / (R_E + h))**2))
    
    cos_nadir = np.dot(face_normal, -nadir_vector)
    F_directional = max(0.0, cos_nadir)
    
    return epsilon * OLR * area * F_view * F_directional
```

### 6.5 Émission Radiative vers l'Espace

C'est le seul mécanisme de **refroidissement** en orbite (pas de convection) :

$$\dot{Q}_{rad,espace,i} = \varepsilon_i \cdot \sigma \cdot A_i \cdot T_i^4$$

**Facteur de vue vers l'espace :** Approximation — les faces externes voient l'espace (T_espace = 3K ≈ 0K) avec F_view ≈ 1.0 (le 3 K contribue négligemment : σ × 3⁴ = 4.6 × 10⁻⁶ W/m² vs σ × 300⁴ = 459 W/m²).

```python
def radiation_to_space(T_kelvin, epsilon, area, T_space=3.0):
    SIGMA = 5.67e-8
    return epsilon * SIGMA * area * (T_kelvin**4 - T_space**4)
```

### 6.6 Dissipation Interne (Sources Thermiques Électroniques)

Le CubeSat embarque des composants qui dissipent de la chaleur :

| Composant | Mode Eclipse | Mode Sunlight | Commentaire |
|---|---|---|---|
| OBC (ordinateur de bord) | 0.5 W | 0.5 W | Toujours actif |
| EPS (gestion d'énergie) | 0.3 W | 0.5 W | Plus actif au soleil (chargement) |
| Radio UHF/VHF | 0.0 W | 0.8 W | Tx uniquement en visibilité sol |
| Payload (caméra) | 0.0 W | 2.0 W | Actif seulement en sunlight |
| ADCS (attitude) | 0.2 W | 0.2 W | Magnétocoupleurs continus |
| **TOTAL** | **~1.0 W** | **~4.0 W** | Dissipé dans N8 (OBC+EPS) et N9 |

```python
def internal_power(t_orbital, in_sunlight, config):
    """
    Retourne la dissipation [W] pour chaque nœud interne selon la phase orbitale
    """
    if in_sunlight:
        return {
            'obc_eps': config['power']['obc'] + config['power']['eps_sun'],
            'payload': config['power']['payload_sun'],
            'adcs': config['power']['adcs']
        }
    else:
        return {
            'obc_eps': config['power']['obc'] + config['power']['eps_eclipse'],
            'payload': 0.0,
            'adcs': config['power']['adcs']
        }
```

---

## 7. Couplages Thermiques Internes

### 7.1 Conduction — Conductance Linéaire (GL)

La conductance linéaire entre deux nœuds i et j représente le flux conductif :

$$\dot{Q}_{cond,ij} = GL_{ij} \cdot (T_j - T_i) \quad [W]$$

$$GL_{ij} = \frac{k_{ij} \cdot A_{contact,ij}}{L_{ij}} \quad [W/K]$$

**Matrice GL pour le modèle 3U (valeurs approchées) :**

| Connexion | k [W/m·K] | A [cm²] | L [mm] | GL [W/K] |
|---|---|---|---|---|
| Face +X ↔ Structure | 160 | 2×1 | 5 | 0.064 |
| Face -X ↔ Structure | 160 | 2×1 | 5 | 0.064 |
| Face +Y ↔ Structure | 160 | 2×3 | 5 | 0.096 |
| Face -Y ↔ Structure | 160 | 2×3 | 5 | 0.096 |
| Face +Z ↔ Structure | 160 | 4×1 | 5 | 0.128 |
| Face -Z ↔ Structure | 160 | 4×1 | 5 | 0.128 |
| Structure ↔ OBC/EPS | 160 | 4×2 | 3 | 0.427 |
| Structure ↔ Payload | 160 | 4×2 | 3 | 0.427 |
| OBC/EPS ↔ Payload | 0.3 (air/vide) | N/A | N/A | **0.005** (très faible) |

**Note :** Dans l'espace, les contacts mécaniques sont critiques. Une mauvaise interface conduit thermique peut créer des points chauds. Les vis + interface fillers (graisse thermique, Cho-Bond) améliorent GL.

```python
# Dans thermal_model.py
GL_MATRIX = np.zeros((9, 9))

# Faces → Structure (N7, index 6)
for face_idx in range(6):
    GL_MATRIX[face_idx, 6] = config['gl']['face_to_structure']
    GL_MATRIX[6, face_idx] = config['gl']['face_to_structure']

# Structure → OBC/EPS (N8, index 7)
GL_MATRIX[6, 7] = config['gl']['structure_to_obc']
GL_MATRIX[7, 6] = config['gl']['structure_to_obc']

# Structure → Payload (N9, index 8)
GL_MATRIX[6, 8] = config['gl']['structure_to_payload']
GL_MATRIX[8, 6] = config['gl']['structure_to_payload']
```

### 7.2 Radiation Interne — Conductance Radiative (GR)

Entre deux nœuds internes à vue directe :

$$\dot{Q}_{rad,ij} = GR_{ij} \cdot (T_j^4 - T_i^4)$$

$$GR_{ij} = \frac{\sigma \cdot A_i \cdot F_{ij}}{\frac{1}{\varepsilon_i} + \frac{A_i}{A_j}\left(\frac{1}{\varepsilon_j} - 1\right)}$$

Avec $F_{ij}$ le facteur de forme entre les surfaces i et j (0 ≤ F_ij ≤ 1).

Pour un CubeSat de structure simple, on simplifie :
- Rayonnement interne = **faible** par rapport à la conduction (espace confiné, T intérieure relativement uniforme)
- On le garde pour la précision mais on peut le linéariser autour de T_ref

**Linéarisation autour de T₀ = 280 K :**

$$T_j^4 - T_i^4 \approx 4 T_0^3 (T_j - T_i)$$

$$GR_{lin,ij} = GR_{ij} \cdot 4 T_0^3 \quad [W/K]$$

```python
def linearized_GR(GR, T_ref=280.0):
    return GR * 4 * T_ref**3
```

---

## 8. Intégration Numérique ODE

### 8.1 Formulation du Système pour solve_ivp

```python
# Dans solver.py

from scipy.integrate import solve_ivp
import numpy as np

def run_simulation(model, config):
    """
    Intègre le système d'ODE sur n_orbits orbites complètes.
    
    Retourne un objet OdeResult avec :
    - sol.t  : vecteur temps [s]
    - sol.y  : matrice températures (9 × N_points) [K]
    """
    T_init = np.full(9, config['initial_conditions']['T_init_K'])
    t_span = (0, config['simulation']['n_orbits'] * model.T_orb)
    t_eval = np.linspace(*t_span, config['simulation']['n_points'])
    
    sol = solve_ivp(
        fun=lambda t, T: model.dTdt(t, T),
        t_span=t_span,
        y0=T_init,
        method='RK45',          # Runge-Kutta 4(5) — bon compromis précision/vitesse
        t_eval=t_eval,
        rtol=1e-4,              # Tolérance relative
        atol=1e-6,              # Tolérance absolue [K]
        dense_output=False,
        max_step=30.0           # Pas max de 30s (résoudre les transitions éclipse)
    )
    
    if not sol.success:
        raise RuntimeError(f"Simulation failed: {sol.message}")
    
    return sol
```

### 8.2 Choix du Solveur et Justification

| Solveur | Type | Adapté pour | Commentaire |
|---|---|---|---|
| `RK45` | Explicite adaptatif | Systèmes non raides | **Choix par défaut** pour CubeSat |
| `Radau` | Implicite | Systèmes raides | Si GL très grands (structures métalliques massives) |
| `LSODA` | Hybride auto | Peut basculer | Alternative robuste si convergence difficile |
| `DOP853` | Explicite ordre 8 | Précision élevée | Si besoin de résultats très précis |

**Raideur du système :** Le ratio GL_max / C_min donne une idée du caractère raide :
- τ = C / GL : constante de temps thermique
- Si τ_min << τ_max (ratio > 1000) → système raide → utiliser `Radau`
- Pour notre modèle : τ varie de ~2h (structure) à ~10min (faces) → pas très raide → `RK45` OK

### 8.3 Conditions Initiales et Convergence

**Problème :** Les conditions initiales sont inconnues (on ne sait pas quelle est la T au moment du lancement).

**Solution :** Lancer la simulation sur 5 orbites, utiliser les températures à la fin de l'orbite 4 comme "état établi" — les 4 premières orbites sont le transitoire. Afficher seulement les orbites 3, 4, 5.

```python
N_ORBITS_WARMUP = 2   # Orbites d'initialisation ignorées
N_ORBITS_STEADY = 3   # Orbites affichées (état quasi-stationnaire)
```

---

## 9. Dashboard Streamlit

### 9.1 Architecture de l'App

```python
# Dans app/app.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import yaml
from pathlib import Path
import sys
sys.path.append('..')
from src.solver import run_simulation
from src.thermal_model import ThermalModel

st.set_page_config(
    page_title="CubeSat Thermal Analysis",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

### 9.2 Layout des Panneaux

```
┌─────────────────────────────────────────────────────────────────────┐
│  🛰️ CubeSat 3U — Thermal Balance Dashboard (LEO 550 km)            │
├─────────────┬───────────────────────────────────────────────────────┤
│  SIDEBAR    │  MAIN CONTENT                                         │
│             │                                                       │
│ ─ Orbital ─ │  ┌─────────────────────┬─────────────────────┐       │
│  altitude   │  │ T vs Temps (6 faces)│ T structure + interne│       │
│  beta angle │  │    (Plotly line)    │    (Plotly line)     │       │
│  n_orbits   │  └─────────────────────┴─────────────────────┘       │
│             │                                                       │
│ ─ Thermo ─  │  ┌──────────────────────────────────────────┐        │
│  α face +X  │  │ Heatmap : T(face, temps) — vue d'ensemble│        │
│  ε face +X  │  │         (Plotly heatmap)                 │        │
│  ... etc    │  └──────────────────────────────────────────┘        │
│             │                                                       │
│ ─ Power ─   │  ┌──────────────────┬──────────────────────┐         │
│  P_obc      │  │ Flux thermiques  │ Marges / Limites     │         │
│  P_payload  │  │ (pie chart moyen)│ (bar chart Tmin/Tmax)│         │
│             │  └──────────────────┴──────────────────────┘         │
│ [▶ Run]     │                                                       │
└─────────────┴───────────────────────────────────────────────────────┘
```

### 9.3 Graphiques à Implémenter

#### Plot 1 : Températures des 6 faces vs Temps

```python
def plot_face_temperatures(sol, model):
    fig = go.Figure()
    
    face_names = ['+X', '-X', '+Y', '-Y', '+Z (zenith)', '-Z (nadir)']
    colors = px.colors.qualitative.Set1
    
    t_minutes = sol.t / 60  # Convertir en minutes
    
    for i, name in enumerate(face_names):
        T_celsius = sol.y[i] - 273.15
        fig.add_trace(go.Scatter(
            x=t_minutes, y=T_celsius,
            name=f'Face {name}', line=dict(color=colors[i]),
            mode='lines'
        ))
    
    # Ajouter les zones d'éclipse en arrière-plan
    for eclipse_start, eclipse_end in model.eclipse_periods:
        fig.add_vrect(
            x0=eclipse_start/60, x1=eclipse_end/60,
            fillcolor='rgba(0,0,100,0.1)', line_width=0,
            annotation_text="Eclipse", annotation_position="top left"
        )
    
    # Limites thermiques CubeSat typiques
    fig.add_hline(y=85, line_dash="dash", line_color="red",
                  annotation_text="Tmax opérationnel (+85°C)")
    fig.add_hline(y=-40, line_dash="dash", line_color="blue",
                  annotation_text="Tmin opérationnel (-40°C)")
    
    fig.update_layout(
        title="Températures des faces du CubeSat",
        xaxis_title="Temps [min]",
        yaxis_title="Température [°C]",
        hovermode='x unified'
    )
    return fig
```

#### Plot 2 : Heatmap Faces × Temps

```python
def plot_temperature_heatmap(sol, model):
    face_names = ['+X', '-X', '+Y', '-Y', '+Z', '-Z']
    T_celsius = sol.y[:6] - 273.15
    t_minutes = sol.t / 60
    
    fig = px.imshow(
        T_celsius,
        x=t_minutes,
        y=face_names,
        color_continuous_scale='RdYlBu_r',
        labels={'x': 'Temps [min]', 'y': 'Face', 'color': 'T [°C]'},
        title='Carte thermique — Faces vs Temps'
    )
    return fig
```

#### Plot 3 : Marges Thermiques (Bar Chart)

```python
def plot_thermal_margins(sol, limits):
    node_names = ['+X', '-X', '+Y', '-Y', '+Z', '-Z', 'Structure', 'OBC/EPS', 'Payload']
    T_min = (sol.y.min(axis=1) - 273.15).tolist()
    T_max = (sol.y.max(axis=1) - 273.15).tolist()
    
    # Limites par nœud
    T_limit_min = [limits['panels']['min']] * 6 + [
        limits['structure']['min'],
        limits['electronics']['min'],
        limits['payload']['min']
    ]
    T_limit_max = [limits['panels']['max']] * 6 + [
        limits['structure']['max'],
        limits['electronics']['max'],
        limits['payload']['max']
    ]
    
    margin_min = [t - lim for t, lim in zip(T_min, T_limit_min)]
    margin_max = [lim - t for t, lim in zip(T_max, T_limit_max)]
    
    # Code couleur : vert si marge > 10°C, orange si < 10°C, rouge si négatif
    colors_min = ['green' if m > 10 else 'orange' if m > 0 else 'red' for m in margin_min]
    colors_max = ['green' if m > 10 else 'orange' if m > 0 else 'red' for m in margin_max]
    
    fig = make_subplots(rows=1, cols=2, subplot_titles=['Marge froide', 'Marge chaude'])
    fig.add_trace(go.Bar(x=node_names, y=margin_min, marker_color=colors_min, name='ΔT_min'), row=1, col=1)
    fig.add_trace(go.Bar(x=node_names, y=margin_max, marker_color=colors_max, name='ΔT_max'), row=1, col=2)
    
    return fig
```

### 9.4 Limites Thermiques de Référence CubeSat

```yaml
# Dans cubesat_config.yaml
thermal_limits:
  panels:
    min_C: -100   # Aluminium — très large plage
    max_C: +120
  structure:
    min_C: -80
    max_C: +100
  obc_eps:         # Composants électroniques
    min_C: -40
    max_C: +85
  payload_camera:  # Le plus critique
    min_C: -20
    max_C: +60
  battery:         # Non modélisé explicitement mais à noter
    min_C: 0       # Batteries LiPo ne chargent pas en dessous de 0°C !
    max_C: +45
```

---

## 10. Analyse de Sensibilité

### 10.1 Paramètres d'Étude

L'analyse de sensibilité est la valeur ajoutée ingénieur du projet :

```python
SENSITIVITY_PARAMS = {
    'beta_angle': {
        'values': [0, 15, 30, 45, 60, 75, 90],  # degrés
        'unit': '°', 'label': 'Angle β'
    },
    'alpha_panels': {
        'values': [0.10, 0.23, 0.37, 0.60, 0.85, 0.93],  # coatings différents
        'unit': '', 'label': 'Absorptivité α'
    },
    'epsilon_panels': {
        'values': [0.05, 0.20, 0.50, 0.70, 0.85, 0.92],
        'unit': '', 'label': 'Émissivité ε'
    },
    'internal_power': {
        'values': [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 8.0],  # Watts
        'unit': 'W', 'label': 'Puissance interne'
    },
    'thermal_capacity': {
        'values': [0.5, 0.75, 1.0, 1.5, 2.0],  # Facteur multiplicatif
        'unit': '×', 'label': 'Inertie thermique (facteur)'
    }
}
```

### 10.2 Méthode d'Exécution

```python
def run_sensitivity_analysis(base_config, param_name, values):
    """
    Lance une simulation pour chaque valeur du paramètre.
    Retourne T_min et T_max par nœud pour chaque cas.
    """
    results = []
    
    for val in values:
        config = deepcopy(base_config)
        set_nested_param(config, param_name, val)  # Modifie le param dans le dict
        
        model = ThermalModel(config)
        sol = run_simulation(model, config)
        
        # Extraire les statistiques (après 2 orbites de stabilisation)
        i_start = len(sol.t) // 3  # Ignorer le premier tiers
        T_steady = sol.y[:, i_start:]
        
        results.append({
            'param_value': val,
            'T_min': T_steady.min(axis=1) - 273.15,  # °C par nœud
            'T_max': T_steady.max(axis=1) - 273.15,
            'T_mean': T_steady.mean(axis=1) - 273.15,
            'delta_T': T_steady.max(axis=1) - T_steady.min(axis=1)  # Amplitude
        })
    
    return results
```

### 10.3 Visualisation de la Sensibilité

```python
def plot_sensitivity(results, param_label, node_idx=8, node_name='Payload'):
    """
    Tornado chart de sensibilité : T_min et T_max du nœud le plus critique (Payload)
    en fonction du paramètre étudié.
    """
    values = [r['param_value'] for r in results]
    T_mins = [r['T_min'][node_idx] for r in results]
    T_maxs = [r['T_max'][node_idx] for r in results]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=values, y=T_mins, name='T_min Payload', 
                              line=dict(color='blue', dash='dot')))
    fig.add_trace(go.Scatter(x=values, y=T_maxs, name='T_max Payload', 
                              line=dict(color='red')))
    fig.add_hrect(y0=-20, y1=60, fillcolor='green', opacity=0.1,
                  annotation_text="Plage opérationnelle payload")
    
    fig.update_layout(title=f'Sensibilité {node_name} — {param_label}',
                       xaxis_title=param_label,
                       yaxis_title='Température [°C]')
    return fig
```

---

## 11. Structure du Code — Recette Fichier par Fichier

### 11.1 `config/cubesat_config.yaml` — Écrire en premier

```yaml
# ============================================================
# CubeSat 3U - Configuration Thermique
# Tous les paramètres physiques centralisés ici
# ============================================================

satellite:
  name: "3U CubeSat LEO"
  total_mass_kg: 4.0
  dimensions:
    x_mm: 100
    y_mm: 100
    z_mm: 300

orbit:
  altitude_km: 550
  inclination_deg: 51.6
  beta_angle_deg: 30.0

simulation:
  n_orbits: 5
  n_points: 5000          # Points temporels (résolution = T_orb * n_orbits / n_points)
  n_warmup_orbits: 2      # Orbites ignorées pour le transitoire initial
  T_init_K: 280.0         # Température initiale uniforme

environment:
  solar_constant_Wm2: 1361.0
  earth_albedo: 0.30
  earth_OLR_Wm2: 237.0
  T_space_K: 3.0

# Propriétés thermo-optiques par face (α, ε)
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
    mass_kg: 0.10    # Panneau solaire + substrat
    cp_JkgK: 750.0
  minus_Y:
    material: "solar_panel"
    alpha: 0.92
    epsilon: 0.85
    area_m2: 0.030
    mass_kg: 0.10
    cp_JkgK: 750.0
  plus_Z:
    material: "painted_white"   # Zenith
    alpha: 0.23
    epsilon: 0.88
    area_m2: 0.010
    mass_kg: 0.04
    cp_JkgK: 896.0
  minus_Z:
    material: "painted_white"   # Nadir
    alpha: 0.23
    epsilon: 0.88
    area_m2: 0.010
    mass_kg: 0.04
    cp_JkgK: 896.0

# Nœuds internes
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

# Conductances linéaires [W/K]
conductances_GL:
  face_to_structure: 0.064    # Toutes les faces → structure (sera surchargé par face si besoin)
  structure_to_obc: 0.427
  structure_to_payload: 0.427
  obc_to_payload: 0.005

# Puissance dissipée [W]
power_dissipation:
  obc_W: 0.5
  eps_sun_W: 0.5
  eps_eclipse_W: 0.3
  payload_sun_W: 2.0
  payload_eclipse_W: 0.0
  adcs_W: 0.2
  radio_sun_W: 0.8
  radio_eclipse_W: 0.0

# Limites thermiques opérationnelles [°C]
thermal_limits:
  panels:  {min_C: -100, max_C: 120}
  structure: {min_C: -80, max_C: 100}
  obc_eps: {min_C: -40, max_C: 85}
  payload: {min_C: -20, max_C: 60}
```

### 11.2 `src/orbital.py` — Écrire en deuxième

```python
"""
orbital.py — Mécanique orbitale simplifiée pour simulation thermique CubeSat

Hypothèses :
- Orbite circulaire (excentricité = 0)
- Deux corps (Terre + satellite)
- Ombre cylindrique (simplification : ombre pénombre ignorée)
- Angle β constant sur la simulation (< 1 orbite << précession nodale)
"""

import numpy as np
from dataclasses import dataclass

# Constantes
R_EARTH = 6371e3        # m
MU_EARTH = 3.986004418e14  # m³/s²
SIGMA = 5.67e-8         # W/(m²·K⁴)
AU = 1.496e11           # m

@dataclass
class OrbitalParameters:
    altitude_km: float
    beta_deg: float
    
    def __post_init__(self):
        self.r = R_EARTH + self.altitude_km * 1e3
        self.T_orb = 2 * np.pi * np.sqrt(self.r**3 / MU_EARTH)
        self.omega = 2 * np.pi / self.T_orb
        self.beta = np.radians(self.beta_deg)
        self.beta_crit = np.arcsin(R_EARTH / self.r)
        
    @property
    def eclipse_fraction(self):
        if abs(self.beta) >= self.beta_crit:
            return 0.0
        num = np.sqrt(1 - (R_EARTH / self.r)**2 * np.cos(self.beta)**2)
        return (1/np.pi) * np.arccos(num / np.cos(self.beta))
    
    @property
    def eclipse_duration_min(self):
        return self.eclipse_fraction * self.T_orb / 60
    
    @property
    def sunlight_duration_min(self):
        return (1 - self.eclipse_fraction) * self.T_orb / 60


def sun_vector_orbital_frame(t, orbital_params):
    """
    Vecteur unitaire Soleil dans le repère orbital (RTN).
    
    Repère RTN :
    - R : radial (du centre Terre vers le satellite)
    - T : transverse (direction de vol)
    - N : normal au plan orbital
    
    Dans l'approximation angle β constant :
    - Composante N = sin(β) (constante)
    - Composantes R, T varient avec θ = ω*t
    """
    beta = orbital_params.beta
    theta = orbital_params.omega * t  # Position angulaire sur l'orbite
    
    # Vecteur soleil dans RTN (rotation autour de N par θ)
    s_R = -np.cos(beta) * np.sin(theta)   # Composante radiale
    s_T = -np.cos(beta) * np.cos(theta)   # Composante transverse
    s_N = np.sin(beta)                     # Composante normale (constante)
    
    return np.array([s_R, s_T, s_N])


def is_in_eclipse(t, orbital_params):
    """
    Détermine si le satellite est en éclipse au temps t.
    
    Basé sur la géométrie de l'ombre cylindrique :
    Le satellite est en ombre si sa projection sur le plan
    perpendiculaire à la direction Soleil est dans l'ombre de la Terre.
    """
    if abs(orbital_params.beta) >= orbital_params.beta_crit:
        return False  # Jamais d'éclipse pour β > β_crit
    
    theta = orbital_params.omega * t
    beta = orbital_params.beta
    r = orbital_params.r
    
    # Position du satellite dans le plan orbital
    # Ombre cylindrique : condition x > 0 (derrière la Terre) ET y² + z² < R_Earth²
    # Dans RTN avec β :
    x_shadow = -r * np.cos(beta) * np.cos(theta)  # Dans la direction anti-soleil
    y_shadow = r * np.sqrt(np.sin(beta)**2 + np.cos(beta)**2 * np.sin(theta)**2)
    
    # En ombre si devant l'ombre (x > 0) et dans le cylindre (y < R_Earth)
    return (x_shadow > 0) and (y_shadow < R_EARTH)


def nadir_vector_orbital_frame():
    """
    En repère RTN, le vecteur nadir pointe dans la direction -R (vers la Terre).
    En orientation nadir-pointing, la face -Z du satellite est alignée avec -R.
    """
    return np.array([-1, 0, 0])  # -R = vers la Terre
```

### 11.3 `src/environment.py` — Écrire en troisième

```python
"""
environment.py — Calcul des flux thermiques environnementaux

Pour chaque face du CubeSat, calcule à chaque instant t :
- Flux solaire direct [W]
- Flux albédo [W]
- Flux IR Terre [W]
- Ces flux dépendent de : l'orientation du satellite, la position orbitale, l'éclipse
"""

import numpy as np
from .orbital import is_in_eclipse, sun_vector_orbital_frame, nadir_vector_orbital_frame

SIGMA = 5.67e-8
R_EARTH = 6371e3


def view_factor_earth(altitude_km):
    """Facteur de vue géométrique face → Terre (sphère à altitude h)"""
    r = R_EARTH + altitude_km * 1e3
    return 0.5 * (1 - np.sqrt(1 - (R_EARTH / r)**2))


class EnvironmentModel:
    def __init__(self, config):
        self.S0 = config['environment']['solar_constant_Wm2']
        self.a_E = config['environment']['earth_albedo']
        self.OLR = config['environment']['earth_OLR_Wm2']
        self.T_space = config['environment']['T_space_K']
        self.altitude = config['orbit']['altitude_km']
        self.F_earth = view_factor_earth(self.altitude)
        
        # Extraire les normales de face de la config
        self.face_normals = self._build_face_normals(config)
        self.face_props = self._build_face_properties(config)
    
    def _build_face_normals(self, config):
        """Vecteurs normaux dans le repère RTN (orientation nadir-pointing)"""
        return {
            '+X': np.array([0, 1, 0]),    # Transverse avant
            '-X': np.array([0, -1, 0]),   # Transverse arrière
            '+Y': np.array([0, 0, 1]),    # Normal orbital
            '-Y': np.array([0, 0, -1]),   # Normal orbital (autre sens)
            '+Z': np.array([1, 0, 0]),    # Radial extérieur (zenith)
            '-Z': np.array([-1, 0, 0]),   # Radial intérieur (nadir)
        }
    
    def _build_face_properties(self, config):
        """Propriétés thermo-optiques par face"""
        faces = {}
        for face_name, face_config in config['faces'].items():
            face_key = face_name.replace('_', '')  # 'plus_X' → 'plusX'
            # Map vers les clés normalisées
            key_map = {
                'plusX': '+X', 'minusX': '-X', 
                'plusY': '+Y', 'minusY': '-Y',
                'plusZ': '+Z', 'minusZ': '-Z'
            }
            k = key_map.get(face_key, face_key)
            faces[k] = {
                'alpha': face_config['alpha'],
                'epsilon': face_config['epsilon'],
                'area': face_config['area_m2']
            }
        return faces
    
    def compute_fluxes(self, t, orbital_params):
        """
        Calcule TOUS les flux externes pour TOUTES les faces au temps t.
        
        Retourne un dict {face_name: {'solar': W, 'albedo': W, 'IR': W, 'rad_out_coef': W/K⁴}}
        """
        sun_vec = sun_vector_orbital_frame(t, orbital_params)
        nadir_vec = nadir_vector_orbital_frame()
        in_sun = not is_in_eclipse(t, orbital_params)
        
        fluxes = {}
        for face_name, normal in self.face_normals.items():
            props = self.face_props[face_name]
            alpha = props['alpha']
            eps = props['epsilon']
            area = props['area']
            
            cos_sun = max(0.0, np.dot(normal, sun_vec))
            cos_nadir = max(0.0, np.dot(normal, -nadir_vec))  # Faces regardant la Terre
            
            # Flux solaire direct
            Q_sol = alpha * self.S0 * area * cos_sun * (1.0 if in_sun else 0.0)
            
            # Flux albédo
            Q_alb = alpha * self.a_E * self.S0 * area * self.F_earth * cos_nadir * (1.0 if in_sun else 0.0)
            
            # Flux IR Terre (permanent, jour et nuit)
            Q_ir = eps * self.OLR * area * self.F_earth * cos_nadir
            
            # Coefficient de rayonnement vers l'espace (Q = coef * T⁴)
            rad_coef = eps * SIGMA * area
            
            fluxes[face_name] = {
                'solar': Q_sol,
                'albedo': Q_alb,
                'earth_IR': Q_ir,
                'rad_coef': rad_coef,   # Sera utilisé par le modèle thermique
                'in_sunlight': in_sun
            }
        
        return fluxes
```

### 11.4 `src/thermal_model.py` — Le cœur du projet

```python
"""
thermal_model.py — Modèle thermique nodal du CubeSat 3U

9 nœuds :
  0: Face +X   4: Face +Z
  1: Face -X   5: Face -Z
  2: Face +Y   6: Structure
  3: Face -Y   7: OBC/EPS
               8: Payload
"""

import numpy as np
from .orbital import OrbitalParameters
from .environment import EnvironmentModel

SIGMA = 5.67e-8

FACE_INDICES = {'+X': 0, '-X': 1, '+Y': 2, '-Y': 3, '+Z': 4, '-Z': 5}
NODE_NAMES = ['+X', '-X', '+Y', '-Y', '+Z', '-Z', 'Structure', 'OBC/EPS', 'Payload']
N_NODES = 9


class ThermalModel:
    def __init__(self, config):
        self.config = config
        self.orbital = OrbitalParameters(
            altitude_km=config['orbit']['altitude_km'],
            beta_deg=config['orbit']['beta_angle_deg']
        )
        self.env = EnvironmentModel(config)
        
        # Capacités thermiques [J/K]
        self.C = self._build_capacities(config)
        
        # Matrice de conductances linéaires [W/K]
        self.GL = self._build_GL_matrix(config)
        
        # Propriétés par face
        self.face_props = self.env.face_props
        
        # Cache pour l'analyse post-simulation
        self.T_orb = self.orbital.T_orb
        self._eclipse_cache = {}
    
    def _build_capacities(self, config):
        C = np.zeros(N_NODES)
        face_names = ['plus_X', 'minus_X', 'plus_Y', 'minus_Y', 'plus_Z', 'minus_Z']
        for i, fname in enumerate(face_names):
            fc = config['faces'][fname]
            C[i] = fc['mass_kg'] * fc['cp_JkgK']
        
        ic = config['internal_nodes']
        C[6] = ic['structure']['mass_kg'] * ic['structure']['cp_JkgK']
        C[7] = ic['obc_eps']['mass_kg'] * ic['obc_eps']['cp_JkgK']
        C[8] = ic['payload']['mass_kg'] * ic['payload']['cp_JkgK']
        return C
    
    def _build_GL_matrix(self, config):
        GL = np.zeros((N_NODES, N_NODES))
        gl = config['conductances_GL']
        
        # Faces (0-5) ↔ Structure (6)
        for i in range(6):
            GL[i, 6] = gl['face_to_structure']
            GL[6, i] = gl['face_to_structure']
        
        # Structure (6) ↔ OBC/EPS (7)
        GL[6, 7] = gl['structure_to_obc']
        GL[7, 6] = gl['structure_to_obc']
        
        # Structure (6) ↔ Payload (8)
        GL[6, 8] = gl['structure_to_payload']
        GL[8, 6] = gl['structure_to_payload']
        
        # OBC/EPS (7) ↔ Payload (8)
        GL[7, 8] = gl['obc_to_payload']
        GL[8, 7] = gl['obc_to_payload']
        
        return GL
    
    def internal_power(self, t):
        """Dissipation thermique interne [W] — dépend de l'éclipse"""
        in_sun = not (t % self.T_orb in self._get_eclipse_window())
        pd = self.config['power_dissipation']
        
        Q_int = np.zeros(N_NODES)
        if in_sun:
            Q_int[7] = pd['obc_W'] + pd['eps_sun_W'] + pd['radio_sun_W']
            Q_int[8] = pd['payload_sun_W']
        else:
            Q_int[7] = pd['obc_W'] + pd['eps_eclipse_W']
            Q_int[8] = pd['payload_eclipse_W']
        
        Q_int[6] = pd['adcs_W']  # ADCS dans la structure
        return Q_int
    
    def dTdt(self, t, T):
        """
        Fonction d'état pour scipy.integrate.solve_ivp
        T : array[9] en Kelvin
        Retourne dT/dt array[9] en K/s
        """
        dT = np.zeros(N_NODES)
        
        # Flux environnementaux sur les faces
        fluxes = self.env.compute_fluxes(t, self.orbital)
        
        # Dissipation interne
        Q_int = self.internal_power(t)
        
        for i in range(N_NODES):
            Q_total = Q_int[i]  # Sources internes
            
            if i < 6:  # Nœuds de face (exposés à l'espace)
                face_name = NODE_NAMES[i]
                flux = fluxes[face_name]
                
                # Flux entrants
                Q_total += flux['solar'] + flux['albedo'] + flux['earth_IR']
                
                # Rayonnement vers l'espace (sortant)
                Q_total -= flux['rad_coef'] * T[i]**4
            
            # Conduction avec les voisins
            for j in range(N_NODES):
                if self.GL[i, j] > 0:
                    Q_total += self.GL[i, j] * (T[j] - T[i])
            
            dT[i] = Q_total / self.C[i]
        
        return dT
    
    def _get_eclipse_window(self):
        """Retourne les phases d'éclipse dans une orbite (en secondes depuis début orbite)"""
        # Simplification : éclipse centrée à θ = π (côté opposé au Soleil)
        f_ecl = self.orbital.eclipse_fraction
        t_ecl = f_ecl * self.T_orb
        t_center = self.T_orb / 2
        return range(int(t_center - t_ecl/2), int(t_center + t_ecl/2))
```

### 11.5 `src/solver.py` — Propre et robuste

```python
"""
solver.py — Lancement de l'intégration ODE et post-traitement des résultats
"""

import numpy as np
from scipy.integrate import solve_ivp
from dataclasses import dataclass, field


@dataclass
class SimulationResult:
    t: np.ndarray                          # Temps [s]
    T_K: np.ndarray                        # Températures [K] — shape (9, N)
    node_names: list = field(default_factory=list)
    T_orb: float = 0.0
    n_warmup_orbits: int = 2
    
    @property
    def T_C(self):
        return self.T_K - 273.15
    
    @property
    def t_minutes(self):
        return self.t / 60
    
    @property
    def t_steady(self):
        """Temps en régime établi (après warmup)"""
        t_start = self.n_warmup_orbits * self.T_orb
        mask = self.t >= t_start
        return self.t[mask]
    
    @property
    def T_steady_C(self):
        """Températures en régime établi"""
        t_start = self.n_warmup_orbits * self.T_orb
        mask = self.t >= t_start
        return self.T_C[:, mask]
    
    def summary(self):
        """Tableau récapitulatif des températures min/max/moyenne en régime établi"""
        T = self.T_steady_C
        return {
            name: {
                'T_min': round(T[i].min(), 1),
                'T_max': round(T[i].max(), 1),
                'T_mean': round(T[i].mean(), 1),
                'delta_T': round(T[i].max() - T[i].min(), 1)
            }
            for i, name in enumerate(self.node_names)
        }


def run_simulation(model, config) -> SimulationResult:
    T_init = np.full(9, config['simulation']['T_init_K'])
    n_orbits = config['simulation']['n_orbits']
    t_final = n_orbits * model.T_orb
    n_points = config['simulation']['n_points']
    
    t_eval = np.linspace(0, t_final, n_points)
    
    sol = solve_ivp(
        fun=lambda t, T: model.dTdt(t, T),
        t_span=(0.0, t_final),
        y0=T_init,
        method='RK45',
        t_eval=t_eval,
        rtol=1e-4,
        atol=1e-6,
        max_step=model.T_orb / 200,  # ≥ 200 pas par orbite (résolution suffisante)
        dense_output=False
    )
    
    if not sol.success:
        raise RuntimeError(f"Simulation diverged: {sol.message}")
    
    from .thermal_model import NODE_NAMES
    
    return SimulationResult(
        t=sol.t,
        T_K=sol.y,
        node_names=NODE_NAMES,
        T_orb=model.T_orb,
        n_warmup_orbits=config['simulation']['n_warmup_orbits']
    )
```

---

## 12. Données d'Entrée & Paramètres

### 12.1 Requirements.txt

```text
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0
plotly>=5.14.0
streamlit>=1.25.0
pyyaml>=6.0
matplotlib>=3.7.0          # Pour les figures statiques du rapport
reportlab>=4.0.0           # Pour la génération PDF du rapport
jupyter>=1.0.0             # Pour les notebooks de validation
pytest>=7.3.0              # Pour les tests unitaires
```

### 12.2 Sources des Paramètres

| Paramètre | Valeur | Source |
|---|---|---|
| Constante solaire | 1361 W/m² | SORCE/TIM (NASA) |
| Albédo terrestre moyen | 0.30 | CERES Earth Energy Budget |
| OLR terrestre moyen | 237 W/m² | CERES Earth Energy Budget |
| Température spatiale | 3 K | CMB (fond diffus cosmologique) |
| α peinture blanche | 0.23 | Sheldahl / AZ-93 datasheet |
| ε peinture blanche | 0.88 | Sheldahl / AZ-93 datasheet |
| Masse 3U typique | 2–4 kg | CubeSat Design Spec Rev 14 |
| Puissance max 3U | 10 W (panneaux) | Typical 3U EPS datasheets |

---

## 13. Livrables & Sorties Attendues

### 13.1 Sortie Console (main_simulation.py)

```
========================================
  CubeSat 3U — Thermal Simulation
  Orbit: 550 km LEO, β = 30°
  Duration: 5 orbits (≈481 min)
========================================

Orbital parameters:
  Period      : 95.5 min
  Eclipse     : 34.8 min/orbit (36.4%)
  β_critical  : 66.9°
  Sun fraction : 63.6%

Running simulation... ████████████████ 100% (5.2 s)

=== Steady-State Results (orbits 3-5) ===
Node         T_min [°C]  T_max [°C]  ΔT [°C]  Status
-----------  ----------  ----------  -------  --------
Face +X          -42.3       +63.1     105.4   ✓ OK
Face -X          -44.1       +61.8     105.9   ✓ OK
Face +Y (PV)     -38.2       +71.4     109.6   ✓ OK
Face -Y (PV)     -39.0       +70.2     109.2   ✓ OK
Face +Z          -51.2       +48.3      99.5   ✓ OK
Face -Z          -39.8       +55.7      95.5   ✓ OK
Structure        -21.4       +38.2      59.6   ✓ OK
OBC/EPS          -14.8       +44.7      59.5   ✓ OK
Payload          -16.2       +42.1      58.3   ✓ OK

⚠  Critical check: Payload T_min = -16.2°C (limit: -20°C) → Margin: 3.8°C — TIGHT!

Results saved to results/run_550km_b30/
```

### 13.2 Fichiers de Sortie

```
results/run_550km_b30/
├── temperatures.csv        # T[K] vs t[s] pour les 9 nœuds
├── summary.json            # T_min/T_max/T_mean par nœud
├── orbital_params.json     # Paramètres orbitaux calculés
├── fluxes.csv              # Flux instantanés par face (pour vérification)
└── figures/
    ├── face_temperatures.html    # Plotly interactif
    ├── heatmap.html
    ├── thermal_margins.html
    └── sensitivity_beta.html
```

---

## 14. Plan d'Exécution Phase par Phase

### Phase 1 — Fondations (3-4 jours)

**Objectif :** Avoir un modèle qui tourne et produit des résultats physiquement cohérents.

- [ ] Créer la structure de dossiers
- [ ] Écrire `cubesat_config.yaml` complet
- [ ] Écrire `src/orbital.py` + test notebook de validation
  - Vérifier T_orb ≈ 96 min pour 550 km
  - Vérifier fraction éclipse ≈ 36% pour β=0°
  - Tracer le flag éclipse vs temps sur 3 orbites
- [ ] Écrire `src/environment.py` + validation
  - Vérifier Q_sol ≈ 0 sur toutes les faces quand éclipse=True
  - Vérifier Q_sol > 0 seulement sur les faces orientées vers le Soleil
  - Vérifier Q_IR > 0 seulement sur les faces regardant la Terre
- [ ] **Test de cohérence dimensionnelle :** Q_total moyen sur une orbite ≈ 0 à l'équilibre thermique

### Phase 2 — Modèle Thermique (4-5 jours)

**Objectif :** ODE qui converge vers un régime cohérent.

- [ ] Écrire `src/thermal_model.py`
- [ ] Écrire `src/solver.py`
- [ ] Lancer une première simulation, vérifier :
  - Pas de divergence numérique (T restant entre 100 K et 500 K)
  - Convergence vers régime quasi-stationnaire après 2 orbites
  - Températures dans la plage physique attendue
- [ ] **Validation simple :** Cas extrême β=90° (pas d'éclipse) → température plus haute. Cas β=0° → température plus basse et cyclique. Vérifier qualitativement.
- [ ] Écrire `scripts/main_simulation.py` avec sortie console formatée

### Phase 3 — Dashboard (3-4 jours)

**Objectif :** Visualisation interactive complète.

- [ ] Écrire `app/app.py` avec les 4 graphiques Plotly
- [ ] Sidebar avec tous les paramètres configurables
- [ ] Bouton "Run Simulation" qui relance en temps réel
- [ ] Affichage des marges thermiques avec code couleur
- [ ] Test local : `streamlit run app/app.py`

### Phase 4 — Analyse de Sensibilité (2-3 jours)

**Objectif :** Résultats ingénieur à haute valeur ajoutée.

- [ ] Écrire `src/sensitivity.py`
- [ ] Lancer la boucle de sensibilité sur 5 paramètres (peut prendre 10-30 min)
- [ ] Graphiques de sensibilité intégrés dans le dashboard

### Phase 5 — Finition Portfolio (2 jours)

**Objectif :** Présentation GitHub professionnelle.

- [ ] Écrire le README.md final (voir section suivante)
- [ ] Écrire les tests unitaires `tests/`
- [ ] Captures d'écran du dashboard → dossier `images/`
- [ ] `notebooks/01_physics_validation.ipynb` avec les checks étape par étape
- [ ] Vérifier que `pip install -r requirements.txt && streamlit run app/app.py` fonctionne depuis zéro

---

## 15. README GitHub

```markdown
# 🛰️ CubeSat 3U Thermal Balance — LEO Orbit Simulation

> **Portfolio project** | Energy Engineering → Space Systems transition  
> Applying industrial thermal-hydraulic modeling methods (EPR2/Edvance) to a CubeSat in LEO.

## What This Demonstrates

| Skill | How it's shown |
|---|---|
| Nodal thermal modeling | 9-node lumped parameter model with full coupling matrix |
| Orbital mechanics | Kepler, eclipse fraction, β-angle, shadow geometry |
| Space thermal environment | Solar flux, albedo, Earth IR, radiative cooling |
| Scientific Python | NumPy, SciPy ODE solver, Plotly, Streamlit |
| Engineering judgment | Sensitivity analysis, thermal margin assessment |
| Industrial workflow | YAML-based config, automated pipeline, reproducible results |

## Physics in 30 Seconds

The CubeSat thermal problem is fundamentally different from building HVAC (my EPR2 background):
**no convection** exists in vacuum. Heat flows only via:
- ☀️ **Absorbed radiation** (Sun + Earth albedo + Earth IR)  
- 🌡️ **Emitted radiation** to deep space (Stefan-Boltzmann)  
- 🔩 **Internal conduction** through structural interfaces

The satellite alternates between eclipse (~36 min) and sunlight (~60 min) every 96-minute orbit,
creating ΔT cycles of 80–110°C on external panels.

## Quick Start

```bash
git clone https://github.com/[username]/cubesat-thermal
cd cubesat-thermal
pip install -r requirements.txt

# Run CLI simulation
python scripts/main_simulation.py

# Or launch interactive dashboard
streamlit run app/app.py
```

## Results Preview

[Dashboard screenshot here]

**Nominal case** (550 km LEO, β=30°, white paint + solar panels):

| Component | T_min | T_max | Status |
|---|---|---|---|
| Panels | −44°C | +71°C | ✅ OK |
| Structure | −21°C | +38°C | ✅ OK |
| OBC/EPS | −15°C | +45°C | ✅ OK |
| Payload | −16°C | +42°C | ⚠️ Tight margin at cold |

## Project Structure

```
src/           Core physics modules (orbital, environment, thermal model, solver)
config/        All parameters in one YAML (no magic numbers)
app/           Streamlit dashboard
scripts/       CLI entry points
tests/         Unit tests for physics validation
notebooks/     Step-by-step physics verification
```

## Key Engineering Insights

1. **β-angle is the dominant parameter**: Switching from β=0° to β=90° can raise minimum temperatures by 30°C+ on the payload — critical for battery survival.

2. **Coating selection matters more than mass**: Changing α/ε ratio shifts equilibrium temperature by up to 50°C — far more impact than adding thermal mass.

3. **Internal power dominates during eclipse**: With 1 W dissipated internally and no solar input, thermal inertia determines minimum temperature — exactly the satellite equivalent of overnight cooling in building thermal models.

## Background

This project directly transposes methods I applied during EPR2 engineering work:
- Complex energy balance automation → Python ODE pipeline
- Multi-zone nodal models → Multi-node satellite thermal network  
- Parametric sensitivity reports → Interactive Streamlit dashboard

---
*Thermal environment data sources: NASA SORCE, CERES Energy Budget, ESA ECSS-E-HB-31-01*
```

---

*Fin du Cahier des Charges v1.0*  
*Durée totale estimée : 15–20 soirées de travail concentré*
